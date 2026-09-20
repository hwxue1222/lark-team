from __future__ import annotations

import time
import uuid
import webbrowser
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class ActionResult:
    action_id: str
    ok: bool
    error: str | None = None


def _parse_allowed_domains(raw: str) -> set[str]:
    out: set[str] = set()
    for part in (raw or "").split(","):
        d = part.strip().lower()
        if not d:
            continue
        out.add(d)
    return out


def open_url(*, url: str, allowed_domains_raw: str) -> ActionResult:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ActionResult(action_id=str(uuid.uuid4()), ok=False, error="only http/https is allowed")
    if not parsed.netloc:
        return ActionResult(action_id=str(uuid.uuid4()), ok=False, error="missing domain")

    allowed = _parse_allowed_domains(allowed_domains_raw)
    hostname = (parsed.hostname or "").lower()
    if allowed and hostname not in allowed:
        return ActionResult(action_id=str(uuid.uuid4()), ok=False, error=f"domain not allowed: {hostname}")

    action_id = str(uuid.uuid4())
    ok = webbrowser.open(url, new=1, autoraise=True)
    time.sleep(0.1)
    if not ok:
        return ActionResult(action_id=action_id, ok=False, error="failed to open browser")
    return ActionResult(action_id=action_id, ok=True)

