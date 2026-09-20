import sys
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from local_agent.config import get_local_agent_settings


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    settings = get_local_agent_settings()
    uvicorn.run(
        "local_agent.app:app",
        host=settings.local_agent_host,
        port=settings.local_agent_port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()

