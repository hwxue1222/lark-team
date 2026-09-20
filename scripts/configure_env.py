import getpass
from pathlib import Path


def _read_existing(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    data: dict[str, str] = {}
    for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        data[k.strip()] = v.strip()
    return data


def _quote_if_needed(value: str) -> str:
    if value == "":
        return value
    if any(ch.isspace() for ch in value) or "#" in value:
        escaped = value.replace('"', '\\"')
        return f'"{escaped}"'
    return value


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    existing = _read_existing(env_path)

    lark_app_id = input(f"LARK_APP_ID [{existing.get('LARK_APP_ID','')}]: ").strip() or existing.get("LARK_APP_ID", "")
    lark_app_secret = getpass.getpass("LARK_APP_SECRET (hidden): ").strip() or existing.get("LARK_APP_SECRET", "")
    moonshot_api_key = getpass.getpass("MOONSHOT_API_KEY (hidden): ").strip() or existing.get("MOONSHOT_API_KEY", "")
    model_name = input(f"MODEL_NAME [{existing.get('MODEL_NAME','')}]: ").strip() or existing.get("MODEL_NAME", "")

    data = {
        "LARK_APP_ID": lark_app_id,
        "LARK_APP_SECRET": lark_app_secret,
        "MOONSHOT_API_KEY": moonshot_api_key,
        "MODEL_NAME": model_name,
    }

    missing = [k for k, v in data.items() if not v]
    if missing:
        raise SystemExit(f"missing/empty: {', '.join(missing)}")

    lines = [
        "# Lark / Feishu",
        f"LARK_APP_ID={_quote_if_needed(data['LARK_APP_ID'])}",
        f"LARK_APP_SECRET={_quote_if_needed(data['LARK_APP_SECRET'])}",
        "",
        "# Kimi / Moonshot",
        f"MOONSHOT_API_KEY={_quote_if_needed(data['MOONSHOT_API_KEY'])}",
        f"MODEL_NAME={_quote_if_needed(data['MODEL_NAME'])}",
        "",
    ]
    env_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"saved: {env_path}")


if __name__ == "__main__":
    main()

