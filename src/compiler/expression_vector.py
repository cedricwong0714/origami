"""
Expression / coexpression strategy checks.

CLASP requires coordinated expression of scaffold and payload constructs.
A single pET28a+ ORF strategy is rejected for full systems.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

_ALLOWLIST_PATH = Path(__file__).with_name("approved_parts.json")


class ExpressionPlan(BaseModel):
    """How scaffold and payload ORFs will be hosted."""

    scaffold_vector_id: str
    payload_vector_ids: list[str] = Field(..., min_length=1)
    coexpression_strategy: str = Field(
        ...,
        description="dual_cassette | dual_plasmid | operon | other",
    )


def load_allowlist(path: Optional[Path] = None) -> dict[str, Any]:
    allowlist_path = path or _ALLOWLIST_PATH
    with allowlist_path.open(encoding="utf-8") as fh:
        return json.load(fh)


def _part_index(allowlist: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {p["part_id"]: p for p in allowlist.get("parts", [])}


def verify_parts_against_allowlist(
    part_ids: list[str],
    sequences_by_id: Optional[dict[str, str]] = None,
    allowlist: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Biosecurity gate: every compiled part ID must appear on the allowlist.
    When a sequence is provided for a verified_short_part, checksum must match.
    """
    allowlist = allowlist or load_allowlist()
    index = _part_index(allowlist)
    sequences_by_id = sequences_by_id or {}
    errors: list[str] = []
    warnings: list[str] = []

    for part_id in part_ids:
        if part_id not in index:
            errors.append(f"Part '{part_id}' is not on the approved-parts allowlist.")
            continue
        meta = index[part_id]
        status = meta.get("sequence_status", "reference_only")
        if status == "reference_only":
            warnings.append(
                f"Part '{part_id}' is allowlisted by ID only; deposit checksummed DNA before synthesis."
            )
        seq = sequences_by_id.get(part_id) or meta.get("sequence") or ""
        expected = meta.get("checksum_sha256") or ""
        if seq and expected:
            digest = hashlib.sha256(seq.encode("utf-8")).hexdigest()
            if digest != expected:
                errors.append(
                    f"Checksum mismatch for '{part_id}': sequence failed allowlist verification."
                )

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "checked_part_ids": list(part_ids),
    }


def validate_expression_plan(
    plan: ExpressionPlan,
    allowlist: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """
    Reject single-ORF pET28a+ as the sole strategy for scaffold + payload systems.
    """
    allowlist = allowlist or load_allowlist()
    forbidden = {v.lower() for v in allowlist.get("forbidden_solo_vectors", [])}
    errors: list[str] = []
    warnings: list[str] = []

    vectors = [plan.scaffold_vector_id, *plan.payload_vector_ids]
    vectors_l = [v.lower() for v in vectors]

    # Hard reject: everything on a single forbidden solo vector
    unique = set(vectors_l)
    if len(unique) == 1 and next(iter(unique)) in forbidden:
        errors.append(
            "Rejected: scaffold and payloads cannot all be hosted on a single "
            f"{plan.scaffold_vector_id} (pET28a+ solo strategy is forbidden for CLASP)."
        )

    if plan.coexpression_strategy not in {
        "dual_cassette",
        "dual_plasmid",
        "operon",
        "other",
    }:
        errors.append(
            f"Unknown coexpression_strategy '{plan.coexpression_strategy}'. "
            "Use dual_cassette, dual_plasmid, operon, or other."
        )

    if plan.coexpression_strategy == "other":
        warnings.append("coexpression_strategy='other' requires manual biosafety review.")

    # Soft require: at least one dedicated coexpression vector ID when using dual strategies
    if plan.coexpression_strategy in {"dual_cassette", "dual_plasmid"}:
        if plan.scaffold_vector_id.lower() in forbidden and all(
            v.lower() in forbidden for v in plan.payload_vector_ids
        ):
            errors.append(
                "dual_cassette/dual_plasmid strategy still resolves to forbidden solo vector IDs."
            )

    # Allowlist vector IDs when present in catalog
    index = _part_index(allowlist)
    for vid in vectors:
        if vid in index and index[vid].get("category") not in {"vector", None}:
            warnings.append(f"'{vid}' is allowlisted but not categorized as a vector.")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "plan": plan.model_dump(),
    }
