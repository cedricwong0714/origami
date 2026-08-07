"""Trans-activation / phosphorylation-transfer profile.

Models proximity-induced trans-autophosphorylation and spatial enzymatic
activation for cell-signaling engineering (CLASP Docs §3.5).

Governing quantities:
- C_eff(r, σ²): effective local concentration from Gaussian-chain linker
  ensemble (src/core/linker_ensemble.py) as a function of scaffold
  separation r and linker variance σ².
- Inter-domain orientation (θ, φ): catalytic active-site alignment,
  folded into the trans-rate as an orientation factor (MVP: uniform).
- k_cat_trans vs k_cat_basal: proximity-induced vs monomeric rate.
- K_m saturation under spatial confinement.
- J_dephos: competitive dephosphorylation flux from soluble phosphatase.
- Scaffold occupancy and stoichiometry (src/core/calcium_kinetics.py).

Outputs:
- v_prox / v_basal: proximity-induced catalytic activation factor.
- f_phos: steady-state target phosphorylation fraction.
- r_opt: optimal spatial separation for trans-catalysis (from geometry).
- Threshold scaffold occupancy for signal activation.
- Signal-to-background ratio relative to monomeric activity.

Evidence target: Literature-parameterized, structurally evaluated
through MD, and benchmarked against experimental trans-autophosphorylation
assays. Current implementation is Tier-3 (computational baseline) until
calibrated values are deposited.
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


class TransActivationProfile(MechanismProfile):
    profile_id = "trans_activation"
    version = "1.0.0"
    mechanism_type = MechanismType.TRANS_ACTIVATION

    DEFAULT_PARAMS = {
        "k_cat_basal": 0.05,
        "k_cat_trans": 1.0,
        "k_on_prox": 1.0,
        "k_dephos": 0.1,
        "phosphatase_uM": 0.1,
    }

    def _params(self) -> dict[str, float]:
        try:
            return kinetic_params(self.mechanism_type.value)
        except FileNotFoundError:
            return dict(self.DEFAULT_PARAMS)

    def validate_inputs(self, design: DesignSpec) -> list[str]:
        errors: list[str] = []
        if design.mechanism_type != MechanismType.TRANS_ACTIVATION:
            errors.append(
                f"Profile {self.profile_id} requires mechanism_type="
                f"{MechanismType.TRANS_ACTIVATION.value}"
            )
        if len(design.payloads) < 2:
            errors.append(
                "Trans-activation requires ≥2 payloads (kinase donor + acceptor substrate)."
            )
        roles = {p.role for p in design.payloads}
        if design.payloads and PayloadRole.KINASE_DONOR not in roles:
            errors.append("Missing payload role kinase_donor.")
        if design.payloads and PayloadRole.KINASE_ACCEPTOR not in roles:
            errors.append("Missing payload role kinase_acceptor.")
        if len(design.scaffold.docking_positions) < 2:
            errors.append(
                "Scaffold must place kinase and substrate at ≥2 defined docking sites."
            )
        return errors

    def required_parameters(self, design: DesignSpec) -> list[str]:
        return [
            "k_cat_basal",
            "k_cat_trans",
            "k_on_prox",
            "k_dephos",
            "phosphatase_uM",
            "c_eff_mM",
        ]

    def build_model(self, design: DesignSpec) -> dict[str, Any]:
        return {
            "equations": (
                "dS/dt, dK/dt, dKS/dt, dSp/dt — basal + C_eff-driven trans "
                "phosphorylation with competitive dephosphorylation flux"
            ),
            "geometry_objective": "minimize active-site separation for trans-catalysis",
            "payload_roles": design.role_map(),
            "payloads": [p.model_dump() for p in design.payloads],
            "params": self._params(),
        }

    def _c_eff_mM(self, design: DesignSpec, ca2_free_M: float = 1e-5) -> float:
        """Effective local concentration from linker ensemble + geometry."""
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
        kinase = np.asarray(concs["E"])
        complex_ = np.asarray(concs["ES"])
        phosphorylated = np.asarray(concs["P"])

        f_phos = float(
            phosphorylated[-1] / max(substrate[-1] + phosphorylated[-1], 1e-12)
        )
        # v_prox / v_basal at peak trans-flux vs basal flux
        k_cat_trans = merged["k_cat_trans"]
        k_cat_basal = merged["k_cat_basal"]
        v_prox = float(k_cat_trans * np.max(complex_))
        v_basal = float(k_cat_basal * kinase[-1] * substrate[-1])
        activation_factor = float(v_prox / max(v_basal, 1e-12))
        signal_to_background = activation_factor

        occupancy = recruitment_occupancy(ca2_free_M).occupancy_fraction
        threshold_occupancy = 0.5  # MVP: half-occupancy activation threshold

        return ProfilePrediction(
            profile_id=self.profile_id,
            mechanism_type=self.mechanism_type,
            primary_metric_name="phosphorylation_fraction",
            primary_metric_value=f_phos,
            unit="dimensionless",
            uncertainty_95ci=(f_phos * 0.6, min(1.0, f_phos * 1.3)),
            evidence_maturity=self.assign_evidence_level(design),
            assumptions=[
                "Tier-3 computational defaults; no wet-lab calibration claimed",
                "Orientation factor treated as uniform (MVP) until MD-informed",
                "C_eff from Gaussian-chain linker ensemble drives proximity assembly",
                "Competitive phosphatase flux is first-order in phosphorylated substrate",
            ],
            warnings=[
                "Activation factor is a computational ranking until calibrated.",
                "Do not present f_phos as a clinical signaling readout.",
            ],
            details={
                "time_final": float(t[-1]),
                "params": merged,
                "activation_factor_v_prox_over_v_basal": activation_factor,
                "signal_to_background_ratio": signal_to_background,
                "scaffold_occupancy": occupancy,
                "threshold_occupancy_for_activation": threshold_occupancy,
                "c_eff_mM": merged["c_eff_mM"],
            },
        )

    def required_controls(self, design: DesignSpec) -> ControlPlan:
        return ControlPlan(
            mandatory_control_type="Kinase-Dead Donor Mutant",
            description=(
                "Replace kinase donor with catalytic-dead mutant (e.g. K→M in the "
                "HRD/DLK motif) at the same docking site to isolate proximity-driven "
                "activation from monomeric background."
            ),
            expected_negative_signal=(
                "Phosphorylation drops to basal monomeric autophosphorylation level."
            ),
        )

    def required_measurements(self, design: DesignSpec) -> list[str]:
        return [
            "Phospho-specific antibody or Phos-tag SDS-PAGE for f_phos",
            "Distance-series scaffold comparison (Δi sweep) to estimate r_opt",
            "Kinase-dead donor negative control",
            "Phosphatase titration to characterize J_dephos",
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
            "Fewer than 2 docking sites for kinase + substrate",
            "Phosphatase concentration exceeds kinase concentration (no signal)",
        ]
