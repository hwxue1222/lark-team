from app.main import _parse_local_command, _parse_operator_allowlist


def test_parse_local_command_cn_open() -> None:
    assert _parse_local_command("本地 打开 https://example.com") == ("open_url", "https://example.com")


def test_parse_local_command_en_open() -> None:
    assert _parse_local_command("local open https://example.com") == ("open_url", "https://example.com")


def test_parse_local_command_non_local() -> None:
    assert _parse_local_command("打开 https://example.com") is None


def test_operator_allowlist() -> None:
    assert _parse_operator_allowlist("a,b , c") == {"a", "b", "c"}

