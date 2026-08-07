"""ORIGAMI Mechanism Profile Standard — shared interface for all functional profiles."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from pydantic import BaseModel, Field

from src.core.schema import ControlPlan, DesignSpec, EvidenceMaturity, MechanismType


class ProfilePrediction(BaseModel):
    """Standardized prediction payload returned by every mechanism profile."""

    profile_id: str
    mechanism_type: MechanismType
    primary_metric_name: str
    primary_metric_value: float
    unit: str
    uncertainty_95ci: tuple[float, float]
    evidence_maturity: EvidenceMaturity
    assumptions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class MechanismProfile(ABC):
    """
    Complete, testable mechanism package.

    A new profile cannot be added by writing another LLM prompt — it must
    supply equations, controls, measurements, and evidence thresholds.
    """

    profile_id: str
    version: str
    mechanism_type: MechanismType

    @abstractmethod
    def validate_inputs(self, design: DesignSpec) -> list[str]:
        """Return human-readable errors; empty list means inputs are acceptable."""

    @abstractmethod
    def required_parameters(self, design: DesignSpec) -> list[str]:
        """Parameter keys that must be resolved from evidence or defaults."""

    @abstractmethod
    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        """Construct mechanism-specific model configuration / rate parameters."""

    @abstractmethod
    def predict(self, design: DesignSpec, params: Optional[dict[str, float]] = None) -> ProfilePrediction:
        """Run the functional model and return a standardized prediction."""

    @abstractmethod
    def required_controls(self, design: DesignSpec) -> ControlPlan:
        """Mandatory negative/positive controls for wet-lab validation."""

    @abstractmethod
    def required_measurements(self, design: DesignSpec) -> list[str]:
        """Assays required to score this profile honestly."""

    @abstractmethod
    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        """Tiered evidence maturity (never a single undifferentiated 'validated')."""

    def failure_conditions(self, design: DesignSpec) -> list[str]:
        """Documented conditions under which the profile must refuse or warn."""
        return [
            "Unsupported payload outside approved-parts allowlist",
            "Geometry/steric check fails shared physical engine",
            "Evidence retrieval confidence below refusal threshold",
        ]
