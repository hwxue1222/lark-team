import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.bby_accounting_client import BBYAccountingClient
from app.config import get_settings


def main() -> None:
    load_dotenv(dotenv_path=ROOT / ".env")
    s = get_settings()
    if not s.accountant_enabled:
        raise SystemExit("ACCOUNTANT_ENABLED is false")
    if not s.bby_accounting_email or not s.bby_accounting_password:
        raise SystemExit("missing BBY_ACCOUNTING_EMAIL/BBY_ACCOUNTING_PASSWORD")

    client = BBYAccountingClient(
        base_url=s.bby_accounting_base_url,
        email=s.bby_accounting_email,
        password=s.bby_accounting_password,
        org_id=(s.bby_accounting_org_id or None),
    )
    try:
        accounts = client.list_accounts()
        print(f"ok: base_url={s.bby_accounting_base_url} accounts={len(accounts)}")
        if accounts:
            a0 = accounts[0]
            print(f"sample account: code={a0.code} name={a0.name} id_tail=***{a0.id[-6:]}")
    finally:
        client.close()


if __name__ == "__main__":
    main()

