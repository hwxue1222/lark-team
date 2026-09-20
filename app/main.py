from __future__ import annotations

import logging
import threading
from typing import Any
import uuid

import lark_oapi as lark

from lark_oapi.event.callback.model.p2_card_action_trigger import P2CardActionTriggerResponse

from app.bby_accounting_client import BBYAccountingClient
from app.account_cards import build_account_select_card
from app.journal_cards import build_journal_confirm_card
from app.journal_command import JournalCommand, parse_journal_command
from app.org_cards import build_org_select_card
from app.local_agent_client import LocalAgentClient
from app.kimi import KimiClient
from app.ttl_store import TTLStore

logger = logging.getLogger("app")


class AccountantConfig:
    def __init__(
        self,
        *,
        enabled: bool,
        base_url: str,
        email: str,
        password: str,
        org_id: str,
        operator_ids: str,
        default_currency: str,
        default_fx_rate: float,
    ) -> None:
        self.enabled = enabled
        self.base_url = base_url
        self.email = email
        self.password = password
        self.org_id = org_id
        self.operator_ids = operator_ids
        self.default_currency = default_currency
        self.default_fx_rate = default_fx_rate


class PendingJournal:
    def __init__(
        self,
        *,
        cmd: JournalCommand,
        sender_id_type: str,
        sender_id_value: str,
        chat_id: str | None,
        org_id: str | None,
        stage: str,
        resolved_account_ids: dict[int, str] | None = None,
        resolved_account_labels: dict[int, str] | None = None,
        latest_voucher_no: str | None = None,
    ) -> None:
        self.cmd = cmd
        self.sender_id_type = sender_id_type
        self.sender_id_value = sender_id_value
        self.chat_id = chat_id
        self.org_id = org_id
        self.stage = stage
        self.resolved_account_ids = resolved_account_ids or {}
        self.resolved_account_labels = resolved_account_labels or {}
        self.latest_voucher_no = latest_voucher_no


def _format_journal_status(status: str | None) -> str:
    raw = (status or "").strip()
    if not raw:
        return "-"

    s = raw.lower().replace("_", " ").replace("-", " ")
    s = " ".join([p for p in s.split() if p])

    if "posted" in s:
        return "已过账"
    if s in {"post", "post ok", "posted ok"}:
        return "已过账"
    if "draft" in s:
        return "草稿"
    if "void" in s:
        return "已作废"
    if "cancel" in s:
        return "已取消"
    return raw


def _extract_operator_receive_id(event: Any) -> tuple[str, str] | None:
    operator = getattr(event, "operator", None) if event else None
    operator_id = getattr(operator, "operator_id", None) if operator else None
    if not operator_id:
        return None
    open_id = getattr(operator_id, "open_id", None)
    if open_id:
        return ("open_id", str(open_id))
    user_id = getattr(operator_id, "user_id", None)
    if user_id:
        return ("user_id", str(user_id))
    union_id = getattr(operator_id, "union_id", None)
    if union_id:
        return ("union_id", str(union_id))
    return None



def _extract_text_from_message(message: Any) -> str:
    msg_type = getattr(message, "message_type", None) or getattr(message, "msg_type", None)
    if msg_type != "text":
        return ""
    content = getattr(message, "content", None)
    if not content:
        return ""
    try:
        import json

        parsed = json.loads(content)
    except Exception:
        return ""
    return str(parsed.get("text") or "")


def _should_reply(message: Any, *, bot_name_hint: str) -> bool:
    chat_type = getattr(message, "chat_type", None)
    if chat_type not in {"group", "p2p"}:
        return True
    if chat_type == "p2p":
        return True

    mentions = getattr(message, "mentions", None) or []
    if not mentions:
        return False

    hint = (bot_name_hint or "").strip()
    if not hint:
        return True

    for m in mentions:
        name = getattr(m, "name", None) or ""
        if hint in name:
            return True
    return False


def _strip_mentions(message: Any, text: str) -> str:
    out = text
    mentions = getattr(message, "mentions", None) or []
    for m in mentions:
        key = getattr(m, "key", None) or ""
        name = getattr(m, "name", None) or ""
        if key:
            out = out.replace(key, "")
        if name:
            out = out.replace("@" + name, "")
            out = out.replace(name, "")
    return out.strip()


def _extract_sender_open_id(event: Any) -> str | None:
    sender = getattr(event, "sender", None)
    if not sender:
        return None
    sender_id = getattr(sender, "sender_id", None)
    if not sender_id:
        return None
    open_id = getattr(sender_id, "open_id", None)
    return str(open_id) if open_id else None


