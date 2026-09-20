from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.account_aliases import expand_account_queries


@dataclass(frozen=True)
class Account:
    id: str
    code: str
    name: str


@dataclass(frozen=True)
class PostJournalResult:
    entry_id: str
    voucher_no: str | None
    status: str | None


@dataclass(frozen=True)
class Org:
    org_id: str
    org_name: str
    base_currency: str | None = None


class BBYAccountingClient:
    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        password: str,
        org_id: str | None = None,
        timeout_seconds: int = 20,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._email = email
        self._password = password
        self._org_id = org_id
        self._timeout = timeout_seconds
        self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout, follow_redirects=True)
        self._logged_in_at: float | None = None
        self._accounts_cache: dict[str, Account] | None = None

    def close(self) -> None:
        self._client.close()

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        r = self._client.post(path, json=payload, headers={"accept": "application/json"})
        data = self._must_json(r)
        if not data.get("success"):
            raise RuntimeError(f"bbyaccounting error: http={r.status_code} error={data.get('error')}")
        return data

    def _get_json(self, path: str) -> dict[str, Any]:
        r = self._client.get(path, headers={"accept": "application/json"})
        data = self._must_json(r)
        if not data.get("success"):
            raise RuntimeError(f"bbyaccounting error: http={r.status_code} error={data.get('error')}")
        return data

    def _must_json(self, r: httpx.Response) -> dict[str, Any]:
        try:
            data = r.json()
        except Exception:
            raise RuntimeError(f"bbyaccounting bad json: http={r.status_code}")
        if not isinstance(data, dict):
            raise RuntimeError(f"bbyaccounting bad json: http={r.status_code}")
        return data

    def ensure_logged_in(self) -> None:
        if self._logged_in_at and time.time() - self._logged_in_at < 60 * 30:
            return

        data = self._post_json("/api/auth/login", {"email": self._email, "password": self._password})
        _ = data.get("data")
        self._logged_in_at = time.time()

        if self._org_id:
            self.switch_org(org_id=self._org_id)
        self._accounts_cache = None

    def list_orgs(self) -> tuple[list[Org], str | None]:
        self.ensure_logged_in()
        data = self._get_json("/api/orgs")
        data_obj = data.get("data")
        orgs_raw = (data_obj.get("orgs") if isinstance(data_obj, dict) else None) or []
        active = (data_obj.get("activeOrgId") if isinstance(data_obj, dict) else None) or None
        out: list[Org] = []
        for o in orgs_raw:
            if not isinstance(o, dict):
                continue
            oid = str(o.get("orgId") or "")
            name = str(o.get("orgName") or "")
            base_currency = str(o.get("baseCurrency")) if o.get("baseCurrency") is not None else None
            if oid and name:
                out.append(Org(org_id=oid, org_name=name, base_currency=base_currency))
        return out, (str(active) if active else None)

    def switch_org(self, *, org_id: str) -> None:
        self.ensure_logged_in()
        self._post_json("/api/orgs/switch", {"orgId": org_id})
        self._org_id = org_id
        self._accounts_cache = None

    def list_accounts(self) -> list[Account]:
        self.ensure_logged_in()
        data = self._get_json("/api/settings/accounts")
        data_obj = data.get("data")
        accounts = (data_obj.get("accounts") if isinstance(data_obj, dict) else None) or []
        out: list[Account] = []
        for a in accounts:
            if not isinstance(a, dict):
                continue
            aid = str(a.get("id") or "")
            code = str(a.get("code") or "")
            name = str(a.get("name") or "")
            if aid and code:
                out.append(Account(id=aid, code=code, name=name))
        return out

    def _accounts_by_code(self) -> dict[str, Account]:
        if self._accounts_cache is not None:
            return self._accounts_cache
        m: dict[str, Account] = {}
        for a in self.list_accounts():
            m[a.code] = a
        self._accounts_cache = m
        return m

    def suggest_accounts(self, *, query: str, limit: int = 5) -> list[Account]:
        queries = expand_account_queries(query)
        if not queries:
            return []

        by_code = self._accounts_by_code()
        best: dict[str, tuple[int, Account]] = {}

        for q0 in queries:
            q = q0.strip().lower()
            if not q:
                continue
            for a in by_code.values():
                name = a.name.lower()
                code = a.code.lower()

                score = -10_000
                if q == code:
                    score = 10_000
                elif q == name:
                    score = 9_000
                elif name.startswith(q):
                    score = 7_000
                elif q in name:
                    score = 5_000
                elif code.startswith(q):
                    score = 4_000
                elif q in code:
                    score = 3_000
                else:
                    tokens = [t for t in q.replace("_", " ").replace("-", " ").split() if t]
                    if tokens:
                        hit = sum(1 for t in tokens if t in name)
                        if hit:
                            score = 1000 + hit * 100

                if score <= -10_000:
                    continue

                cur = best.get(a.id)
                if not cur or score > cur[0]:
                    best[a.id] = (score, a)

        scored = list(best.values())
        scored.sort(key=lambda x: (-x[0], x[1].code))
        return [a for _, a in scored[:limit]]

    def find_exact_account_id(self, *, account_ref: str) -> str | None:
        ref = (account_ref or "").strip()
        if not ref:
            return None

        by_code = self._accounts_by_code()
        a = by_code.get(ref)
        if a:
            return a.id

        ref_lower = ref.lower()
        for acct in by_code.values():
            if acct.name.lower() == ref_lower:
                return acct.id
        return None

    def post_journal(
        self,
        *,
        entry_date: str,
        currency: str,
        fx_rate: float,
        memo: str,
        lines: list[dict[str, Any]],
    ) -> PostJournalResult:
        self.ensure_logged_in()
        payload = {
            "entryDate": entry_date,
            "currency": currency,
            "fxRate": fx_rate,
            "memo": memo,
            "lines": lines,
        }
        data = self._post_json("/api/journals/post", payload)
        data_obj = data.get("data")
        entry = (data_obj.get("entry") if isinstance(data_obj, dict) else None) or {}
        if not isinstance(entry, dict):
            raise RuntimeError("bbyaccounting bad response: missing entry")
        return PostJournalResult(
            entry_id=str(entry.get("id") or ""),
            voucher_no=(str(entry.get("voucherNo")) if entry.get("voucherNo") is not None else None),
            status=(str(entry.get("status")) if entry.get("status") is not None else None),
        )

    def resolve_account_id(self, *, account_code: str) -> str:
        ref = (account_code or "").strip()
        if not ref:
            raise RuntimeError("missing account")

        by_code = self._accounts_by_code()
        for q in expand_account_queries(ref):
            a = by_code.get(q)
            if a:
                return a.id
            q_lower = q.lower()
            for acct in by_code.values():
                if acct.name.lower() == q_lower:
                    return acct.id

        suggestions = self.suggest_accounts(query=ref, limit=5)
        if len(suggestions) == 1:
            return suggestions[0].id
        if suggestions:
            names = ", ".join([f"{c.code}-{c.name}" for c in suggestions])
            raise RuntimeError(f"unknown account: {ref} suggestions={names}")
        raise RuntimeError(f"unknown account: {ref}")
