from src.compliance.run_tests import run_tests


def test_self_check_pass() -> None:
    result = run_tests("self-check")
    assert result["status"] == "pass"


def test_sandboxed_fail() -> None:
    result = run_tests("tests/unit_tests")
    assert result["status"] == "fail"
    assert "sandboxed" in result["reason"]
