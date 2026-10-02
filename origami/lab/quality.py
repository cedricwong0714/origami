"""Phase 3 calibration and quality sections (vacant until posted).

Each subsection is computable only when the caller supplies numbers.
Nothing is invented from literature here.
"""

from __future__ import annotations

from typing import Any

from origami.assay.window import admissibility, fit_standard_curve
from origami.lab.uncertainty_budget import pooled_cv_budget, uncertainty_budget


def run_quality(body: dict[str, Any]) -> dict[str, Any]:
    """Evaluate optional Phase 3 quality/calibration blocks."""
    out: dict[str, Any] = {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "sections": {},
    }
    if not body:
        out["note"] = "quality section omitted"
        return out

    if "inter_day_rlu" in body:
        out["sections"]["inter_day_cv"] = uncertainty_budget(
            body["inter_day_rlu"], assay="luminescence", source="inter_day"
        )
    if "inter_operator_rlu" in body:
        out["sections"]["inter_operator_cv"] = uncertainty_budget(
            body["inter_operator_rlu"], assay="luminescence", source="inter_operator"
        )

    cv_blocks = [
        v
        for k, v in out["sections"].items()
        if k.endswith("_cv") and isinstance(v, dict)
    ]
    if cv_blocks:
        out["pooled_gp_noise"] = pooled_cv_budget(cv_blocks)

    if "normalization_a_rlu" in body and "normalization_b_rlu" in body:
        a, b = float(body["normalization_a_rlu"]), float(body["normalization_b_rlu"])
        out["sections"]["normalization_ratio"] = {
            "computable": b != 0,
            "ratio": a / b if b != 0 else None,
            "calibrated": False,
            "note": "Caller-defined normalization methods A vs B.",
        }

    if "fluo3_free_ca_M" in body:
        out["sections"]["fluo3_free_ca"] = {
            "computable": True,
            "free_ca_M": float(body["fluo3_free_ca_M"]),
            "calibrated": False,
            "note": "Compare to titrated [Ca2+] in calcium dose-response.",
        }

    if "background_rlu" in body and "expressed_rlu" in body:
        bg, ex = float(body["background_rlu"]), float(body["expressed_rlu"])
        out["sections"]["background_vs_expression"] = {
            "computable": True,
            "signal_to_background": ex / bg if bg != 0 else None,
            "calibrated": False,
        }

    if "linearity_amount" in body and "linearity_rlu" in body:
        out["sections"]["linearity"] = fit_standard_curve(
            body["linearity_amount"], body["linearity_rlu"]
        )

    if "check_rlu" in body or "rlu_low" in body:
        out["sections"]["linear_range_check"] = admissibility(
            body.get("check_rlu"),
            body.get("rlu_low"),
            body.get("rlu_high"),
        )

    if "freeze_thaw_rlu" in body:
        out["sections"]["freeze_thaw_cv"] = uncertainty_budget(
            body["freeze_thaw_rlu"], assay="luminescence", source="freeze_thaw"
        )

    if "lysis_soluble_fraction" in body:
        out["sections"]["lysis"] = {
            "computable": True,
            "soluble_fraction": float(body["lysis_soluble_fraction"]),
            "calibrated": False,
        }

    if "negative_control_rlu" in body:
        vals = body["negative_control_rlu"]
        if isinstance(vals, list) and vals:
            mx = max(float(v) for v in vals)
            out["sections"]["negative_panel"] = {
                "computable": True,
                "max_rlu": mx,
                "n_controls": len(vals),
                "calibrated": False,
            }

    if "competitor_fold" in body and "complex_fraction_after_h" in body:
        out["sections"]["irreversibility"] = {
            "computable": True,
            "competitor_fold": float(body["competitor_fold"]),
            "complex_fraction_after_h": float(body["complex_fraction_after_h"]),
            "reversal_observed": float(body["complex_fraction_after_h"]) > 0.05,
            "calibrated": False,
            "note": "Spy irreversibility: Zakeri 2012 saw no reversal with 20× competitor overnight.",
        }

    if "plate_reader_reference_rlu" in body:
        out["sections"]["instrument_calibration"] = {
            "computable": True,
            "reference_rlu": float(body["plate_reader_reference_rlu"]),
            "calibrated": False,
        }

    return out
