from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException


@dataclass(frozen=True)
class AuthContext:
    token: str


def require_bearer_token(*, configured_token: str, authorization: str | None = Header(default=None)) -> AuthContext:
    if not configured_token:
        raise HTTPException(status_code=500, detail="LOCAL_AGENT_TOKEN is not configured")
    if not authorization:
        raise HTTPException(status_code=401, detail="missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="invalid Authorization header")
    token = authorization.removeprefix("Bearer ").strip()
    if token != configured_token:
        raise HTTPException(status_code=403, detail="invalid token")
    return AuthContext(token=token)

