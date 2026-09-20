from __future__ import annotations

import re


def _has_cjk(s: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in (s or ""))


_ALIASES: list[tuple[re.Pattern[str], list[str]]] = [
    (re.compile(r"^现金$"), ["cash", "cash on hand", "petty cash"]),
    (re.compile(r"现金|库存现金"), ["cash", "cash on hand", "petty cash"]),
    (re.compile(r"银行|银行存款"), ["bank", "cash at bank", "bank balance"]),
    (re.compile(r"应收账款|应收"), ["accounts receivable", "trade receivables", "receivable"]),
    (re.compile(r"应付账款|应付"), ["accounts payable", "trade payables", "payable"]),
    (re.compile(r"应付董事|欠董事|董事往来"), ["amount due to director", "due to director", "director"]),
    (re.compile(r"应收董事|董事应收"), ["amount due from director", "due from director", "director"]),
    (re.compile(r"收入|营业收入"), ["revenue", "sales"]),
    (re.compile(r"成本|营业成本"), ["cost of sales", "cogs"]),
    (re.compile(r"办公费|办公室"), ["office expense", "office supplies"]),
    (re.compile(r"运费"), ["freight", "delivery"]),
    (re.compile(r"水电费"), ["utilities", "electricity", "water"]),
    (re.compile(r"租金|房租"), ["rent"]),
    (re.compile(r"工资|薪金"), ["salary", "wages", "payroll"]),
]


def expand_account_queries(query: str) -> list[str]:
    q = (query or "").strip()
    if not q:
        return []

    out: list[str] = [q]
    for pat, alts in _ALIASES:
        if pat.search(q):
            out.extend(alts)

    if _has_cjk(q):
        q2 = re.sub(r"\s+", " ", q)
        if q2 != q:
            out.append(q2)

    seen: set[str] = set()
    uniq: list[str] = []
    for s in out:
        v = s.strip()
        if not v:
            continue
        key = v.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(v)
    return uniq

