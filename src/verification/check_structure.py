"""Local structure-confidence labels. Does not fetch PDB or run models."""

from __future__ import annotations

from typing import Literal


def check_structure(protein: dict) -> dict:
    """Return a confidence tier from local fields only.

    ``confidence`` is ``none`` if ``structure_id`` is absent. If present,
    ``plddt`` or ``confidence_score`` (0–100 scale if >1, else 0–1) maps to
    high / medium / low. Missing numeric score with a structure_id is medium.
    """
    structure_id = protein.get("structure_id")
    if structure_id is None or str(structure_id).strip() == "":
        return {"confidence": "none"}

    raw = protein.get("plddt")
    if raw is None:
        raw = protein.get("confidence_score")
    if raw is None:
        return {"confidence": "medium"}

    try:
        score = float(raw)
    except (TypeError, ValueError):
        return {"confidence": "low"}

    if score <= 1.0:
        score = score * 100.0
    tier: Literal["high", "medium", "low", "none"]
    if score >= 90.0:
        tier = "high"
    elif score >= 70.0:
        tier = "medium"
    else:
        tier = "low"
    return {"confidence": tier}
