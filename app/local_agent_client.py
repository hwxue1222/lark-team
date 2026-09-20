from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(frozen=True)
class LocalAgentResponse:
    ok: bool
    action_id: str | None = None
    error: str | None = None


class LocalAgentClient:
    def __init__(self, *, base_url: str, token: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token

    def open_url(self, *, url: str) -> LocalAgentResponse:
        headers = {"Authorization": f"Bearer {self._token}"}
        payload = {"action": "open_url", "url": url}
        with httpx.Client(timeout=10) as client:
            r = client.post(f"{self._base_url}/v1/actions", json=payload, headers=headers)
        try:
            data = r.json()
        except Exception:
            return LocalAgentResponse(ok=False, error=f"bad response: http={r.status_code}")
        if not isinstance(data, dict):
            return LocalAgentResponse(ok=False, error=f"bad response: http={r.status_code}")
        ok = bool(data.get("ok"))
        return LocalAgentResponse(ok=ok, action_id=data.get("action_id"), error=data.get("error"))