def _extract_sender_receive_id(event: Any) -> tuple[str, str] | None:
    sender = getattr(event, "sender", None)
    sender_id = getattr(sender, "sender_id", None) if sender else None
    if not sender_id:
        return None
    open_id = getattr(sender_id, "open_id", None)
    if open_id:
        return ("open_id", str(open_id))
    user_id = getattr(sender_id, "user_id", None)
    if user_id:
        return ("user_id", str(user_id))
    union_id = getattr(sender_id, "union_id", None)
    if union_id:
        return ("union_id", str(union_id))
    return None


def _parse_local_command(text: str) -> tuple[str, str] | None:
    t = (text or "").strip()
    if not t:
        return None
    lowered = t.lower()
    if lowered.startswith("local "):
        t = t[6:].strip()
    elif t.startswith("本地"):
        t = t[2:].strip()
    else:
        return None

    if not t:
        return None

    if t.startswith("打开"):
        url = t[2:].strip()
        return ("open_url", url) if url else None
    if t.lower().startswith("open "):
        url = t[5:].strip()
        return ("open_url", url) if url else None
    return None


def _parse_operator_allowlist(raw: str) -> set[str]:
    out: set[str] = set()
    for part in (raw or "").split(","):
        v = part.strip()
        if v:
            out.add(v)
    return out


def _extract_chat_id(message: Any) -> str | None:
    chat_id = getattr(message, "chat_id", None) if message else None
    return str(chat_id) if chat_id else None


def _is_bot_sender(event: Any) -> bool:
    sender = getattr(event, "sender", None)
    sender_type = getattr(sender, "sender_type", None) if sender else None
    return sender_type in {"app", "bot"}


