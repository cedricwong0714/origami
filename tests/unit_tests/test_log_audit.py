from src.compliance.log_audit import log_audit


def test_row_fields() -> None:
    row = log_audit({"action": "screen", "n": 1})
    assert "timestamp" in row
    assert "T" in row["timestamp"]
    assert row["event"]["action"] == "screen"
    assert len(row["id"]) == 64


def test_deterministic_id() -> None:
    a = log_audit({"x": 1})
    b = log_audit({"x": 1})
    assert a["id"] == b["id"]
