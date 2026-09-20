from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass(frozen=True)
class JournalLine:
    account_code: str
    debit: float
    credit: float
    description: str


@dataclass(frozen=True)
class JournalCommand:
    org_id: str | None
    entry_date: str
    currency: str
    fx_rate: float
    memo: str
    lines: list[JournalLine]


def _normalize_currency(token: str | None, default_currency: str) -> str:
    t = (token or "").strip().upper()
    if not t:
        return default_currency.upper()
    mapping = {
        "马币": "MYR",
        "MYR": "MYR",
        "RM": "MYR",
        "RINGGIT": "MYR",
        "新币": "SGD",
        "SGD": "SGD",
        "人民币": "CNY",
        "CNY": "CNY",
        "RMB": "CNY",
        "美金": "USD",
        "美元": "USD",
        "USD": "USD",
        "欧元": "EUR",
        "EUR": "EUR",
    }
    return mapping.get(t, t)


def _parse_amount(raw: str) -> float:
    s = (raw or "").strip().replace(",", "")
    return float(s)


def _parse_freeform_journal(payload: str, *, default_currency: str, default_fx_rate: float) -> JournalCommand:
    s = (payload or "").strip()
    s = s.replace("，", ",")
    s = re.sub(r"\s+", " ", s)

    s_lower = s.lower()
    debit_idx = s_lower.find("借")
    credit_idx = s_lower.find("贷")
    if debit_idx == -1 or credit_idx == -1 or credit_idx <= debit_idx:
        raise ValueError("无法识别借方/贷方，请用：借方<科目><金额><币种>，贷方<科目>（可省略金额）")

    debit_part = s[debit_idx:credit_idx].strip().lstrip("借").lstrip("方").strip(" ,")
    credit_part = s[credit_idx:].strip().lstrip("贷").lstrip("方").strip(" ,")

    side_ccy = r"(?P<ccy>马币|新币|人民币|美金|美元|欧元|MYR|SGD|CNY|RMB|USD|EUR|RM)?$"
    debit_re = re.compile(
        r"^(?P<acct>.+?)\s*(?P<amt>[0-9][0-9,]*(?:\.[0-9]+)?)\s*" + side_ccy,
        re.IGNORECASE,
    )
    credit_re = re.compile(
        r"^(?P<acct>.+?)(?:\s*(?P<amt>[0-9][0-9,]*(?:\.[0-9]+)?))?\s*" + side_ccy,
        re.IGNORECASE,
    )

    dm = debit_re.match(debit_part)
    cm = credit_re.match(credit_part)
    if not dm or not cm:
        raise ValueError("无法识别借方/贷方，请用：借方<科目><金额><币种>，贷方<科目>（可省略金额）")

    debit_acct = str(dm.group("acct") or "").strip()
    debit_amt = _parse_amount(dm.group("amt") or "0")
    debit_ccy = dm.group("ccy")

    credit_acct = str(cm.group("acct") or "").strip()
    credit_amt_raw = cm.group("amt")
    credit_amt = _parse_amount(credit_amt_raw) if credit_amt_raw else debit_amt
    credit_ccy = cm.group("ccy")

    ccy = _normalize_currency(debit_ccy or credit_ccy, default_currency)
    fx_rate = float(default_fx_rate)

    if debit_amt <= 0 or credit_amt <= 0:
        raise ValueError("金额必须大于 0")
    if abs(debit_amt - credit_amt) > 1e-9:
        raise ValueError("借贷金额不相等，请补齐金额")

    lines = [
        JournalLine(account_code=debit_acct, debit=debit_amt, credit=0.0, description=""),
        JournalLine(account_code=credit_acct, debit=0.0, credit=credit_amt, description=""),
    ]
    cmd = JournalCommand(
        org_id=None,
        entry_date=date.today().isoformat(),
        currency=ccy,
        fx_rate=fx_rate,
        memo="",
        lines=lines,
    )
    return cmd


def parse_journal_command(text: str, *, default_currency: str, default_fx_rate: float) -> JournalCommand | None:
    t = (text or "").strip()
    if not t:
        return None

    lowered = t.lower()
    if lowered.startswith("je "):
        payload = t[3:].strip()
    elif t.startswith("分录"):
        payload = t[2:].strip()
    else:
        return None

    if not payload:
        return None

    if payload.startswith("`"):
        payload = payload.strip("`").strip()

    try:
        obj = json.loads(payload)
    except Exception:
        return _parse_freeform_journal(payload, default_currency=default_currency, default_fx_rate=default_fx_rate)

    if not isinstance(obj, dict):
        raise ValueError("分录 JSON 必须是对象")

    org_id_raw = obj.get("orgId") if obj.get("orgId") is not None else obj.get("org_id")
    org_id = str(org_id_raw).strip() if org_id_raw else None
    entry_date = str(obj.get("entryDate") or obj.get("entry_date") or date.today().isoformat())
    currency = str(obj.get("currency") or default_currency).upper()
    fx_rate_raw = obj.get("fxRate") if obj.get("fxRate") is not None else obj.get("fx_rate")
    fx_rate = float(fx_rate_raw) if fx_rate_raw is not None else float(default_fx_rate)
    memo = str(obj.get("memo") or "")

    raw_lines: Any = obj.get("lines")
    if not isinstance(raw_lines, list) or len(raw_lines) < 2:
        raise ValueError("lines 需要至少两行（借/贷）")

    lines: list[JournalLine] = []
    for i, it in enumerate(raw_lines):
        if not isinstance(it, dict):
            raise ValueError(f"lines[{i}] 必须是对象")
        account_code = str(it.get("account") or it.get("accountCode") or it.get("account_code") or "").strip()
        if not account_code:
            raise ValueError(f"lines[{i}] 缺少 account/accountCode")
        debit = float(it.get("debit") or it.get("debitTxn") or it.get("debit_txn") or 0)
        credit = float(it.get("credit") or it.get("creditTxn") or it.get("credit_txn") or 0)
        description = str(it.get("desc") or it.get("description") or "").strip()
        lines.append(JournalLine(account_code=account_code, debit=debit, credit=credit, description=description))

    return JournalCommand(org_id=org_id, entry_date=entry_date, currency=currency, fx_rate=fx_rate, memo=memo, lines=lines)


def format_journal_preview(cmd: JournalCommand, *, account_label_overrides: dict[int, str] | None = None) -> str:
    total_debit = sum(x.debit for x in cmd.lines)
    total_credit = sum(x.credit for x in cmd.lines)
    overrides = account_label_overrides or {}
    lines_md = "\n".join(
        [
            f"- {overrides.get(i, x.account_code)} | 借 {x.debit:g} | 贷 {x.credit:g} | {x.description}".rstrip()
            for i, x in enumerate(cmd.lines)
        ]
    )
    header = f"日期：{cmd.entry_date}\n币种：{cmd.currency}（fxRate={cmd.fx_rate:g}）"
    memo = f"备注：{cmd.memo}" if cmd.memo else "备注：-"
    totals = f"合计：借 {total_debit:g} / 贷 {total_credit:g}"
    return "\n".join([header, memo, totals, "\n分录行：", lines_md])
