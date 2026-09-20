from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import lark_oapi as lark


@dataclass(frozen=True)
class LarkSendResult:
    message_id: str | None


class LarkBotClient:
    def __init__(self, *, app_id: str, app_secret: str, domain: str | None = None) -> None:
        builder = lark.Client.builder().app_id(app_id).app_secret(app_secret)
        if domain:
            builder = builder.domain(domain)
        self._client = builder.build()

    def send_text_to_open_id(self, *, open_id: str, text: str) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(open_id)
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_text failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_text_to_user_id(self, *, user_id: str, text: str) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("user_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(user_id)
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_text(user_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_text_to_union_id(self, *, union_id: str, text: str) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("union_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(union_id)
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_text(union_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_text_to_chat_id(self, *, chat_id: str, text: str) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("text")
                .content(json.dumps({"text": text}, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_text(chat_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_card_to_open_id(self, *, open_id: str, card: dict[str, Any]) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("open_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(open_id)
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_card failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_card_to_user_id(self, *, user_id: str, card: dict[str, Any]) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("user_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(user_id)
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_card(user_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_card_to_union_id(self, *, union_id: str, card: dict[str, Any]) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("union_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(union_id)
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_card(union_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))

    def send_card_to_chat_id(self, *, chat_id: str, card: dict[str, Any]) -> LarkSendResult:
        req = (
            lark.im.v1.CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                lark.im.v1.CreateMessageRequestBody.builder()
                .receive_id(chat_id)
                .msg_type("interactive")
                .content(json.dumps(card, ensure_ascii=False))
                .build()
            )
            .build()
        )
        resp = self._client.im.v1.message.create(req)
        if not resp.success():
            raise RuntimeError(f"lark send_card(chat_id) failed: code={resp.code} msg={resp.msg}")
        return LarkSendResult(message_id=getattr(resp.data, "message_id", None))
