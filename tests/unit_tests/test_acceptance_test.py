from src.compliance.acceptance_test import acceptance_test


def test_marker_pass() -> None:
    result = acceptance_test("known-plasmid-checksums-ok")
    assert result["status"] == "pass"


def test_export_sequence_fails() -> None:
    result = acceptance_test("please export sequence")
    assert result["status"] == "fail"


def test_other_fails() -> None:
    result = acceptance_test("anything else")
    assert result["status"] == "fail"
