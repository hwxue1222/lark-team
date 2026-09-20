from __future__ import annotations

from datetime import datetime
from typing import Any

from app.bby_today import DueJob


def build_morning_report_card(*, title: str, date_label: str, jobs: list[DueJob]) -> dict[str, Any]:
    lines: list[str] = []
    if not jobs:
        lines.append("今天暂无到期任务。")
    else:
        for j in jobs[:20]:
            due = _format_due(j.due_at)
            if j.url:
                lines.append(f"- {due} [{_escape(j.title)}]({j.url})")
            else:
                lines.append(f"- {due} {_escape(j.title)}")

    content = "\n".join(lines)
    return {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"{title} · 晨报 {date_label}"},
            "template": "blue",
        },
        "elements": [
            {"tag": "markdown", "content": content},
        ],
    }


def _format_due(d: datetime | None) -> str:
    if not d:
        return "(无截止)"
    try:
        return d.strftime("%m-%d %H:%M")
    except Exception:
        return "(截止)"


def _escape(s: str) -> str:
    return s.replace("\n", " ").strip()

