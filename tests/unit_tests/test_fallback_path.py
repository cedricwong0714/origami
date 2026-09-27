from src.compliance.fallback_path import fallback


def test_known_good() -> None:
    result = fallback({"known_good_id": "design-ok"})
    assert result["human_review_required"] is True
    assert "design-ok" in result["fallback_path"]


def test_explicit_failure() -> None:
    result = fallback({})
    assert result["human_review_required"] is True
    assert result["prediction"] is None
