import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.logging_setup import setup_logging
from app.ws_client_patched import PatchedWSClient


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    setup_logging(os.getenv("LOG_LEVEL", "INFO"))
    settings = get_settings()

    app_id_tail = settings.lark_app_id[-6:] if settings.lark_app_id else ""
    print(f"using LARK_DOMAIN={settings.lark_domain} LARK_APP_ID=***{app_id_tail}")

    missing = []
    if not settings.lark_app_id:
        missing.append("LARK_APP_ID")
    if not settings.lark_app_secret:
        missing.append("LARK_APP_SECRET")
    if missing:
        raise SystemExit(f"missing env: {', '.join(missing)}")

    import lark_oapi as lark
    import lark_oapi.ws.client as ws_client_module

    def on_any_event(_: object) -> None:
        print("received event")

    handler = lark.EventDispatcherHandler.builder("", "", lark.LogLevel.INFO).register_p2_customized_event(
        "im.message.receive_v1",
        on_any_event,
    ).build()

    ws_client = PatchedWSClient(
        settings.lark_app_id,
        settings.lark_app_secret,
        log_level=lark.LogLevel.INFO,
        event_handler=handler,
        domain=settings.lark_domain,
        auto_reconnect=True,
    )

    loop = ws_client_module.loop
    loop.run_until_complete(ws_client._connect())
    print("长连接已建立，等待事件...（此脚本只验证是否收到 im.message.receive_v1）")

    loop.create_task(ws_client._ping_loop())
    loop.run_until_complete(ws_client_module._select())


if __name__ == "__main__":
    main()
