from __future__ import annotations

from typing import Any

from app.journal_command import JournalCommand, format_journal_preview


def build_journal_confirm_card(
    *,
    action_id: str,
    cmd: JournalCommand,
    account_label_overrides: dict[int, str] | None = None,
) -> dict[str, Any]:
    preview = format_journal_preview(cmd, account_label_overrides=account_label_overrides)
    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "会计分录确认"}},
        "elements": [
            {"tag": "markdown", "content": preview},
            {
                "tag": "action",
                "actions": [
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "确认执行"},
                        "type": "primary",
                        "value": {"op": "confirm", "action_id": action_id},
                    },
                    {
                        "tag": "button",
                        "text": {"tag": "plain_text", "content": "取消"},
                        "type": "danger",
                        "value": {"op": "cancel", "action_id": action_id},
                    },
                ],
            },
        ],
    }
