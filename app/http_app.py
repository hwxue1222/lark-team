from __future__ import annotations

from fastapi import FastAPI

from app.config import get_settings


settings = get_settings()
app = FastAPI(title=settings.bot_title)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

