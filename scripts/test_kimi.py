import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings
from app.kimi import KimiClient


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    settings = get_settings()

    client = KimiClient(api_key=settings.kimi_api_key, base_url=settings.kimi_base_url, model=settings.kimi_model)
    res = client.infer_intent_and_reply(user_text="ping")
    print(res.intent)
    print(res.reply)


if __name__ == "__main__":
    main()

