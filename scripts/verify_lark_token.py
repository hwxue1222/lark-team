import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    settings = get_settings()

    url = settings.lark_domain.rstrip("/") + "/open-apis/auth/v3/app_access_token/internal"
    payload = {"app_id": settings.lark_app_id, "app_secret": settings.lark_app_secret}

    with httpx.Client(timeout=10) as client:
        r = client.post(url, json=payload)

    try:
        data = r.json()
    except Exception:
        data = {"raw": r.text}

    code = data.get("code")
    msg = data.get("msg")
    expire = data.get("expire")
    ok = (r.status_code == 200) and (code == 0)

    app_id_tail = settings.lark_app_id[-6:] if settings.lark_app_id else ""
    print(f"LARK_DOMAIN={settings.lark_domain} LARK_APP_ID=***{app_id_tail}")
    print(f"http_status={r.status_code} code={code} msg={msg} expire={expire}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

