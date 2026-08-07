"""Covalent-capture profile: SpyTag/SpyCatcher proximity locking."""

from __future__ import annotations

from typing import Any, Optional

from src.core.asset_paths import kinetic_params
from src.core.schema import ControlPlan, DesignSpec, EvidenceMaturity, MechanismType
from src.ode_model.solver import run_system_simulation
from src.profiles.base import MechanismProfile, ProfilePrediction


class CovalentCaptureProfile(MechanismProfile):
    profile_id = "covalent_capture"
    version = "1.0.0"
    mechanism_type = MechanismType.COVALENT_CAPTURE

    DEFAULT_PARAMS = {"k_bond": 2.0, "k_rev": 0.05}

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.COVALENT_CAPTURE:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.COVALENT_CAPTURE.value}"
            )
        if design.operating_mode not in {"locking", "reversible"}:
            errors.append("Covalent capture expects operating_mode='locking' (or reversible pre-lock).")
        if len(design.payload_ids) < 1:
            errors.append("At least one SpyTag-bearing payload is required.")
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return ["k_bond", "k_rev", "spy_reaction_distance_nm"]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        roles = {design.payload_ids[0]: "covalent_tag"}
        if len(design.payload_ids) > 1:
            roles[design.payload_ids[1]] = "covalent_catcher"
        return {
            "equations": "Reversible recruitment → irreversible isopeptide bond",
            "geometry_objective": "force SpyTag–SpyCatcher within reactive proximity after recruitment",
            "payload_roles": roles,
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
        locked = float(concs["P"][-1])
        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="covalent_adduct_fraction",
            primary_metric_value=locked,
            unit="dimensionless",
            uncertainty_95ci=(locked * 0.65, min(1.0, locked * 1.25)),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Isopeptide formation is effectively irreversible on assay timescale",
                "Recruitment (e.g. CaM–M13) precedes productive Spy encounter",
            ],
            details={"time_final": float(t[-1]), "params": merged},
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Quenched / Non-Reactive Target",
            description="Blocking antibody, EGTA (no recruitment), or non-reactive SpyTag mutant.",
            expected_negative_signal="Reversible binding without covalent adduct on SDS-PAGE.",
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "SDS-PAGE / Western shift for covalent adduct",
            "Post-chelation luminescence retention (>80% if locked)",
            "No-SpyTag or no-SpyCatcher negative control",
        ]

    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        if has_experimental_data:
            return EvidenceMaturity.TIER_1_CALIBRATED
        return EvidenceMaturity.TIER_2_LITERATURE
