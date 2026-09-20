import json


class DummyBot:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str, str]] = []

    def send_text_to_chat_id(self, *, chat_id: str, text: str):
        self.sent.append(("chat_id", chat_id, text))

    def send_text_to_open_id(self, *, open_id: str, text: str):
        self.sent.append(("open_id", open_id, text))

    def send_text_to_user_id(self, *, user_id: str, text: str):
        self.sent.append(("user_id", user_id, text))


class DummyKimi:
    def infer_intent_and_reply(self, *, user_text: str):
        return type("R", (), {"reply": f"echo:{user_text}"})


def test_card_action_v1_is_ignored() -> None:
    from app.main import build_event_handler

    handler = build_event_handler(bot=DummyBot(), kimi=DummyKimi(), bot_title="BBY中控")

    payload = json.dumps(
        {
            "uuid": "u1",
            "event": {"type": "card.action.trigger", "action": {"value": {"k": "v"}}},
        }
    ).encode("utf-8")

    assert handler.do_without_validation(payload) is None

