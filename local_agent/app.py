from __future__ import annotations

from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel

from local_agent.actions import ActionResult, open_url
from local_agent.config import get_local_agent_settings
from local_agent.security import AuthContext, require_bearer_token


settings = get_local_agent_settings()
app = FastAPI(title="BBY Local Agent")


def _auth(authorization: str | None = Header(default=None)) -> AuthContext:
    return require_bearer_token(configured_token=settings.local_agent_token, authorization=authorization)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


class ActionRequest(BaseModel):
    action: str
    url: str | None = None


class ActionResponse(BaseModel):
    ok: bool
    action_id: str
    error: str | None = None


@app.post("/v1/actions", response_model=ActionResponse)
def create_action(
    req: ActionRequest,
    _: AuthContext = Depends(_auth),
) -> ActionResponse:
    if req.action == "open_url":
        if not req.url:
            return ActionResponse(ok=False, action_id="", error="missing url")
        res: ActionResult = open_url(url=req.url, allowed_domains_raw=settings.allowed_domains)
        return ActionResponse(ok=res.ok, action_id=res.action_id, error=res.error)
    return ActionResponse(ok=False, action_id="", error=f"unsupported action: {req.action}")
