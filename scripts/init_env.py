import argparse
from pathlib import Path
import shutil


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    src = root / ".env.example"
    dst = root / ".env"

    if not src.exists():
        raise SystemExit(f"missing template: {src}")
    if dst.exists() and not args.force:
        raise SystemExit(f"already exists: {dst} (use --force to overwrite)")

    shutil.copyfile(src, dst)
    print(f"created: {dst}")


if __name__ == "__main__":
    main()

