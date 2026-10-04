"""One-page JSON passport for a chassis evaluation. Not a wet-lab certificate."""

from __future__ import annotations

from typing import Any

from origami.export.constructs import ConstructError, construct_for_n
from origami.ssdk.chassis import ChassisError, evaluate_chassis


def chassis_passport(body: dict[str, Any]) -> dict[str, Any]:
    report = evaluate_chassis(body)
    n_repeats = int(report["n_repeats"])
    sequence_block: dict[str, Any] | None
    try:
        row = construct_for_n(n_repeats)
        sequence_block = {
            "construct_id": row["construct_id"],
            "sequence_sha256": row["sequence_sha256"],
            "length_aa": row["length_aa"],
            "camsol_intrinsic_score": row["camsol_intrinsic_score"],
            "camsol_pH": row["camsol_pH"],
            "wet_lab_intended": row["wet_lab_intended"],
        }
    except ConstructError:
        sequence_block = None
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "evidence_maturity": "computationally_evaluated",
        "n_repeats": n_repeats,
        "structure": {
            "contour_nm": report["structure"]["contour_nm"],
            "axial_span_A": report["structure"]["axial_span_A"],
            "rigid_screw": report["structure"]["rigid_screw"],
        },
        "stability": {
            "tm_C": report["stability"]["tm_C"],
            "delta_g": report["stability"]["delta_g"],
            "source": "Phillips 2012 CTPRa DSC length model",
        },
        "docking": {
            "clash_computable": report["docking"].get("clash_computable"),
        },
        "kinetics": {
            "computable": report["kinetics"].get("computable"),
        },
        "team_construct": sequence_block,
        "honesty_note": (
            "This passport is a software snapshot. A filled sequence checksum "
            "is not a validated clone. CamSol is dry. Phillips ΔG is the length "
            "curve, not a melt of this fusion."
        ),
    }
