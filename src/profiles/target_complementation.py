"""Target-induced complementation profile: cell-free / screening-assay split reporters."""

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


class TargetComplementationProfile(MechanismProfile):
    profile_id = "target_complementation"
    version = "1.0.0"
    mechanism_type = MechanismType.TARGET_COMPLEMENTATION

    DEFAULT_PARAMS = {"k_on": 10.0, "k_off": 1.0, "k_rec": 2.0}

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.TARGET_COMPLEMENTATION:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.TARGET_COMPLEMENTATION.value}"
            )
        if design.chassis not in {"cell_free", "E_coli"}:
            errors.append("Target complementation MVP supports cell_free or E_coli chassis only.")
        if design.operating_mode not in {"reversible", "target_triggered"}:
            errors.append("Operating mode should be reversible or target_triggered for this profile.")
        if len(design.payloads) < 1:
            errors.append("At least one recognition/reporter payload is required.")
        roles = {p.role for p in design.payloads}
        if design.payloads and not roles.intersection(
            {PayloadRole.RECOGNITION_COMPONENT, PayloadRole.REPORTER_FRAGMENT}
        ):
            errors.append("Expected recognition_component and/or reporter_fragment payload roles.")
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return ["k_on", "k_off", "k_rec", "nanobit_max_distance_nm"]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        return {
            "equations": "Target-bridged fragment association → reconstituted reporter",
            "geometry_objective": "keep LgBiT–SmBiT distance ≤ 3.0 nm when target is bound",
            "payload_roles": design.role_map(),
            "payloads": [p.model_dump() for p in design.payloads],
            "params": self._params(),
            "claim_boundary": "screening-assay proof of concept — not a clinical diagnostic",
        }

    def predict(self, design: DesignSpec, params: Optional[dict[str, float]] = None) -> ProfilePrediction:
        model = self.build_model(design)
        merged = {**model["params"], **(params or {})}
        initial = {"S": 0.5, "E": 1.0, "E2": 1.0, "ES": 0.0, "P": 0.0}
        t, concs = run_system_simulation(
            initial,
            mechanism_type=self.mechanism_type,
            params=merged,
        )
        active = float(concs["P"][-1])
        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="reconstituted_reporter_fraction",
            primary_metric_value=active,
            unit="dimensionless",
            uncertainty_95ci=(active * 0.6, min(1.0, active * 1.4)),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Target binding is required for productive complementation",
                "Intrinsic LgBiT–SmBiT affinity alone is insufficient (Kd ≈ 190 µM)",
            ],
            warnings=[model["claim_boundary"]],
            details={"time_final": float(t[-1]), "params": merged},
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Non-Binding Target Mutant",
            description="Assay with target mutant lacking docking motif / aptamer epitope.",
            expected_negative_signal="Background self-assembly signal < 5% of wild-type.",
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "Luminescence dose–response to target",
            "No-target and mutant-target backgrounds",
            "Time-to-signal at fixed target concentration",
        ]

    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        if has_experimental_data:
            return EvidenceMaturity.TIER_1_CALIBRATED
        return EvidenceMaturity.TIER_3_COMPUTATIONAL
