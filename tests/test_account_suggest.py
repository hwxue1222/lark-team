from app.bby_accounting_client import Account, BBYAccountingClient


def test_suggest_accounts_scores() -> None:
    c = BBYAccountingClient(base_url="http://localhost", email="a@b.com", password="x")
    try:
        c._accounts_cache = {
            "1000": Account(id="id1000", code="1000", name="Cash"),
            "2000": Account(id="id2000", code="2000", name="Amount Due To Director"),
            "3000": Account(id="id3000", code="3000", name="Sales"),
        }
        out = c.suggest_accounts(query="cash", limit=5)
        assert out
        assert out[0].code == "1000"
        out_cn = c.suggest_accounts(query="现金", limit=5)
        assert out_cn
        assert out_cn[0].code == "1000"
        assert c.find_exact_account_id(account_ref="现金") is None
        assert c.find_exact_account_id(account_ref="1000") == "id1000"
        assert c.find_exact_account_id(account_ref="Cash") == "id1000"
        out2 = c.suggest_accounts(query="director", limit=5)
        assert out2
        assert out2[0].code == "2000"
    finally:
        c.close()
