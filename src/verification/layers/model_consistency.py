"""Layer 3 — model consistency (AGENTS.md §9.3)."""

from __future__ import annotations

from typing import Optional

from src.compliance.models import Check, VerificationLayerResult
from src.compliance.prediction_result import profile_prediction_to_result
from src.profiles.base import ProfilePrediction


def verify_model_consistency(
    prediction: Optional[ProfilePrediction],
    model_version: str = "unknown",
) -> VerificationLayerResult:
    checks: list[Check] = []
    if prediction is None:
        checks.append(
            Check(
                name="prediction_present",
                passed=False,
                message="No prediction available for model consistency check.",
                severity="warning",
            )
        )
        return VerificationLayerResult(
            layer=3,
            layer_name="model_consistency",
            checks=checks,
            passed=True,
        )

    result = profile_prediction_to_result(prediction)
    interval_width = result.uncertainty_95_upper - result.uncertainty_95_lower
    checks.append(
        Check(
            name="positive_prediction",
            passed=result.predicted_value >= 0,
            message=(
                f"Predicted value {result.predicted_value} is negative."
                if result.predicted_value < 0
                else "Predicted value is non-negative."
            ),
            severity="error" if result.predicted_value < 0 else "pass",
        )
    )
    checks.append(
        Check(
            name="valid_uncertainty_interval",
            passed=interval_width >= 0,
            message=(
                f"Uncertainty interval inverted: [{result.uncertainty_95_lower}, "
                f"{result.uncertainty_95_upper}]."
                if interval_width < 0
                else "Uncertainty interval is valid."
            ),
            severity="error" if interval_width < 0 else "pass",
        )
    )
    tier_extrapolation_consistent = (
        result.confidence_tier in ["extrapolated", "hypothesis_only"]
    ) == result.is_extrapolation
    checks.append(
        Check(
            name="tier_extrapolation_consistency",
            passed=tier_extrapolation_consistent,
            message=(
                "Confidence tier and extrapolation flag are inconsistent."
                if not tier_extrapolation_consistent
                else "Confidence tier and extrapolation flag consistent."
            ),
            severity="error" if not tier_extrapolation_consistent else "pass",
        )
    )
    checks.append(
        Check(
            name="model_version_recorded",
            passed=bool(model_version),
            message=(
                "Model version is not recorded."
                if not model_version
                else f"Model version: {model_version}."
            ),
            severity="warning" if not model_version else "pass",
        )
    )

    hard_fail = any(c.severity == "error" and not c.passed for c in checks)
    return VerificationLayerResult(
        layer=3,
        layer_name="model_consistency",
        checks=checks,
        passed=not hard_fail,
    )
