"""Layer 1 — sequence integrity (AGENTS.md §9.1)."""

from __future__ import annotations

from typing import Optional

from src.compliance.models import Check, VerificationLayerResult
from src.compliance.sequence_integrity import (
    check_forbidden_sites,
    compute_sequence_checksum,
    verify_reading_frame,
)
from src.core.schema import MoCloPart


def verify_sequence_integrity(
    sequence: str,
    sequence_id: str,
    expected_length: Optional[int] = None,
    expected_protein: Optional[str] = None,
) -> VerificationLayerResult:
    checks: list[Check] = []
    valid_bases = set("ATCGatcgNn")
    invalid = [c for c in sequence if c not in valid_bases]
    checks.append(
        Check(
            name="valid_alphabet",
            passed=len(invalid) == 0,
            message=(
                f"Invalid characters found: {set(invalid)}"
                if invalid
                else "Valid nucleotide alphabet."
            ),
            severity="error" if invalid else "pass",
        )
    )

    if expected_length is not None:
        ok = len(sequence) == expected_length
        checks.append(
            Check(
                name="length_check",
                passed=ok,
                message=(
                    f"Length {len(sequence)} does not match expected {expected_length}."
                    if not ok
                    else f"Length {len(sequence)} correct."
                ),
                severity="error" if not ok else "pass",
            )
        )

    frame_result = verify_reading_frame(sequence, expected_protein, sequence_id)
    checks.append(
        Check(
            name="reading_frame",
            passed=frame_result.valid,
            message=frame_result.error or "Reading frame valid.",
            severity="error" if not frame_result.valid else "pass",
        )
    )

    site_result = check_forbidden_sites(sequence, sequence_id=sequence_id)
    checks.append(
        Check(
            name="forbidden_sites",
            passed=site_result.passed,
            message=(
                f"Forbidden sites found: {site_result.found_sites}"
                if not site_result.passed
                else "No forbidden sites detected."
            ),
            severity="warning" if not site_result.passed else "pass",
        )
    )

    return VerificationLayerResult(
        layer=1,
        layer_name="sequence_integrity",
        checks=checks,
        passed=all(c.passed for c in checks),
        checksum=compute_sequence_checksum(sequence),
    )


def verify_parts_sequences(parts: list[MoCloPart]) -> VerificationLayerResult:
    """Run layer 1 across all MoClo parts with sequences."""
    checks: list[Check] = []
    for part in parts:
        if not part.sequence:
            checks.append(
                Check(
                    name=f"sequence_present_{part.part_id}",
                    passed=True,
                    message=f"No sequence supplied for '{part.part_id}' (reference-only OK).",
                    severity="pass",
                )
            )
            continue
        layer = verify_sequence_integrity(part.sequence, part.part_id)
        for check in layer.checks:
            checks.append(
                Check(
                    name=f"{part.part_id}:{check.name}",
                    passed=check.passed,
                    message=check.message,
                    severity=check.severity,
                )
            )
    hard_fail = any(c.severity == "error" and not c.passed for c in checks)
    return VerificationLayerResult(
        layer=1,
        layer_name="sequence_integrity",
        checks=checks,
        passed=not hard_fail,
    )
