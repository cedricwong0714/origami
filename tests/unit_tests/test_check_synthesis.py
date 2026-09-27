from src.verification.check_synthesis import check_synthesis


def test_long_flags() -> None:
    result = check_synthesis({"length": 10001})
    assert result["status"] == "flag"


def test_biosecurity_not_pass() -> None:
    result = check_synthesis({"biosecurity_status": "block"})
    assert result["status"] == "flag"


def test_pass() -> None:
    result = check_synthesis({"length": 100, "biosecurity_status": "pass"})
    assert result["status"] == "pass"
