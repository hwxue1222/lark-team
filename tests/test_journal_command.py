import pytest

from app.journal_command import format_journal_preview, parse_journal_command


def test_parse_journal_command_cn_json() -> None:
    cmd = parse_journal_command(
        '分录 {"entryDate":"2026-09-20","currency":"SGD","memo":"m","lines":[{"account":"6000","debit":10},{"account":"1000","credit":10}]}',
        default_currency="SGD",
        default_fx_rate=1,
    )
    assert cmd is not None
    assert cmd.entry_date == "2026-09-20"
    assert cmd.currency == "SGD"
    assert len(cmd.lines) == 2


def test_parse_journal_command_org_id() -> None:
    cmd = parse_journal_command(
        'je {"orgId":"11111111-1111-1111-1111-111111111111","memo":"m","lines":[{"account":"6000","debit":1},{"account":"1000","credit":1}]}',
        default_currency="SGD",
        default_fx_rate=1,
    )
    assert cmd is not None
    assert cmd.org_id == "11111111-1111-1111-1111-111111111111"


def test_parse_journal_command_requires_lines() -> None:
    with pytest.raises(ValueError):
        parse_journal_command('je {"memo":"x","lines":[]}', default_currency="SGD", default_fx_rate=1)


def test_parse_journal_command_freeform_cn() -> None:
    cmd = parse_journal_command(
        "分录，借方现金1000马币，贷方amount due to director",
        default_currency="SGD",
        default_fx_rate=1,
    )
    assert cmd is not None
    assert cmd.currency == "MYR"
    assert len(cmd.lines) == 2
    assert cmd.lines[0].account_code == "现金"
    assert cmd.lines[0].debit == 1000
    assert cmd.lines[1].account_code.lower() == "amount due to director"
    assert cmd.lines[1].credit == 1000


def test_format_journal_preview_account_override() -> None:
    cmd = parse_journal_command(
        "分录，借方现金1000马币，贷方amound to director",
        default_currency="SGD",
        default_fx_rate=1,
    )
    assert cmd is not None
    preview = format_journal_preview(
        cmd,
        account_label_overrides={
            0: "1000-Cash",
            1: "2020-Amount due to shareholder",
        },
    )
    assert "1000-Cash" in preview
    assert "2020-Amount due to shareholder" in preview
