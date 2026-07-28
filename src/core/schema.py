# src/core/schema.py
from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class MoCloPart(BaseModel):
    model_config = ConfigDict(frozen=True)
    part_id: str
    overhang_5prime: str = Field(min_length=4, max_length=4)
    overhang_3prime: str = Field(min_length=4, max_length=4)
    sequence: str

    @field_validator("sequence")
    @classmethod
    def validate_dna_sequence(cls, v: str) -> str:
        v_upper = v.upper()
        if not set(v_upper).issubset(set("ATCG")):
            raise ValueError("Sequence contains non-canonical nucleotides.")
        return v_upper

class ScaffoldSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    scaffold_id: str
    repeat_count: int = Field(gt=0)
    docking_positions: list[int]
    persistence_length_nm: float = Field(default=15.0, ge=0.0)

class DesignSpec(BaseModel):
    model_config = ConfigDict(frozen=True)
    design_id: str
    chassis: Literal["cell_free", "E_coli", "B_subtilis"]
    scaffold: ScaffoldSpec
    payload_ids: list[str] = Field(min_length=1)
    operating_mode: Literal["reversible", "locking"]

class VerificationReport(BaseModel):
    design_id: str
    is_valid: bool
    overhang_check: bool
    mass_balance_check: bool
    errors: list[str] = Field(default_factory=list)