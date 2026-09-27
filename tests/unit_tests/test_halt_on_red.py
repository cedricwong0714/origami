from src.verification.halt_on_red import halt_on_red


def test_stop_on_block() -> None:
    result = halt_on_red([{"status": "block"}])
    assert result["decision"] == "stop"


def test_stop_on_red_severity() -> None:
    result = halt_on_red([{"severity": "red"}])
    assert result["decision"] == "stop"


def test_proceed() -> None:
    result = halt_on_red([{"status": "pass"}, {"severity": "warning"}])
    assert result["decision"] == "proceed"
