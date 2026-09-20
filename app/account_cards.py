from __future__ import annotations

from typing import Any


def build_account_select_card(
    *,
    action_id: str,
    line_index: int,
    query: str,
    candidates: list[dict[str, str]],
) -> dict[str, Any]:
    elements: list[dict[str, Any]] = [
        {
            "tag": "markdown",
            "content": f"未找到科目：`{query}`\n\n请选择最接近的科目（第 {line_index + 1} 行）：",
        }
    ]

    actions: list[dict[str, Any]] = []
    for c in candidates[:8]:
        label = f"{c.get('code','')}-{c.get('name','')}"
        actions.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": label[:40]},
                "type": "primary",
                "value": {
                    "op": "select_account",
                    "action_id": action_id,
                    "line_index": line_index,
                    "account_id": c.get("id"),
                    "account_code": c.get("code"),
                    "account_name": c.get("name"),
                },
            }
        )

    elements.append({"tag": "action", "actions": actions})
    elements.append(
        {
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "取消"},
                    "type": "danger",
                    "value": {"op": "cancel", "action_id": action_id},
                }
            ],
        }
    )

    return {
        "config": {"wide_screen_mode": True},
        "header": {"title": {"tag": "plain_text", "content": "选择科目"}},
        "elements": elements,
    }

