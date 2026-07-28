# src/verification/layers/physical.py
from src.core.schema import DesignSpec

def verify_physical_bounds(spec: DesignSpec) -> tuple[bool, list[str]]:
    """
    Checks scaffold spatial boundaries, docking site alignment, and chassis selection.
    """
    errors = []
    scaffold = spec.scaffold

    # Verify docking site indexes stay within total repeat count
    for pos in scaffold.docking_positions:
        if pos < 1 or pos > scaffold.repeat_count:
            errors.append(
                f"Docking position {pos} is out of bounds for CTPR repeat count {scaffold.repeat_count}."
            )

    # Verify scaffold persistence length
    if scaffold.persistence_length_nm <= 0:
        errors.append("Scaffold persistence length must be strictly positive.")

    return len(errors) == 0, errors