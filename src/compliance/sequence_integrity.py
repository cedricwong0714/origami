"""Sequence integrity utilities (AGENTS.md §5)."""

from __future__ import annotations

import hashlib
from typing import Optional

from src.compliance.models import (
    ForbiddenSiteResult,
    ReadingFrameResult,
    UnexpectedSequenceModificationError,
)

COMMON_FORBIDDEN_SITES = {
    "BsaI": "GGTCTC",
    "BsmBI": "CGTCTC",
    "BbsI": "GAAGAC",
    "EcoRI": "GAATTC",
    "SpeI": "ACTAGT",
    "XbaI": "TCTAGA",
    "PstI": "CTGCAG",
    "NotI": "GCGGCCGC",
}


def compute_sequence_checksum(sequence: str) -> str:
    """SHA-256 of normalized uppercase sequence."""
    normalized = sequence.upper().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def verify_sequence_unchanged(
    original: str,
    modified: str,
    operation_name: str,
) -> None:
    """Raise if sequence changed without explicit declaration."""
    original_checksum = compute_sequence_checksum(original)
    modified_checksum = compute_sequence_checksum(modified)
    if original_checksum != modified_checksum:
        raise UnexpectedSequenceModificationError(
            f"Operation '{operation_name}' changed the sequence without explicit "
            f"declaration. Original checksum: {original_checksum}. "
            f"Modified checksum: {modified_checksum}."
        )


def verify_reading_frame(
    sequence: str,
    expected_protein: Optional[str],
    sequence_id: str,
) -> ReadingFrameResult:
    """
    Verify coding sequence integrity when translation is expected.

    Non-coding parts (promoters/RBS) may skip strict frame checks when
    ``expected_protein`` is omitted and length is not divisible by 3.
    """
    seq = sequence.upper().strip()
    if len(seq) % 3 != 0:
        if expected_protein:
            return ReadingFrameResult(
                valid=False,
                error=(
                    f"Sequence '{sequence_id}' length {len(seq)} is not divisible by 3."
                ),
            )
        return ReadingFrameResult(
            valid=True,
            error=None,
            protein=None,
        )

    # Simple in-frame translation without BioPython dependency
    codon_table = {
        "TTT": "F", "TTC": "F", "TTA": "L", "TTG": "L",
        "TCT": "S", "TCC": "S", "TCA": "S", "TCG": "S",
        "TAT": "Y", "TAC": "Y", "TAA": "*", "TAG": "*",
        "TGT": "C", "TGC": "C", "TGA": "*", "TGG": "W",
        "CTT": "L", "CTC": "L", "CTA": "L", "CTG": "L",
        "CCT": "P", "CCC": "P", "CCA": "P", "CCG": "P",
        "CAT": "H", "CAC": "H", "CAA": "Q", "CAG": "Q",
        "CGT": "R", "CGC": "R", "CGA": "R", "CGG": "R",
        "ATT": "I", "ATC": "I", "ATA": "I", "ATG": "M",
        "ACT": "T", "ACC": "T", "ACA": "T", "ACG": "T",
        "AAT": "N", "AAC": "N", "AAA": "K", "AAG": "K",
        "AGT": "S", "AGC": "S", "AGA": "R", "AGG": "R",
        "GTT": "V", "GTC": "V", "GTA": "V", "GTG": "V",
        "GCT": "A", "GCC": "A", "GCA": "A", "GCG": "A",
        "GAT": "D", "GAC": "D", "GAA": "E", "GAG": "E",
        "GGT": "G", "GGC": "G", "GGA": "G", "GGG": "G",
    }
    protein = "".join(
        codon_table.get(seq[i : i + 3], "X") for i in range(0, len(seq), 3)
    )
    internal_stops = protein[:-1].count("*") if protein else 0
    if internal_stops > 0:
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' contains {internal_stops} internal stop codon(s)."
            ),
        )
    if expected_protein and protein[:-1] != expected_protein.rstrip("*"):
        return ReadingFrameResult(
            valid=False,
            error=(
                f"Sequence '{sequence_id}' translates unexpectedly. "
                f"Expected prefix {expected_protein[:20]}..., got {protein[:20]}..."
            ),
        )
    return ReadingFrameResult(valid=True, protein=protein)


def _reverse_complement(seq: str) -> str:
    comp = str.maketrans("ACGT", "TGCA")
    return seq.upper().translate(comp)[::-1]


def check_forbidden_sites(
    sequence: str,
    forbidden_sites: dict[str, str] | None = None,
    sequence_id: str = "unknown",
) -> ForbiddenSiteResult:
    """Detect common Type IIS / cloning restriction sites."""
    forbidden_sites = forbidden_sites or COMMON_FORBIDDEN_SITES
    seq_upper = sequence.upper()
    found: dict[str, dict] = {}

    for site_name, recognition_seq in forbidden_sites.items():
        positions: list[int] = []
        start = 0
        while True:
            pos = seq_upper.find(recognition_seq, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        rev = _reverse_complement(recognition_seq)
        start = 0
        while True:
            pos = seq_upper.find(rev, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
        if positions:
            found[site_name] = {
                "recognition_sequence": recognition_seq,
                "positions": sorted(positions),
            }

    return ForbiddenSiteResult(
        sequence_id=sequence_id,
        found_sites=found,
        passed=len(found) == 0,
    )
