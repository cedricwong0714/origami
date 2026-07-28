# src/moclo_compiler/exceptions.py

class AssemblyError(Exception):
    """Base exception for MoClo assembly failures."""
    pass

class OverhangMismatchError(AssemblyError):
    """Raised when adjacent MoClo parts have incompatible 4-bp fusion sites."""
    def __init__(self, left_part_id: str, left_overhang: str, right_part_id: str, right_overhang: str):
        self.message = (
            f"Overhang mismatch between {left_part_id} (3' overhang: '{left_overhang}') "
            f"and {right_part_id} (5' overhang: '{right_overhang}')."
        )
        super().__init__(self.message)

class InvalidPartOrderError(AssemblyError):
    """Raised when the assembly sequence does not form a valid transcriptional unit."""
    pass