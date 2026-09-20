from __future__ import annotations

from typing import Any


def build_org_select_card(*, action_id: str, orgs: list[dict[str, str]]) -> dict[str, Any]:
    items = orgs[:8]
    lines = "\n".join([f"- {o.get('orgName','')}" for o in items])
    elements: list[dict[str, Any]] = [
        {"tag": "markdown", "content": "请选择要操作的公司：\n" + (lines or "-")},
    ]

    buttons: list[dict[str, Any]] = []
    for o in items:
        buttons.append(
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": o.get("orgName") or "(unnamed)"},
                "type": "primary",
                "value": {"op": "select_org", "action_id": action_id, "org_id": o.get("orgId")},
            }
        )

    if len(orgs) > len(items):
        elements.append({"tag": "markdown", "content": "公司较多，仅展示前 8 个。可在 .env 固定 BBY_ACCOUNTING_ORG_ID。"})

    elements.append({"tag": "action", "actions": buttons})
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
        "header": {"title": {"tag": "plain_text", "content": "选择公司"}},
        "elements": elements,
    }

