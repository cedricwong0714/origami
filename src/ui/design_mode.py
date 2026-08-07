"""
Design Mode — objective → geometry → prediction → construct → passport.

Uses the shared physical engine plus the correct mechanism profile, then
emits a Proximity Design Passport with uncertainty and evidence maturity.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from src.compiler.expression_vector import (
    ExpressionPlan,
    validate_expression_plan,
    verify_parts_against_allowlist,
)
from src.core.calcium_kinetics import recruitment_occupancy
from src.core.clasp_assembly import CLASPParameters, predict_luminescence
from src.core.ctpr_geometry import generate_scaffold_geometry
from src.core.linker_ensemble import compute_effective_concentration, parse_linker
from src.core.schema import DesignSpec, MoCloPart
from src.core.steric_checker import run_steric_check
from src.compliance.prediction_result import profile_prediction_to_result
from src.profiles import get_profile
from src.verification.engine import evaluate_design


class DesignMode:
    def run(
        self,
        spec: DesignSpec,
        parts: list[MoCloPart],
        expression_plan: Optional[ExpressionPlan] = None,
        ca2_free_M: float = 1e-5,
        linker_sequence: str = "(GGGGS)3",
        initial_concentrations: Optional[dict[str, float]] = None,
    ) -> dict[str, Any]:
        profile = get_profile(spec.mechanism_type)
        input_errors = profile.validate_inputs(spec)

        allowlist_report = verify_parts_against_allowlist([p.part_id for p in parts])
        if expression_plan is not None:
            expression_report = validate_expression_plan(expression_plan)
        else:
            expression_report = {
                "ok": True,
                "errors": [],
                "warnings": ["No ExpressionPlan provided; skipped coexpression checks."],
            }

        geometry = generate_scaffold_geometry(spec.scaffold)
        recruitment = recruitment_occupancy(ca2_free_M)

        linker = parse_linker(linker_sequence)
        distance_uncertainty_nm = None
        # Use first inter-site distance when ≥2 docking sites exist
        if len(geometry.docking_sites) >= 2:
            distance = geometry.get_inter_site_distance_nm(0, 1)
            distance_uncertainty_nm = geometry.get_inter_site_distance_uncertainty_nm(0, 1)
        else:
            distance = geometry.total_length_nm
        reach = compute_effective_concentration(linker, anchor_distance_nm=distance)

        # Anchor spheres for docking-site clash MVP (use PayloadSpec radii, capped for anchors)
        payload_positions = []
        for i, site in enumerate(geometry.docking_sites):
            if i < len(spec.payloads):
                payload = spec.payloads[i]
                label = f"{payload.payload_id}:{payload.role.value}"
                radius = min(0.8, float(payload.approximate_radius_nm) * 0.25)
            else:
                label = f"payload_{i}"
                radius = 0.5
            payload_positions.append((label, site.position_nm, radius))
        steric = run_steric_check(geometry, payload_positions)

        prediction = None
        if not input_errors:
            prediction = profile.predict(spec)

        # Stream 1 assembly dose-response (Docs-6 Layer 1) — shared physical engine
        ca_grid_M = np.logspace(-8, -4, 9)
        r_series = predict_luminescence(
            ca_grid_M, params=CLASPParameters(), E_T=1e-6, M_T=1e-6, t_end=1800.0
        )
        assembly_dose_response = {
            "calcium_M": [float(x) for x in ca_grid_M],
            "luminescence_RLU": [float(x) for x in r_series],
            "operating_ca2_M": float(ca2_free_M),
            "note": (
                "Mechanistic CLASP assembly ODE prediction (literature-parameterized). "
                "Not a wet-lab measurement. Hill n=4 ORIGAMI invariant."
            ),
        }

        verification = evaluate_design(
            spec,
            parts,
            initial_concentrations=initial_concentrations,
            expression_plan=expression_plan,
            prediction=prediction,
            profile_version=profile.version,
        )

        blocking = list(input_errors)
        blocking.extend(allowlist_report.get("errors", []))
        blocking.extend(expression_report.get("errors", []))
        warnings: list[str] = []
        warnings.extend(allowlist_report.get("warnings", []))
        warnings.extend(expression_report.get("warnings", []))
        if geometry.rigid_rod_warning:
            warnings.append(geometry.rigid_rod_warning)
        if not steric.is_feasible:
            warnings.append(
                "Steric check reported clashes (review geometry; not an automatic hard reject in MVP)."
            )
            warnings.extend(v.description for v in steric.violations)
        if not verification.is_valid:
            blocking.extend(verification.errors)

        passport = self._build_passport(
            spec=spec,
            profile=profile,
            geometry=geometry,
            recruitment=recruitment,
            reach=reach,
            steric=steric,
            prediction=prediction,
            verification=verification,
            allowlist_report=allowlist_report,
            expression_report=expression_report,
            blocking=blocking,
            warnings=warnings,
            inter_site_distance_nm=distance,
            inter_site_distance_uncertainty_nm=distance_uncertainty_nm,
        )

        return {
            "status": "SUCCESS" if not blocking else "REJECTED",
            "errors": blocking,
            "warnings": warnings,
            "geometry": geometry.model_dump(),
            "inter_site_distance_nm": distance,
            "inter_site_distance_uncertainty_nm": distance_uncertainty_nm,
            "recruitment": recruitment.model_dump(),
            "linker_reach": reach.model_dump(),
            "steric": steric.model_dump(),
            "prediction": prediction.model_dump() if prediction else None,
            "assembly_dose_response": assembly_dose_response,
            "verification_report": verification,
            "passport": passport,
        }

    def _build_passport(self, **ctx: Any) -> dict[str, Any]:
        spec: DesignSpec = ctx["spec"]
        profile = ctx["profile"]
        prediction = ctx["prediction"]
        verification = ctx["verification"]
        return {
            "design_objective": f"Apply {profile.profile_id} on chassis {spec.chassis}",
            "mechanism_profile": profile.profile_id,
            "profile_version": profile.version,
            "intended_use": spec.operating_mode,
            "sensor_id": spec.sensor_id,
            "reporter_id": spec.reporter_id,
            "localization": spec.localization,
            "payload_ids": list(spec.payload_ids),
            "payloads": [p.model_dump() for p in spec.payloads],
            "payload_roles": spec.role_map(),
            "scaffold_architecture": {
                "scaffold_id": spec.scaffold.scaffold_id,
                "repeat_count": spec.scaffold.repeat_count,
                "docking_positions": list(spec.scaffold.docking_positions),
            },
            "geometry_summary": {
                "total_length_nm": ctx["geometry"].total_length_nm,
                "is_rigid": ctx["geometry"].is_rigid,
                "n_docking_sites": len(ctx["geometry"].docking_sites),
                "wlc_end_to_end_rms_nm": ctx["geometry"].wlc_end_to_end_rms_nm,
                "inter_site_distance_nm": ctx.get("inter_site_distance_nm"),
                "inter_site_distance_uncertainty_nm": ctx.get(
                    "inter_site_distance_uncertainty_nm"
                ),
            },
            "recruitment_occupancy": ctx["recruitment"].occupancy_fraction,
            "linker_c_eff_mM": ctx["reach"].c_eff_mM,
            "steric_feasible": ctx["steric"].is_feasible,
            "predicted_output": prediction.model_dump() if prediction else None,
            "prediction_result": (
                profile_prediction_to_result(prediction).model_dump() if prediction else None
            ),
            "verification_layers": [layer.model_dump() for layer in verification.layers],
            "blocks_export": verification.blocks_export,
            "evidence_maturity": (
                prediction.evidence_maturity.value
                if prediction
                else verification.evidence_maturity.value
            ),
            "required_controls": profile.required_controls(spec).model_dump(),
            "required_measurements": profile.required_measurements(spec),
            "verification_is_valid": verification.is_valid,
            "allowlist": ctx["allowlist_report"],
            "expression_strategy": ctx["expression_report"],
            "biosecurity_review_state": (
                "pass_allowlist" if ctx["allowlist_report"].get("ok") else "blocked_unapproved_parts"
            ),
            "blocking_errors": ctx["blocking"],
            "warnings": ctx.get("warnings", []),
            "model_versions": {
                "profile": profile.version,
                "physical_engine": "ctpr+linker+steric+calcium+clasp_assembly_v1",
            },
        }


def design(
    spec: DesignSpec,
    parts: list[MoCloPart],
    **kwargs: Any,
) -> dict[str, Any]:
    return DesignMode().run(spec, parts, **kwargs)
