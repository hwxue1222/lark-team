import sys
from pathlib import Path

from dotenv import dotenv_values
from openai import OpenAI


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    values = dotenv_values(env_path)

    api_key = values.get("MOONSHOT_API_KEY") or ""
    model_name = values.get("MODEL_NAME") or ""
    base_url = values.get("MOONSHOT_BASE_URL") or "https://api.moonshot.ai/v1"

    if not api_key:
        raise SystemExit("missing/empty: MOONSHOT_API_KEY")
    if not model_name:
        raise SystemExit("missing/empty: MODEL_NAME")
    if "“" in model_name or "”" in model_name:
        raise SystemExit("MODEL_NAME contains smart quotes: replace “ ” with normal double quotes")

    client = OpenAI(api_key=api_key, base_url=base_url)
    try:
        models = client.models.list()
    except Exception as e:
        print(f"base_url: {base_url}")
        print(f"auth_test: failed ({type(e).__name__})")
        print(str(e))
        raise SystemExit(1)

    ids = []
    for m in getattr(models, "data", [])[:10]:
        mid = getattr(m, "id", None)
        if mid:
            ids.append(mid)

    print(f"base_url: {base_url}")
    print("auth_test: ok")
    if ids:
        print("sample_models:")
        for mid in ids:
            print(f"- {mid}")


if __name__ == "__main__":
    main()

