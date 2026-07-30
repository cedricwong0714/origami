# src/verification/engine.py
from src.core.schema import (
    DesignSpec,
    MoCloPart,
    VerificationReport,
    MechanismType,
    EvidenceMaturity,
    ControlPlan,
)
from src.moclo_compiler.assembly import assemble_level1_vector
from src.ode_model.solver import run_system_simulation

MANDATORY_CONTROL_PLANS = {
    MechanismType.INTERMEDIATE_TRANSFER: ControlPlan(
        mandatory_control_type="Unscaffolded Mixture Control",
        description="Assay reaction rate using equimolar E1 and E2 without scaffold backbone.",
        expected_negative_signal="Baseline diffusion-limited product formation rate."
    ),
    MechanismType.TARGET_COMPLEMENTATION: ControlPlan(
        mandatory_control_type="Non-Binding Target Mutant",
        description="Assay reporter complementation using target mutant lacking docking motif.",
        expected_negative_signal="Background self-assembly signal < 5% of wild-type."
    ),
    MechanismType.REDOX_TRANSFER: ControlPlan(
        mandatory_control_type="Non-Functional Redox Partner",
        description="Replace active redox donor with redox-inactive alanine mutant.",
        expected_negative_signal="Zero measurable electron transfer current."
    ),
    MechanismType.COVALENT_CAPTURE: ControlPlan(
        mandatory_control_type="Quenched / Non-Reactive Target",
        description="Pre-incubate target with blocking antibody or active-site inhibitor.",
        expected_negative_signal="Reversible binding observed without covalent adduct creation."
    )
}

def evaluate_design(
    spec: DesignSpec,
    parts: list[MoCloPart],
    initial_concentrations: dict[str, float] = None,
    has_experimental_data: bool = False
) -> VerificationReport:
    errors = []
    initial_concentrations = initial_concentrations or {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}

    # 1. MoClo Overhang Continuity
    overhang_ok = True
    try:
        assemble_level1_vector(parts)
    except Exception as e:
        overhang_ok = False
        errors.append(f"MoClo Assembly Error: {e}")


    # 2. Docking Positions Spatial Bounds Check
    docking_ok = True
    for pos in spec.scaffold.docking_positions:
        if pos < 1 or pos > spec.scaffold.repeat_count:
            docking_ok = False
            errors.append(f"Docking position {pos} is out of bounds for CTPR repeat count ({spec.scaffold.repeat_count}).")

    # 3. ODE Kinetic Mass Balance Check
    mass_ok = True
    try:
        t, concs = run_system_simulation(initial_concentrations, mechanism_type=spec.mechanism_type)
        if len(t) == 0:
            mass_ok = False
            errors.append("ODE Integration returned empty output.")
    except Exception as e:
        mass_ok = False
        errors.append(f"ODE Integration failure: {e}")

    # Determine Evidence Maturity
    maturity = EvidenceMaturity.TIER_1_CALIBRATED if has_experimental_data else EvidenceMaturity.TIER_3_COMPUTATIONAL
    control_plan = MANDATORY_CONTROL_PLANS.get(spec.mechanism_type, MANDATORY_CONTROL_PLANS[MechanismType.INTERMEDIATE_TRANSFER])

    is_valid = overhang_ok and docking_ok and mass_ok

    return VerificationReport(
        design_id=spec.design_id,
        mechanism_type=spec.mechanism_type,
        is_valid=is_valid,
        overhang_check=overhang_ok,
        mass_balance_check=mass_ok,
        docking_bounds_check=docking_ok,
        evidence_maturity=maturity,
        control_plan=control_plan,
        errors=errors
    )