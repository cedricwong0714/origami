from src.verification.screen_sequence import screen_sequence


def test_empty_blocks() -> None:
    result = screen_sequence("", "dna")
    assert result["status"] == "block"


def test_invalid_dna_blocks() -> None:
    result = screen_sequence("ATGCZ", "dna")
    assert result["status"] == "block"


def test_valid_atgc_passes() -> None:
    result = screen_sequence("ATGCATGC", "dna")
    assert result["status"] == "pass"
    assert result["reasons"] == []


def test_bsai_motif_flags() -> None:
    # Motif copied from COMMON_FORBIDDEN_SITES / AGENTS.md: BsaI GGTCTC
    result = screen_sequence("ATGCGGTCTCATGC", "dna")
    assert result["status"] == "flag"


def test_invalid_protein_blocks() -> None:
    result = screen_sequence("ACDEF123", "protein")
    assert result["status"] == "block"


def test_valid_protein_passes() -> None:
    result = screen_sequence("ACDEFGHIKLMNPQRSTVWY", "protein")
    assert result["status"] == "pass"
