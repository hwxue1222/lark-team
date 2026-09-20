from pathlib import Path


def _fix_model_name(value: str) -> str:
    v = value.strip()
    v = v.replace("“", '"').replace("”", '"')
    if v.startswith('"') and v.endswith('"') and len(v) >= 2:
        inner = v[1:-1]
        if inner:
            return inner
    return v


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    env_path = root / ".env"
    if not env_path.exists():
        raise SystemExit(f"missing: {env_path}")

    lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[str] = []
    changed = False

    for line in lines:
        if line.lstrip().startswith("MODEL_NAME="):
            prefix, raw = line.split("=", 1)
            fixed = _fix_model_name(raw)
            if raw != fixed:
                changed = True
            out.append(f"{prefix}={fixed}")
        else:
            out.append(line)

    if not changed:
        print("no changes")
        return

    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")
    print(f"fixed: {env_path}")


if __name__ == "__main__":
    main()

