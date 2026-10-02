"""Inter-day / inter-operator CV and GP observation noise from replicates.

Uses the same CV definition as ``origami.assay.window.coefficient_of_variation``.
Outputs are labeled unmeasured until the team posts real replicate tables.
"""

from __future__ import annotations

import math
from typing import Any

from origami.assay.window import coefficient_of_variation

Z95 = 1.96


def observation_sigma_from_cv(mean_signal: float, cv: float) -> float:
    """sigma_obs = |mean| * CV (homoscedastic approximation on the mean scale)."""
    if cv < 0:
        raise ValueError("cv must be non-negative")
    return abs(mean_signal) * cv


def uncertainty_budget(
    rlu_values: object,
    *,
    assay: str = "luminescence",
    source: str = "caller_replicates",
) -> dict[str, Any]:
    """CV from a replicate list and a suggested GP noise sigma at the sample mean."""
    cv_block = coefficient_of_variation(rlu_values)
    if not cv_block.get("computable"):
        return {
            "computable": False,
            "assay": assay,
            "calibrated": False,
            "missing": cv_block.get("missing", ["replicates"]),
            "source": source,
        }
    mean = float(cv_block["mean"])
    cv = float(cv_block["cv"])
    sigma = observation_sigma_from_cv(mean, cv)
    return {
        "computable": True,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "assay": assay,
        "source": source,
        "n_replicates": cv_block.get("n_points"),
        "mean_rlu": mean,
        "sample_sd_rlu": cv_block.get("sample_sigma"),
        "cv": cv,
        "cv_percent": 100.0 * cv,
        "suggested_sigma_obs_rlu": sigma,
        "suggested_sigma_95_half_width_rlu": Z95 * sigma,
        "note": (
            "Suggested sigma is mean × CV. Use measured replicates to replace "
            "placeholder CVs in data/config/active_learning_config.json."
        ),
    }


def pooled_cv_budget(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    """Combine several computable budgets (max CV wins for conservative noise)."""
    ok = [b for b in blocks if b.get("computable")]
    if not ok:
        return {
            "computable": False,
            "calibrated": False,
            "missing": ["no computable CV blocks"],
        }
    worst = max(ok, key=lambda b: float(b["cv"]))
    return {
        "computable": True,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "policy": "max_cv_across_blocks",
        "dominant_assay": worst.get("assay"),
        "cv": worst["cv"],
        "suggested_sigma_obs_rlu": worst.get("suggested_sigma_obs_rlu"),
        "blocks": ok,
    }
