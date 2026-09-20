from __future__ import annotations

import dataclasses
from datetime import datetime
from typing import Any

import httpx


@dataclasses.dataclass(frozen=True)
class DueJob:
    job_id: str
    title: str
    due_at: datetime | None
    url: str | None
    raw: dict[str, Any]


class BBYTodayAdminClient:
    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def fetch_due_jobs(self, *, path: str) -> list[DueJob]:
        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {self._token}"}
        with httpx.Client(timeout=20.0) as client:
            resp = client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        items: Any = payload
        if isinstance(payload, dict):
            for key in ("jobs", "data", "items", "due_jobs"):
                if key in payload:
                    items = payload[key]
                    break

        if not isinstance(items, list):
            return []

        out: list[DueJob] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            job_id = str(it.get("id") or it.get("job_id") or it.get("uuid") or "")
            title = str(it.get("title") or it.get("name") or it.get("summary") or "")
            url_val = it.get("url") or it.get("link")
            url_str = str(url_val) if url_val else None
            due_at = _parse_datetime(it.get("due_at") or it.get("dueAt") or it.get("due_time"))
            if not job_id:
                job_id = title or "unknown"
            if not title:
                title = job_id
            out.append(DueJob(job_id=job_id, title=title, due_at=due_at, url=url_str, raw=it))
        return out


def _parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds > 10_000_000_000:
            seconds = seconds / 1000.0
        try:
            return datetime.fromtimestamp(seconds)
        except Exception:
            return None
    if isinstance(value, str):
        v = value.strip()
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None
    return None

