import json
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.kimi import KimiClient
from app.main import build_event_handler


@dataclass
class _Captured:
    cards: list[dict[str, Any]]
    texts: list[str]


class FakeBot:
    def __init__(self, captured: _Captured) -> None:
        self._captured = captured

    def send_card_to_open_id(self, *, open_id: str, card: dict[str, Any]) -> Any:
        self._captured.cards.append(card)
        return {"message_id": "fake_card"}

    def send_text_to_open_id(self, *, open_id: str, text: str) -> Any:
        self._captured.texts.append(text)
        return {"message_id": "fake_text"}

    def send_text_to_chat_id(self, *, chat_id: str, text: str) -> Any:
        self._captured.texts.append(text)
        return {"message_id": "fake_text_chat"}

    def send_card_to_chat_id(self, *, chat_id: str, card: dict[str, Any]) -> Any:
        self._captured.cards.append(card)
        return {"message_id": "fake_card_chat"}


def _require_env(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise SystemExit(f"missing env: {name}")
    return v


def _payload_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def _event_message_receive(*, app_id: str, open_id: str, text: str) -> dict[str, Any]:
    now = int(time.time())
    return {
        "schema": "2.0",
        "header": {
            "event_id": "local_e2e_event",
            "event_type": "im.message.receive_v1",
            "create_time": str(now),
            "token": "local",
            "app_id": app_id,
            "tenant_key": "local",
        },
        "event": {
            "sender": {
                "sender_id": {"open_id": open_id},
                "sender_type": "user",
                "tenant_key": "local",
            },
            "message": {
                "message_id": "local_msg",
                "message_type": "text",
                "chat_id": "oc_local_chat",
                "content": json.dumps({"text": text}, ensure_ascii=False),
            },
        },
    }


def _event_card_action(*, app_id: str, open_id: str, reply: str, intent: str) -> dict[str, Any]:
    now = int(time.time())
    return {
        "schema": "2.0",
        "header": {
            "event_id": "local_e2e_action",
            "event_type": "card.action.trigger",
            "create_time": str(now),
            "token": "local",
            "app_id": app_id,
            "tenant_key": "local",
        },
        "event": {
            "operator": {"operator_id": {"open_id": open_id}},
            "action": {
                "tag": "button",
                "value": {"open_id": open_id, "reply": reply, "intent": intent, "action": "confirm"},
            },
        },
    }


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    app_id = _require_env("LARK_APP_ID")
    moonshot_api_key = _require_env("MOONSHOT_API_KEY")
    moonshot_base_url = os.getenv("MOONSHOT_BASE_URL") or "https://api.moonshot.ai/v1"
    model_name = _require_env("MODEL_NAME")

    captured = _Captured(cards=[], texts=[])
    bot = FakeBot(captured)
    kimi = KimiClient(api_key=moonshot_api_key, base_url=moonshot_base_url, model=model_name)

    dispatcher = build_event_handler(
        bot=bot,
        kimi=kimi,
        bot_title="本地E2E",
    )

    open_id = "ou_local_test"
    user_text = "你好，帮我用一句话介绍一下你自己"

    dispatcher.do_without_validation(_payload_bytes(_event_message_receive(app_id=app_id, open_id=open_id, text=user_text)))

    deadline = time.time() + 20
    while time.time() < deadline and not captured.texts:
        time.sleep(0.1)
    if not captured.texts:
        raise SystemExit("no text reply sent")

    print("user_text:")
    print(user_text)
    print("\nreply:")
    print(captured.texts[-1])


if __name__ == "__main__":
    main()
