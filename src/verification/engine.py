# src/verification/engine.py
from __future__ import annotations

from typing import Optional

from src.compiler.expression_vector import ExpressionPlan
from src.compliance.models import VerificationLayerResult
from src.core.schema import (
    ControlPlan,
    DesignSpec,
    EvidenceMaturity,
    MechanismType,
    MoCloPart,
    VerificationReport,
)
from src.moclo_compiler.assembly import assemble_level1_vector
from src.ode_model.solver import run_system_simulation
from src.profiles.base import ProfilePrediction
from src.verification.layers.biological_plausibility import verify_biological_plausibility
from src.verification.layers.biosecurity import verify_safety_and_biosecurity
from src.verification.layers.model_consistency import verify_model_consistency
from src.verification.layers.reproducibility import verify_reproducibility
from src.verification.layers.sequence_integrity import verify_parts_sequences

MANDATORY_CONTROL_PLANS = {
    MechanismType.INTERMEDIATE_TRANSFER: ControlPlan(
        mandatory_control_type="Unscaffolded Mixture Control",
        description="Assay reaction rate using equimolar E1 and E2 without scaffold backbone.",
        expected_negative_signal="Baseline diffusion-limited product formation rate.",
    ),
    MechanismType.TARGET_COMPLEMENTATION: ControlPlan(
        mandatory_control_type="Non-Binding Target Mutant",
        description="Assay reporter complementation using target mutant lacking docking motif.",
        expected_negative_signal="Background self-assembly signal < 5% of wild-type.",
    ),
    MechanismType.REDOX_TRANSFER: ControlPlan(
        mandatory_control_type="Non-Functional Redox Partner",
        description="Replace active redox donor with redox-inactive alanine mutant.",
        expected_negative_signal="Zero measurable electron transfer current.",
    ),
    MechanismType.COVALENT_CAPTURE: ControlPlan(
        mandatory_control_type="Quenched / Non-Reactive Target",
        description="Pre-incubate target with blocking antibody or active-site inhibitor.",
        expected_negative_signal="Reversible binding observed without covalent adduct creation.",
    ),
    MechanismType.TRANS_ACTIVATION: ControlPlan(
        mandatory_control_type="Kinase-Dead Donor Mutant",
        description=(
            "Dock a catalytic-dead kinase donor at the same site to isolate "
            "proximity-driven trans-activation from monomeric background."
        ),
        expected_negative_signal="Phosphorylation drops to basal monomeric level.",
    ),
}


def evaluate_design(
    spec: DesignSpec,
    parts: list[MoCloPart],
    initial_concentrations: dict[str, float] | None = None,
    has_experimental_data: bool = False,
    expression_plan: Optional[ExpressionPlan] = None,
    prediction: Optional[ProfilePrediction] = None,
    profile_version: str = "unknown",
) -> VerificationReport:
    errors: list[str] = []
    initial_concentrations = initial_concentrations or {
        "S": 1.0,
        "E": 0.1,
        "ES": 0.0,
        "P": 0.0,
    }

    # Legacy layer checks (backward compatible flags)
    overhang_ok = True
    try:
        assemble_level1_vector(parts)
    except Exception as e:
        overhang_ok = False
        errors.append(f"MoClo Assembly Error: {e}")

    docking_ok = True
    for pos in spec.scaffold.docking_positions:
        if pos < 1 or pos > spec.scaffold.repeat_count:
            docking_ok = False
            errors.append(
                f"Docking position {pos} is out of bounds for CTPR repeat count "
                f"({spec.scaffold.repeat_count})."
            )

    mass_ok = True
    try:
        t, concs = run_system_simulation(
            initial_concentrations, mechanism_type=spec.mechanism_type
        )
        if len(t) == 0:
            mass_ok = False
            errors.append("ODE Integration returned empty output.")
    except Exception as e:
        mass_ok = False
        errors.append(f"ODE Integration failure: {e}")

    # AGENTS.md five-layer verification stack
    layers: list[VerificationLayerResult] = [
        verify_parts_sequences(parts),
        verify_biological_plausibility(spec),
        verify_model_consistency(prediction, model_version=profile_version),
        verify_safety_and_biosecurity(spec, parts, expression_plan=expression_plan),
        verify_reproducibility(profile_version, prediction=prediction),
    ]

    for layer in layers:
        for check in layer.checks:
            if check.severity == "error" and not check.passed:
                errors.append(f"[{layer.layer_name}] {check.message}")

    blocks_export = any(layer.blocks_export for layer in layers)
    layers_passed = all(layer.passed for layer in layers)

    maturity = (
        EvidenceMaturity.TIER_1_CALIBRATED
        if has_experimental_data
        else EvidenceMaturity.TIER_3_COMPUTATIONAL
    )
    control_plan = MANDATORY_CONTROL_PLANS.get(
        spec.mechanism_type,
        MANDATORY_CONTROL_PLANS[MechanismType.INTERMEDIATE_TRANSFER],
    )

    is_valid = overhang_ok and docking_ok and mass_ok and layers_passed and not blocks_export

    return VerificationReport(
        design_id=spec.design_id,
        mechanism_type=spec.mechanism_type,
        is_valid=is_valid,
        overhang_check=overhang_ok,
        mass_balance_check=mass_ok,
        docking_bounds_check=docking_ok,
        evidence_maturity=maturity,
        control_plan=control_plan,
        errors=errors,
        layers=layers,
        blocks_export=blocks_export,
    )
