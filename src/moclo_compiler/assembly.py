# src/moclo_compiler/assembly.py
from src.core.schema import MoCloPart
from src.moclo_compiler.exceptions import OverhangMismatchError, InvalidPartOrderError

def assemble_level1_vector(parts: list[MoCloPart]) -> str:
    """
    Validates 4-bp fusion overhang continuity across adjacent MoClo parts
    and concatenates their DNA sequences into a Level 1 construct.
    
    Args:
        parts: List of MoCloPart schema instances ordered 5' -> 3'.
        
    Returns:
        The concatenated DNA sequence string.
        
    Raises:
        InvalidPartOrderError: If fewer than 2 parts are provided.
        OverhangMismatchError: If adjacent overhangs are not complementary.
    """
    if len(parts) < 2:
        raise InvalidPartOrderError("A minimum of 2 Level 0 parts is required for Level 1 assembly.")

    full_sequence = parts[0].sequence

    for i in range(len(parts) - 1):
        left = parts[i]
        right = parts[i + 1]

        # Enforce exact 4-bp fusion overhang match
        if left.overhang_3prime.upper() != right.overhang_5prime.upper():
            raise OverhangMismatchError(
                left_part_id=left.part_id,
                left_overhang=left.overhang_3prime,
                right_part_id=right.part_id,
                right_overhang=right.overhang_5prime
            )

        full_sequence += right.sequence

    return full_sequence