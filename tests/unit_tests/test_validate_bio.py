from src.verification.validate_bio import validate_bio


def test_unknown_chassis() -> None:
    errors = validate_bio(
        {
            "chassis": "unknown_organism",
            "payloads": ["p1"],
            "parts": [{"part_id": "a", "allowlisted": True}],
        }
    )
    assert any("chassis unknown" in e for e in errors)


def test_missing_payloads() -> None:
    errors = validate_bio(
        {
            "chassis": "e_coli",
            "parts": [{"part_id": "a", "allowlisted": True}],
        }
    )
    assert any("payloads missing" in e for e in errors)


def test_not_allowlisted() -> None:
    errors = validate_bio(
        {
            "chassis": "e_coli",
            "payloads": ["p1"],
            "parts": [{"part_id": "a", "allowlisted": False}],
        }
    )
    assert any("not allowlisted" in e for e in errors)


def test_ok() -> None:
    errors = validate_bio(
        {
            "chassis": "e_coli",
            "payloads": ["p1"],
            "parts": [{"part_id": "a", "allowlisted": True}],
        }
    )
    assert errors == []
