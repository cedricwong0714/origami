"""Intermediate-transfer profile: OtsA → OtsB trehalose pathway (reference application)."""

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


class TrehaloseSynthesisProfile(MechanismProfile):
    profile_id = "trehalose_synthesis"
    version = "1.0.0"
    mechanism_type = MechanismType.INTERMEDIATE_TRANSFER

    DEFAULT_PARAMS = {
        "k_cat1": 0.5,
        "k_cat2": 0.8,
        "k_channel": 5.0,
        "k_escape": 0.1,
    }

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.INTERMEDIATE_TRANSFER:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.INTERMEDIATE_TRANSFER.value}"
            )
        if len(design.payloads) < 2:
            errors.append("Intermediate transfer requires ≥2 payloads (upstream + downstream enzyme).")
        roles = {p.role for p in design.payloads}
        if design.payloads and PayloadRole.UPSTREAM_ENZYME not in roles:
            errors.append("Missing payload role upstream_enzyme.")
        if design.payloads and PayloadRole.DOWNSTREAM_ENZYME not in roles:
            errors.append("Missing payload role downstream_enzyme.")
        if len(design.scaffold.docking_positions) < 2:
            errors.append("Scaffold must expose ≥2 docking sites for sequential enzymes.")
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return ["k_cat_OtsA", "k_cat_OtsB", "k_channel", "k_escape"]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        return {
            "equations": "dS/dt, dI_chan/dt, dI_bulk/dt, dP/dt (substrate channeling ODE)",
            "geometry_objective": "minimize active-site separation for T6P handoff",
            "payload_roles": design.role_map(),
            "payloads": [p.model_dump() for p in design.payloads],
            "params": self._params(),
        }

    def predict(self, design: DesignSpec, params: Optional[dict[str, float]] = None) -> ProfilePrediction:
        model = self.build_model(design)
        merged = {**model["params"], **(params or {})}
        initial = {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0}
        t, concs = run_system_simulation(
            initial,
            mechanism_type=self.mechanism_type,
            params=merged,
        )
        product_final = float(concs["P"][-1])
        lo, hi = product_final * 0.7, min(1.0, product_final * 1.3)
        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="trehalose_yield_fraction",
            primary_metric_value=product_final,
            unit="dimensionless",
            uncertainty_95ci=(lo, hi),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Gaussian-chain linker model",
                "Literature k_cat values unless experimentally calibrated",
                "Bulk escape competes with channeling",
            ],
            details={"time_final": float(t[-1]), "params": merged, "payload_roles": design.role_map()},
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Unscaffolded Mixture Control",
            description="Equimolar OtsA/OtsB without CTPR scaffold; same Ca2+ and substrate.",
            expected_negative_signal="Diffusion-limited trehalose titre; no Ca2+-dependent boost.",
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "Megazyme trehalose enzymatic kit (or equivalent)",
            "NanoBiT luminescence (assembly confirmation)",
            "Host growth / OD600 (biological burden penalty)",
        ]

    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        if has_experimental_data:
            return EvidenceMaturity.TIER_1_CALIBRATED
        return EvidenceMaturity.TIER_2_LITERATURE
