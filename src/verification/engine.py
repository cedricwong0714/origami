# src/verification/engine.py
from src.core.schema import DesignSpec, MoCloPart, VerificationReport
from src.verification.layers.overhang import verify_overhangs
from src.verification.layers.mass_balance import verify_mass_conservation
from src.verification.layers.physical import verify_physical_bounds

def evaluate_design(
    spec: DesignSpec,
    parts: list[MoCloPart],
    initial_concentrations: dict[str, float]
) -> VerificationReport:
    """
    Runs multi-layer verification checks on a candidate design spec and returns a status report.
    """
    errors = []

    # Layer 1: Overhang Check
    overhang_ok, overhang_err = verify_overhangs(parts)
    if not overhang_ok and overhang_err:
        errors.append(overhang_err)

    # Layer 2: Mass Balance Check
    mass_ok, mass_err = verify_mass_conservation(initial_concentrations)
    if not mass_ok and mass_err:
        errors.append(mass_err)

    # Layer 3: Physical Constraints
    physical_ok, physical_errs = verify_physical_bounds(spec)
    if not physical_ok:
        errors.extend(physical_errs)

    overall_valid = overhang_ok and mass_ok and physical_ok

    return VerificationReport(
        design_id=spec.design_id,
        is_valid=overall_valid,
        overhang_check=overhang_ok,
        mass_balance_check=mass_ok,
        errors=errors
    )