from src.moclo_compiler.validate_moclo import validate_moclo


def test_missing_parts() -> None:
    errors = validate_moclo({"overhang_5": "ATGC", "overhang_3": "ATGC"})
    assert "missing parts" in errors


def test_overhang_length() -> None:
    errors = validate_moclo(
        {"part_ids": ["p1"], "overhang_5": "ATG", "overhang_3": "ATGC"}
    )
    assert any("overhang_5" in e for e in errors)


def test_ok() -> None:
    errors = validate_moclo(
        {"part_ids": ["p1"], "overhang_5": "ATGC", "overhang_3": "GGCC"}
    )
    assert errors == []
