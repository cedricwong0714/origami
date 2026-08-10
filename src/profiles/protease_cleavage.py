"""Protease–substrate cleavage profile.

Models proximity-dependent recruitment of a protease effector to a
cleavage target on a CTPR scaffold (CLASP Docs §8).

Governing quantities:
- C_eff(r, σ²): effective local concentration from Gaussian-chain linker
  ensemble as a function of scaffold separation.
- k_cat_basal vs k_cat_prox: 3D diffusion vs scaffolded cleavage rate.
- k_nonspecific: off-target / background cleavage (default 0 at Tier-3).

Outputs:
- cleaved_fraction at end of simulation horizon
- enrichment of proximity vs basal cleavage flux
- scaffold occupancy context from Ca²⁺ recruitment

Evidence target: Literature-parameterized and benchmarked against
cleavage assays. Current implementation is Tier-3 (computational
baseline) until calibrated values are deposited.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from src.core.asset_paths import kinetic_params
from src.core.calcium_kinetics import recruitment_occupancy
from src.core.linker_ensemble import compute_effective_concentration, parse_linker
from src.core.schema import (
    ControlPlan,
    DesignSpec,
    EvidenceMaturity,
    MechanismType,
    PayloadRole,
)
from src.ode_model.solver import run_system_simulation
from src.profiles.base import MechanismProfile, ProfilePrediction


class ProteaseCleavageProfile(MechanismProfile):
    profile_id = "protease_cleavage"
    version = "1.0.0"
    mechanism_type = MechanismType.PROTEASE_CLEAVAGE

    DEFAULT_PARAMS = {
        "k_cat_basal": 0.05,
        "k_cat_prox": 1.0,
        "k_on_prox": 1.0,
        "k_nonspecific": 0.0,
    }

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.PROTEASE_CLEAVAGE:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.PROTEASE_CLEAVAGE.value}"
            )
        if len(design.payloads) < 2:
            errors.append(
                "Protease cleavage requires ≥2 payloads "
                "(protease_effector + cleavage_target)."
            )
        roles = {p.role for p in design.payloads}
        if design.payloads and PayloadRole.PROTEASE_EFFECTOR not in roles:
            errors.append("Missing payload role protease_effector.")
        if design.payloads and PayloadRole.CLEAVAGE_TARGET not in roles:
            errors.append("Missing payload role cleavage_target.")
        if len(design.scaffold.docking_positions) < 2:
            errors.append(
                "Scaffold must place protease and target at ≥2 defined docking sites."
            )
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return [
            "k_cat_basal",
            "k_cat_prox",
            "k_on_prox",
            "k_nonspecific",
            "c_eff_mM",
        ]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        return {
            "equations": (
                "dS/dt, dE/dt, dES/dt, dP/dt — basal + C_eff-driven "
                "proximity cleavage with optional nonspecific term"
            ),
            "geometry_objective": "place cleavage site within protease reach without steric clash",
            "payload_roles": design.role_map(),
            "payloads": [p.model_dump() for p in design.payloads],
            "params": self._params(),
        }

    def _c_eff_mM(self, design: DesignSpec, ca2_free_M: float = 1e-5) -> float:
        from src.core.ctpr_geometry import generate_scaffold_geometry

        geometry = generate_scaffold_geometry(design.scaffold)
        if len(geometry.docking_sites) >= 2:
            distance = geometry.get_inter_site_distance_nm(0, 1)
        else:
            distance = geometry.total_length_nm
        linker = parse_linker("Linker_GGGGS3")
        reach = compute_effective_concentration(linker, anchor_distance_nm=distance)
        return float(reach.c_eff_mM)

    def predict(
        self,
        design: DesignSpec,
        params: Optional[dict[str, float]] = None,
        ca2_free_M: float = 1e-5,
    ) -> ProfilePrediction:
        model = self.build_model(design)
        merged = {**model["params"], **(params or {})}
        merged["c_eff_mM"] = merged.get("c_eff_mM", self._c_eff_mM(design, ca2_free_M))
        merged["k_on_prox"] = merged.get("k_on_prox", merged["c_eff_mM"])

        initial = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}
        t, concs = run_system_simulation(
            initial,
            mechanism_type=self.mechanism_type,
            params=merged,
        )
        substrate = np.asarray(concs["S"])
        protease = np.asarray(concs["E"])
        complex_ = np.asarray(concs["ES"])
        cleaved = np.asarray(concs["P"])

        cleaved_fraction = float(
            cleaved[-1] / max(substrate[-1] + cleaved[-1], 1e-12)
        )
        k_cat_prox = merged["k_cat_prox"]
        k_cat_basal = merged["k_cat_basal"]
        v_prox = float(k_cat_prox * np.max(complex_))
        v_basal = float(k_cat_basal * protease[-1] * substrate[-1])
        enrichment = float(v_prox / max(v_basal, 1e-12))

        occupancy = recruitment_occupancy(ca2_free_M).occupancy_fraction

        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="cleaved_fraction",
            primary_metric_value=cleaved_fraction,
            unit="dimensionless",
            uncertainty_95ci=(cleaved_fraction * 0.6, min(1.0, cleaved_fraction * 1.3)),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Tier-3 computational defaults; no wet-lab calibration claimed",
                "C_eff from Gaussian-chain linker ensemble drives proximity assembly",
                "k_nonspecific defaults to 0 unless a sourced off-target rate is supplied",
                "Circuit-switch / signal-processing framing — not a therapeutic claim",
            ],
            warnings=[
                "Cleavage enrichment is a computational ranking until calibrated.",
                "Do not present cleaved_fraction as a clinical or diagnostic endpoint.",
            ],
            details={
                "time_final": float(t[-1]),
                "params": merged,
                "enrichment_v_prox_over_v_basal": enrichment,
                "scaffold_occupancy": occupancy,
                "c_eff_mM": merged["c_eff_mM"],
            },
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Catalytic-Dead Protease / Uncleavable Target",
            description=(
                "Replace the protease with a catalytic-dead mutant at the same "
                "docking site, and/or use an uncleavable target mutant, to isolate "
                "proximity-driven cleavage from basal and nonspecific background."
            ),
            expected_negative_signal=(
                "Cleavage drops to basal monomeric (or zero for uncleavable target) levels."
            ),
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "Cleavage-product gel / Western or FRET reporter for cleaved_fraction",
            "Distance-series scaffold comparison (Δi sweep)",
            "Catalytic-dead protease negative control",
            "Uncleavable target negative control",
            "Ca²⁺-chelation (EGTA) control for scaffold occupancy dependence",
        ]

    def assign_evidence_level(
        self,
        design: DesignSpec,
        has_experimental_data: bool = False,
    ) -> EvidenceMaturity:
        if has_experimental_data:
            return EvidenceMaturity.TIER_1_CALIBRATED
        return EvidenceMaturity.TIER_3_COMPUTATIONAL

    def failure_conditions(self, design: DesignSpec) -> list[str]:
        return [
            "Unsupported payload outside approved-parts allowlist",
            "Geometry/steric check fails shared physical engine",
            "Evidence retrieval confidence below refusal threshold",
            "Fewer than 2 docking sites for protease + target",
            "Nonspecific cleavage dominates proximity signal (no enrichment)",
        ]
