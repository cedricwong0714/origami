"""Redox electron-transfer profile: proximity-organized donor/acceptor pairs."""

from __future__ import annotations

from typing import Any, Optional

from src.core.asset_paths import kinetic_params
from src.core.schema import (
    ControlPlan,
    DesignSpec,
    EvidenceMaturity,
    MechanismType,
    PayloadRole,
)
from src.ode_model.solver import run_system_simulation
from src.profiles.base import MechanismProfile, ProfilePrediction


class RedoxTransferProfile(MechanismProfile):
    profile_id = "redox_transfer"
    version = "1.0.0"
    mechanism_type = MechanismType.REDOX_TRANSFER

    DEFAULT_PARAMS = {"k_et": 3.0, "k_leak": 0.2}

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.REDOX_TRANSFER:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.REDOX_TRANSFER.value}"
            )
        if len(design.payloads) < 2:
            errors.append("Redox transfer requires donor and acceptor payloads.")
        roles = {p.role for p in design.payloads}
        if design.payloads and PayloadRole.REDOX_DONOR not in roles:
            errors.append("Missing payload role redox_donor.")
        if design.payloads and PayloadRole.REDOX_ACCEPTOR not in roles:
            errors.append("Missing payload role redox_acceptor.")
        if len(design.scaffold.docking_positions) < 2:
            errors.append("Scaffold must place donor and acceptor at defined sites.")
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return ["k_et", "k_leak", "edge_to_edge_distance_nm"]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        return {
            "equations": "Marcus-inspired relative electron-transfer ranking (not absolute H2 titre)",
            "geometry_objective": "minimize edge-to-edge distance between redox centers",
            "payload_roles": design.role_map(),
            "payloads": [p.model_dump() for p in design.payloads],
            "params": self._params(),
        }

    def predict(self, design: DesignSpec, params: Optional[dict[str, float]] = None) -> ProfilePrediction:
        model = self.build_model(design)
        merged = {**model["params"], **(params or {})}
        initial = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}
        t, concs = run_system_simulation(
            initial,
            mechanism_type=self.mechanism_type,
            params=merged,
        )
        transferred = float(concs["P"][-1])
        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="relative_electron_transfer_score",
            primary_metric_value=transferred,
            unit="relative",
            uncertainty_95ci=(transferred * 0.5, transferred * 1.5),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Literature-parameterized relative ranking only",
                "Does not claim calibrated hydrogen output without wet-lab calibration",
            ],
            warnings=["Do not interpret primary metric as absolute H2 production rate."],
            details={"time_final": float(t[-1]), "params": merged},
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Non-Functional Redox Partner",
            description="Replace active redox donor with redox-inactive alanine mutant.",
            expected_negative_signal="Zero measurable productive electron transfer.",
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "Spectrophotometric redox partner turnover or H2 headspace (if claimed)",
            "Distance-series scaffold comparison",
            "Inactive-partner negative control",
        ]

    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        if has_experimental_data:
            return EvidenceMaturity.TIER_1_CALIBRATED
        return EvidenceMaturity.TIER_3_COMPUTATIONAL