def build_event_handler(
    *,
    bot: Any,
    kimi: KimiClient,
    bot_title: str,
    local_agent: LocalAgentClient | None = None,
    local_agent_operator_ids: str = "",
    accountant: AccountantConfig | None = None,
) -> Any:
    log_level = lark.LogLevel.INFO
    builder = lark.EventDispatcherHandler.builder("", "", log_level)

    pending_journals: TTLStore[PendingJournal] = TTLStore(ttl_seconds=10 * 60)

    def on_message_receive(data: Any) -> None:
        event = getattr(data, "event", None)
        if event and _is_bot_sender(event):
            return
        message = getattr(event, "message", None) if event else None

        chat_type = getattr(message, "chat_type", None) if message else None
        message_type = getattr(message, "message_type", None) if message else None
        logger.info(
            "message.receive raw chat_type=%s message_type=%s has_message=%s",
            chat_type,
            message_type,
            bool(message),
        )

        user_text = _extract_text_from_message(message)
        sender_receive = _extract_sender_receive_id(event)
        chat_id = _extract_chat_id(message)
        if not user_text or not sender_receive:
            return
        if not _should_reply(message, bot_name_hint=bot_title):
            return
        user_text = _strip_mentions(message, user_text)
        if not user_text:
            return

        sender_id_type, sender_id_value = sender_receive

        if accountant and accountant.enabled:
            allow = _parse_operator_allowlist(accountant.operator_ids)
            if not allow or sender_id_value in allow:
                try:
                    cmd = parse_journal_command(
                        user_text,
                        default_currency=accountant.default_currency,
                        default_fx_rate=accountant.default_fx_rate,
                    )
                except Exception as e:
                    if chat_id:
                        bot.send_text_to_chat_id(chat_id=chat_id, text=f"分录指令解析失败：{e}")
                    else:
                        if sender_id_type == "open_id":
                            bot.send_text_to_open_id(open_id=sender_id_value, text=f"分录指令解析失败：{e}")
                        elif sender_id_type == "user_id":
                            bot.send_text_to_user_id(user_id=sender_id_value, text=f"分录指令解析失败：{e}")
                        elif sender_id_type == "union_id":
                            bot.send_text_to_union_id(union_id=sender_id_value, text=f"分录指令解析失败：{e}")
                    return
                if cmd:
                    if not accountant.email or not accountant.password:
                        reply = "会计 Agent 未配置：请在 .env 设置 BBY_ACCOUNTING_EMAIL / BBY_ACCOUNTING_PASSWORD"
                        if chat_id:
                            bot.send_text_to_chat_id(chat_id=chat_id, text=reply)
                        else:
                            if sender_id_type == "open_id":
                                bot.send_text_to_open_id(open_id=sender_id_value, text=reply)
                            elif sender_id_type == "user_id":
                                bot.send_text_to_user_id(user_id=sender_id_value, text=reply)
                            elif sender_id_type == "union_id":
                                bot.send_text_to_union_id(union_id=sender_id_value, text=reply)
                        return

                    resolved_org_id = cmd.org_id or (accountant.org_id or None)
                    action_id = str(uuid.uuid4())

                    def _send_card(card: dict[str, Any]) -> None:
                        if chat_id:
                            bot.send_card_to_chat_id(chat_id=chat_id, card=card)
                            return
                        if sender_id_type == "open_id":
                            bot.send_card_to_open_id(open_id=sender_id_value, card=card)
                        elif sender_id_type == "user_id":
                            bot.send_card_to_user_id(user_id=sender_id_value, card=card)
                        elif sender_id_type == "union_id":
                            bot.send_card_to_union_id(union_id=sender_id_value, card=card)

                    if resolved_org_id:
                        latest_voucher_no: str | None = None
                        try:
                            client = BBYAccountingClient(
                                base_url=accountant.base_url,
                                email=accountant.email,
                                password=accountant.password,
                                org_id=resolved_org_id,
                            )
                            try:
                                latest_voucher_no = client.get_latest_voucher_no()
                            finally:
                                client.close()
                        except Exception:
                            latest_voucher_no = None
                        pending_journals.set(
                            action_id,
                            PendingJournal(
                                cmd=cmd,
                                sender_id_type=sender_id_type,
                                sender_id_value=sender_id_value,
                                chat_id=chat_id,
                                org_id=resolved_org_id,
                                stage="confirm",
                                resolved_account_ids={},
                                resolved_account_labels={},
                                latest_voucher_no=latest_voucher_no,
                            ),
                        )
                        _send_card(
                            build_journal_confirm_card(
                                action_id=action_id,
                                cmd=cmd,
                                account_label_overrides=None,
                                system_latest_voucher_no=latest_voucher_no,
                            )
                        )
                        return

                    try:
                        client = BBYAccountingClient(
                            base_url=accountant.base_url,
                            email=accountant.email,
                            password=accountant.password,
                            org_id=None,
                        )
                        try:
                            orgs, active_org_id = client.list_orgs()
                        finally:
                            client.close()
                    except Exception as e:
                        reply = f"获取公司列表失败：{e}"
                        if chat_id:
                            bot.send_text_to_chat_id(chat_id=chat_id, text=reply)
                        else:
                            if sender_id_type == "open_id":
                                bot.send_text_to_open_id(open_id=sender_id_value, text=reply)
                            elif sender_id_type == "user_id":
                                bot.send_text_to_user_id(user_id=sender_id_value, text=reply)
                            elif sender_id_type == "union_id":
                                bot.send_text_to_union_id(union_id=sender_id_value, text=reply)
                        return

                    if len(orgs) <= 1:
                        chosen = orgs[0].org_id if orgs else (active_org_id or "")
                        if not chosen:
                            reply = "未找到可用公司，请在 bbyaccounting 创建/加入公司或在 .env 配置 BBY_ACCOUNTING_ORG_ID"
                            if chat_id:
                                bot.send_text_to_chat_id(chat_id=chat_id, text=reply)
                            else:
                                if sender_id_type == "open_id":
                                    bot.send_text_to_open_id(open_id=sender_id_value, text=reply)
                                elif sender_id_type == "user_id":
                                    bot.send_text_to_user_id(user_id=sender_id_value, text=reply)
                                elif sender_id_type == "union_id":
                                    bot.send_text_to_union_id(union_id=sender_id_value, text=reply)
                            return
                        latest_voucher_no: str | None = None
                        try:
                            client2 = BBYAccountingClient(
                                base_url=accountant.base_url,
                                email=accountant.email,
                                password=accountant.password,
                                org_id=chosen,
                            )
                            try:
                                latest_voucher_no = client2.get_latest_voucher_no()
                            finally:
                                client2.close()
                        except Exception:
                            latest_voucher_no = None
                        pending_journals.set(
                            action_id,
                            PendingJournal(
                                cmd=cmd,
                                sender_id_type=sender_id_type,
                                sender_id_value=sender_id_value,
                                chat_id=chat_id,
                                org_id=chosen,
                                stage="confirm",
                                resolved_account_ids={},
                                resolved_account_labels={},
                                latest_voucher_no=latest_voucher_no,
                            ),
                        )
                        _send_card(
                            build_journal_confirm_card(
                                action_id=action_id,
                                cmd=cmd,
                                account_label_overrides=None,
                                system_latest_voucher_no=latest_voucher_no,
                            )
                        )
                        return

                    pending_journals.set(
                        action_id,
                        PendingJournal(
                            cmd=cmd,
                            sender_id_type=sender_id_type,
                            sender_id_value=sender_id_value,
                            chat_id=chat_id,
                            org_id=None,
                            stage="choose_org",
                            resolved_account_ids={},
                            resolved_account_labels={},
                        ),
                    )
                    _send_card(
                        build_org_select_card(
                            action_id=action_id,
                            orgs=[{"orgId": o.org_id, "orgName": o.org_name} for o in orgs],
                        )
                    )
                    return

        local_cmd = _parse_local_command(user_text)
        if local_cmd and local_agent:
            allow = _parse_operator_allowlist(local_agent_operator_ids)
            if allow and sender_id_value not in allow:
                logger.info("local_agent denied sender_id=%s", sender_id_value)
                return
            action, url = local_cmd
            if action == "open_url":
                try:
                    res = local_agent.open_url(url=url)
                    if res.ok:
                        reply = f"已在本机打开：{url}"
                    else:
                        reply = f"本地执行失败：{res.error or 'unknown error'}"
                except Exception as e:
                    logger.exception("local_agent call failed")
                    reply = f"本地执行失败：{e}"

                if chat_id:
                    bot.send_text_to_chat_id(chat_id=chat_id, text=reply)
                else:
                    if sender_id_type == "open_id":
                        bot.send_text_to_open_id(open_id=sender_id_value, text=reply)
                    elif sender_id_type == "user_id":
                        bot.send_text_to_user_id(user_id=sender_id_value, text=reply)
                    elif sender_id_type == "union_id":
                        bot.send_text_to_union_id(union_id=sender_id_value, text=reply)
                return
        logger.info(
            "message.receive sender_id_type=%s sender_id=%s chat_id=%s text=%s",
            sender_id_type,
            sender_id_value,
            chat_id,
            user_text,
        )


        def _work() -> None:
            try:
                kimi_res = kimi.infer_intent_and_reply(user_text=user_text)
                if chat_id:
                    res = bot.send_text_to_chat_id(chat_id=chat_id, text=kimi_res.reply)
                    logger.info("message.send chat_id=%s message_id=%s", chat_id, getattr(res, "message_id", None))
                else:
                    if sender_id_type == "open_id":
                        res = bot.send_text_to_open_id(open_id=sender_id_value, text=kimi_res.reply)
                        logger.info(
                            "message.send open_id=%s message_id=%s",
                            sender_id_value,
                            getattr(res, "message_id", None),
                        )
                    elif sender_id_type == "user_id":
                        res = bot.send_text_to_user_id(user_id=sender_id_value, text=kimi_res.reply)
                        logger.info(
                            "message.send user_id=%s message_id=%s",
                            sender_id_value,
                            getattr(res, "message_id", None),
                        )
                    elif sender_id_type == "union_id":
                        res = bot.send_text_to_union_id(union_id=sender_id_value, text=kimi_res.reply)
                        logger.info(
                            "message.send union_id=%s message_id=%s",
                            sender_id_value,
                            getattr(res, "message_id", None),
                        )
                    else:
                        logger.warning("unsupported sender id type: %s", sender_id_type)
            except Exception:
                logger.exception("message.receive failed sender_id=%s", sender_id_value)
                try:
                    if chat_id:
                        res = bot.send_text_to_chat_id(chat_id=chat_id, text="系统繁忙，请稍后再试")
                        logger.info(
                            "message.send fallback chat_id=%s message_id=%s",
                            chat_id,
                            getattr(res, "message_id", None),
                        )
                    else:
                        if sender_id_type == "open_id":
                            res = bot.send_text_to_open_id(open_id=sender_id_value, text="系统繁忙，请稍后再试")
                            logger.info(
                                "message.send fallback open_id=%s message_id=%s",
                                sender_id_value,
                                getattr(res, "message_id", None),
                            )
                        elif sender_id_type == "user_id":
                            res = bot.send_text_to_user_id(user_id=sender_id_value, text="系统繁忙，请稍后再试")
                            logger.info(
                                "message.send fallback user_id=%s message_id=%s",
                                sender_id_value,
                                getattr(res, "message_id", None),
                            )
                        elif sender_id_type == "union_id":
                            res = bot.send_text_to_union_id(union_id=sender_id_value, text="系统繁忙，请稍后再试")
                            logger.info(
                                "message.send fallback union_id=%s message_id=%s",
                                sender_id_value,
                                getattr(res, "message_id", None),
                            )
                except Exception:
                    logger.exception("fallback send_text failed sender_id=%s", sender_id_value)

        threading.Thread(target=_work, daemon=True).start()

    def _send_text_back(*, pending: PendingJournal, text: str) -> None:
        if pending.chat_id:
            bot.send_text_to_chat_id(chat_id=pending.chat_id, text=text)
            return
        if pending.sender_id_type == "open_id":
            bot.send_text_to_open_id(open_id=pending.sender_id_value, text=text)
        elif pending.sender_id_type == "user_id":
            bot.send_text_to_user_id(user_id=pending.sender_id_value, text=text)
        elif pending.sender_id_type == "union_id":
            bot.send_text_to_union_id(union_id=pending.sender_id_value, text=text)

    def on_card_action(data: Any) -> Any:
        event = getattr(data, "event", None)
        operator = _extract_operator_receive_id(event)
        action = getattr(event, "action", None) if event else None
        value = getattr(action, "value", None) if action else None
        if value is None:
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效操作"}})
        if isinstance(value, str):
            try:
                import json

                value = json.loads(value)
            except Exception:
                value = {}
        if not isinstance(value, dict):
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效操作"}})

        op = str(value.get("op") or "")
        action_id = str(value.get("action_id") or "")
        org_id = str(value.get("org_id") or "")
        line_index_raw = value.get("line_index")
        account_id = str(value.get("account_id") or "")
        account_code = str(value.get("account_code") or "")
        account_name = str(value.get("account_name") or "")
        if not action_id:
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效操作"}})

        if op == "cancel":
            pending_journals.delete(action_id)
            return P2CardActionTriggerResponse({"toast": {"type": "info", "content": "已取消"}})

        pending = pending_journals.get(action_id)
        if not pending:
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "已过期，请重新发起"}})

        if operator and operator[1] != pending.sender_id_value:
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "仅发起人可操作"}})

        if op == "select_org":
            if not org_id:
                return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "未选择公司"}})
            updated = PendingJournal(
                cmd=pending.cmd,
                sender_id_type=pending.sender_id_type,
                sender_id_value=pending.sender_id_value,
                chat_id=pending.chat_id,
                org_id=org_id,
                stage="confirm",
                resolved_account_ids=pending.resolved_account_ids,
                resolved_account_labels=pending.resolved_account_labels,
                latest_voucher_no=None,
            )

            latest_voucher_no: str | None = None
            if accountant and accountant.enabled and accountant.email and accountant.password:
                try:
                    client = BBYAccountingClient(
                        base_url=accountant.base_url,
                        email=accountant.email,
                        password=accountant.password,
                        org_id=org_id,
                    )
                    try:
                        latest_voucher_no = client.get_latest_voucher_no()
                    finally:
                        client.close()
                except Exception:
                    latest_voucher_no = None

            updated.latest_voucher_no = latest_voucher_no
            pending_journals.set(action_id, updated)
            card = build_journal_confirm_card(
                action_id=action_id,
                cmd=pending.cmd,
                account_label_overrides=updated.resolved_account_labels,
                system_latest_voucher_no=latest_voucher_no,
            )
            if pending.chat_id:
                bot.send_card_to_chat_id(chat_id=pending.chat_id, card=card)
            else:
                if pending.sender_id_type == "open_id":
                    bot.send_card_to_open_id(open_id=pending.sender_id_value, card=card)
                elif pending.sender_id_type == "user_id":
                    bot.send_card_to_user_id(user_id=pending.sender_id_value, card=card)
                elif pending.sender_id_type == "union_id":
                    bot.send_card_to_union_id(union_id=pending.sender_id_value, card=card)
            return P2CardActionTriggerResponse({"toast": {"type": "info", "content": "公司已选择，请确认执行"}})

        if op == "select_account":
            try:
                line_index = int(line_index_raw)
            except Exception:
                return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效科目选择"}})
            if line_index < 0 or not account_id:
                return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效科目选择"}})
            pending.resolved_account_ids[line_index] = account_id
            label = ""
            if account_code and account_name:
                label = f"{account_code}-{account_name}"
            elif account_code:
                label = account_code
            elif account_name:
                label = account_name
            if label:
                pending.resolved_account_labels[line_index] = label
            pending_journals.set(action_id, pending)
            card = build_journal_confirm_card(
                action_id=action_id,
                cmd=pending.cmd,
                account_label_overrides=pending.resolved_account_labels,
                system_latest_voucher_no=pending.latest_voucher_no,
            )
            if pending.chat_id:
                bot.send_card_to_chat_id(chat_id=pending.chat_id, card=card)
            else:
                if pending.sender_id_type == "open_id":
                    bot.send_card_to_open_id(open_id=pending.sender_id_value, card=card)
                elif pending.sender_id_type == "user_id":
                    bot.send_card_to_user_id(user_id=pending.sender_id_value, card=card)
                elif pending.sender_id_type == "union_id":
                    bot.send_card_to_union_id(union_id=pending.sender_id_value, card=card)
            msg = f"科目已选择：{account_code}" if account_code else "科目已选择"
            return P2CardActionTriggerResponse({"toast": {"type": "info", "content": msg}})

        if op != "confirm":
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "无效操作"}})

        pending_journals.delete(action_id)
        if not accountant or not accountant.enabled:
            return P2CardActionTriggerResponse({"toast": {"type": "warning", "content": "会计 Agent 未启用"}})

        def _do_post() -> None:
            try:
                client = BBYAccountingClient(
                    base_url=accountant.base_url,
                    email=accountant.email,
                    password=accountant.password,
                    org_id=(pending.org_id or accountant.org_id or None),
                )
                try:
                    lines_payload: list[dict[str, Any]] = []
                    for i, ln in enumerate(pending.cmd.lines):
                        account_id = pending.resolved_account_ids.get(i)
                        if not account_id:
                            exact = client.find_exact_account_id(account_ref=ln.account_code)
                            if exact:
                                account_id = exact
                            else:
                                sugg = client.suggest_accounts(query=ln.account_code, limit=8)
                                if sugg:
                                    pending_journals.set(action_id, pending)
                                    card = build_account_select_card(
                                        action_id=action_id,
                                        line_index=i,
                                        query=ln.account_code,
                                        candidates=[{"id": a.id, "code": a.code, "name": a.name} for a in sugg],
                                    )
                                    if pending.chat_id:
                                        bot.send_card_to_chat_id(chat_id=pending.chat_id, card=card)
                                    else:
                                        if pending.sender_id_type == "open_id":
                                            bot.send_card_to_open_id(open_id=pending.sender_id_value, card=card)
                                        elif pending.sender_id_type == "user_id":
                                            bot.send_card_to_user_id(user_id=pending.sender_id_value, card=card)
                                        elif pending.sender_id_type == "union_id":
                                            bot.send_card_to_union_id(union_id=pending.sender_id_value, card=card)
                                    return
                                raise RuntimeError(f"unknown account: {ln.account_code}")
                        lines_payload.append(
                            {
                                "accountId": account_id,
                                "description": ln.description,
                                "debitTxn": ln.debit,
                                "creditTxn": ln.credit,
                            }
                        )
                    res = client.post_journal(
                        entry_date=pending.cmd.entry_date,
                        currency=pending.cmd.currency,
                        fx_rate=pending.cmd.fx_rate,
                        memo=pending.cmd.memo,
                        lines=lines_payload,
                    )
                finally:
                    client.close()
                status_label = _format_journal_status(res.status)
                voucher_no = res.voucher_no or "-"
                text = f"分录已创建：分录号={voucher_no} 状态={status_label} entry_id={res.entry_id}"
                _send_text_back(pending=pending, text=text)
            except Exception as e:
                _send_text_back(pending=pending, text=f"分录创建失败：{e}")

        threading.Thread(target=_do_post, daemon=True).start()
        return P2CardActionTriggerResponse({"toast": {"type": "info", "content": "已接收，正在执行"}})

    def on_card_action_v1(data: Any) -> None:
        event = getattr(data, "event", None) or {}
        action = event.get("action") if isinstance(event, dict) else None
        logger.info("card.action.trigger ignored action=%s", action)

    handler = (
        builder.register_p2_im_message_receive_v1(on_message_receive)
        .register_p2_card_action_trigger(on_card_action)
        .register_p1_customized_event("card.action.trigger", on_card_action_v1)
        .build()
    )
    return handler
