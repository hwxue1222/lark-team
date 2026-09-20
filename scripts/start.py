import signal
import sys
import threading
import asyncio
import socket
from pathlib import Path

import lark_oapi as lark
import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.kimi import KimiClient
from app.lark_client import LarkBotClient
from app.local_agent_client import LocalAgentClient
from app.logging_setup import setup_logging
from app.main import AccountantConfig, build_event_handler
from app.ws_client_patched import PatchedWSClient


def _run_http(*, host: str, port: int, log_level: str) -> None:
    uvicorn.run(
        "app.http_app:app",
        host=host,
        port=port,
        log_level=log_level.lower(),
        reload=False,
    )


def _can_bind(host: str, port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
        return True
    except OSError:
        return False


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    settings = get_settings()
    setup_logging(settings.log_level)

    missing = []
    if not settings.lark_app_id:
        missing.append("LARK_APP_ID")
    if not settings.lark_app_secret:
        missing.append("LARK_APP_SECRET")
    if not settings.kimi_api_key:
        missing.append("KIMI_API_KEY")
    if not settings.kimi_model:
        missing.append("KIMI_MODEL")
    if missing:
        raise SystemExit(f"missing env: {', '.join(missing)}")

    app_id_tail = settings.lark_app_id[-6:] if settings.lark_app_id else ""
    print(f"using LARK_DOMAIN={settings.lark_domain} LARK_APP_ID=***{app_id_tail}")

    if _can_bind(settings.http_host, settings.http_port):
        http_thread = threading.Thread(
            target=_run_http,
            kwargs={"host": settings.http_host, "port": settings.http_port, "log_level": settings.log_level},
            daemon=True,
        )
        http_thread.start()
    else:
        print(f"health server skipped: {settings.http_host}:{settings.http_port} already in use")

    kimi_client = KimiClient(api_key=settings.kimi_api_key, base_url=settings.kimi_base_url, model=settings.kimi_model)
    bot = LarkBotClient(app_id=settings.lark_app_id, app_secret=settings.lark_app_secret, domain=settings.lark_domain)

    local_agent = None
    if settings.local_agent_enabled and settings.local_agent_token:
        local_agent = LocalAgentClient(base_url=settings.local_agent_url, token=settings.local_agent_token)

    accountant = AccountantConfig(
        enabled=settings.accountant_enabled,
        base_url=settings.bby_accounting_base_url,
        email=settings.bby_accounting_email,
        password=settings.bby_accounting_password,
        org_id=settings.bby_accounting_org_id,
        operator_ids=settings.accountant_operator_ids,
        default_currency=settings.accountant_default_currency,
        default_fx_rate=settings.accountant_default_fx_rate,
    )

    handler = build_event_handler(
        bot=bot,
        kimi=kimi_client,
        bot_title=settings.bot_title,
        local_agent=local_agent,
        local_agent_operator_ids=settings.local_agent_operator_ids,
        accountant=accountant,
    )

    ws_client = PatchedWSClient(
        settings.lark_app_id,
        settings.lark_app_secret,
        log_level=lark.LogLevel.INFO,
        event_handler=handler,
        domain=settings.lark_domain,
        auto_reconnect=True,
    )

    import lark_oapi.ws.client as ws_client_module

    loop = ws_client_module.loop

    def _shutdown(*_args: object) -> None:
        if loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(ws_client._disconnect(), loop)
            except Exception:
                pass
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:
                pass
            return
        try:
            loop.run_until_complete(ws_client._disconnect())
        except Exception:
            pass
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    loop.run_until_complete(ws_client._connect())
    print("长连接已建立")
    print(f"health: http://127.0.0.1:{settings.http_port}/health")

    loop.create_task(ws_client._ping_loop())
    loop.run_until_complete(ws_client_module._select())


if __name__ == "__main__":
    main()
