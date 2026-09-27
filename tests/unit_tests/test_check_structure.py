from src.verification.check_structure import check_structure


def test_none_without_id() -> None:
    assert check_structure({})["confidence"] == "none"


def test_high_plddt() -> None:
    result = check_structure({"structure_id": "local-1", "plddt": 95})
    assert result["confidence"] == "high"


def test_medium_without_score() -> None:
    result = check_structure({"structure_id": "local-1"})
    assert result["confidence"] == "medium"
