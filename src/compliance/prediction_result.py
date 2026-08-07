"""Standard prediction envelope (AGENTS.md §6)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from src.core.schema import EvidenceMaturity
from src.profiles.base import ProfilePrediction


class PredictionResult(BaseModel):
    """
    Standard output for any biological prediction.
    A bare numerical value without uncertainty is not acceptable.
    """

    predicted_value: float
    units: str
    uncertainty_95_lower: float
    uncertainty_95_upper: float
    confidence_tier: Literal[
        "validated",
        "interpolated",
        "extrapolated",
        "hypothesis_only",
    ]
    is_extrapolation: bool
    model_name: str
    model_version: str
    parameter_sources: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    human_review_required: bool = False
    most_sensitive_parameter: Optional[str] = None

    def display_summary(self) -> str:
        return (
            f"{self.predicted_value:.3f} {self.units} "
            f"[95% CI: {self.uncertainty_95_lower:.3f}–{self.uncertainty_95_upper:.3f}] "
            f"({self.confidence_tier})"
            + (" EXTRAPOLATION" if self.is_extrapolation else "")
            + (" HUMAN REVIEW REQUIRED" if self.human_review_required else "")
        )


_EVIDENCE_TO_TIER = {
    EvidenceMaturity.TIER_1_CALIBRATED: ("validated", False),
    EvidenceMaturity.TIER_2_LITERATURE: ("interpolated", False),
    EvidenceMaturity.TIER_3_COMPUTATIONAL: ("hypothesis_only", True),
}


def profile_prediction_to_result(prediction: ProfilePrediction) -> PredictionResult:
    """Adapt mechanism ``ProfilePrediction`` to AGENTS.md ``PredictionResult``."""
    tier, is_extrap = _EVIDENCE_TO_TIER.get(
        prediction.evidence_maturity,
        ("hypothesis_only", True),
    )
    lo, hi = prediction.uncertainty_95ci
    return PredictionResult(
        predicted_value=prediction.primary_metric_value,
        units=prediction.unit,
        uncertainty_95_lower=lo,
        uncertainty_95_upper=hi,
        confidence_tier=tier,
        is_extrapolation=is_extrap,
        model_name=prediction.profile_id,
        model_version=prediction.profile_id,
        parameter_sources=[f"models/kinetic_models/{prediction.mechanism_type.value}.defaults.json"],
        assumptions=list(prediction.assumptions),
        warnings=list(prediction.warnings),
        human_review_required=is_extrap,
    )


def assign_confidence_tier_from_maturity(
    evidence_maturity: EvidenceMaturity,
) -> tuple[str, bool]:
    """Map ORIGAMI evidence maturity enum to AGENTS confidence tier."""
    return _EVIDENCE_TO_TIER.get(evidence_maturity, ("hypothesis_only", True))
