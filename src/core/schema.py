# src/core/schema.py
from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field

class MechanismType(str, Enum):
    INTERMEDIATE_TRANSFER = "intermediate_transfer"   # Reference (OtsA/OtsB)
    TARGET_COMPLEMENTATION = "target_complementation" # Split-reporter / biosensor
    REDOX_TRANSFER = "redox_transfer"                 # Electron transfer partners
    COVALENT_CAPTURE = "covalent_capture"             # Reversible -> Covalent

class EvidenceMaturity(str, Enum):
    TIER_1_CALIBRATED = "Tier 1: Experimentally Calibrated"
    TIER_2_LITERATURE = "Tier 2: Literature Parameterized"
    TIER_3_COMPUTATIONAL = "Tier 3: Computational Baseline"

class ControlPlan(BaseModel):
    mandatory_control_type: str
    description: str
    expected_negative_signal: str

class ScaffoldSpec(BaseModel):
    scaffold_id: str
    repeat_count: int = Field(..., ge=1, le=20)
    # 1-based CTPR repeat indices in [1, repeat_count]
    docking_positions: List[int] = Field(..., min_length=1)
    persistence_length_nm: float = 15.0

class MoCloPart(BaseModel):
    part_id: str
    overhang_5prime: str = Field(..., min_length=4, max_length=4)
    overhang_3prime: str = Field(..., min_length=4, max_length=4)
    sequence: str

class DesignSpec(BaseModel):
    design_id: str
    chassis: str
    mechanism_type: MechanismType = MechanismType.INTERMEDIATE_TRANSFER
    scaffold: ScaffoldSpec
    payload_ids: List[str]
    operating_mode: str = "reversible"

class VerificationReport(BaseModel):
    design_id: str
    mechanism_type: MechanismType
    is_valid: bool
    overhang_check: bool
    mass_balance_check: bool
    docking_bounds_check: bool
    evidence_maturity: EvidenceMaturity
    control_plan: ControlPlan
    errors: List[str] = []