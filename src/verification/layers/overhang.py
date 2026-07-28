# src/verification/layers/overhang.py
from src.core.schema import MoCloPart
from src.moclo_compiler.assembly import assemble_level1_vector
from src.moclo_compiler.exceptions import AssemblyError

def verify_overhangs(parts: list[MoCloPart]) -> tuple[bool, str | None]:
    """
    Validates Golden Gate overhang compatibility across parts.
    Returns (True, None) if compatible, or (False, error_message) if mismatched.
    """
    try:
        assemble_level1_vector(parts)
        return True, None
    except AssemblyError as e:
        return False, str(e)