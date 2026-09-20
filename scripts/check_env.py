import sys
from pathlib import Path

from dotenv import dotenv_values


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"

    print(f"cwd: {Path.cwd()}")
    print(f"env_path: {env_path}")
    print(f"env_exists: {env_path.exists()}")
    if not env_path.exists():
        raise SystemExit("missing .env file")

    values = dotenv_values(env_path)
    required_any = {
        "KIMI_API_KEY": ["KIMI_API_KEY", "MOONSHOT_API_KEY"],
        "KIMI_MODEL": ["KIMI_MODEL", "MODEL_NAME"],
    }
    required = ["LARK_APP_ID", "LARK_APP_SECRET"]

    for k in required:
        v = values.get(k)
        print(f"{k}: present={v is not None} nonempty={bool(v)}")

    for logical, candidates in required_any.items():
        present = any(values.get(c) for c in candidates)
        print(f"{logical}: ok={present} candidates={candidates}")

    missing = [k for k in required if not values.get(k)]
    missing_any = [logical for logical, candidates in required_any.items() if not any(values.get(c) for c in candidates)]
    if missing or missing_any:
        raise SystemExit(f"missing/empty: {', '.join(missing + missing_any)}")

    model_name = (values.get("KIMI_MODEL") or values.get("MODEL_NAME") or "")
    if "“" in model_name or "”" in model_name:
        raise SystemExit("KIMI_MODEL/MODEL_NAME contains smart quotes: replace “ ” with normal double quotes \" \"")

    accountant_enabled = str(values.get("ACCOUNTANT_ENABLED") or "").lower() in {"1", "true", "yes", "on"}
    if accountant_enabled:
        for k in ["BBY_ACCOUNTING_EMAIL", "BBY_ACCOUNTING_PASSWORD"]:
            v = values.get(k)
            print(f"{k}: present={v is not None} nonempty={bool(v)}")
        missing_acc = [k for k in ["BBY_ACCOUNTING_EMAIL", "BBY_ACCOUNTING_PASSWORD"] if not values.get(k)]
        if missing_acc:
            raise SystemExit(f"ACCOUNTANT_ENABLED=true but missing/empty: {', '.join(missing_acc)}")

    print("ok")


if __name__ == "__main__":
    main()
