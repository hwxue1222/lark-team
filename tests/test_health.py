import os

from fastapi.testclient import TestClient


def _set_env() -> None:
    os.environ.setdefault("LARK_APP_ID", "dummy")
    os.environ.setdefault("LARK_APP_SECRET", "dummy")
    os.environ.setdefault("KIMI_API_KEY", "dummy")
    os.environ.setdefault("KIMI_MODEL", "k3")


def test_health() -> None:
    _set_env()
    from app.http_app import app

    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
