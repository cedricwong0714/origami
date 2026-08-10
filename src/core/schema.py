# src/core/schema.py
from __future__ import annotations

from enum import Enum
from typing import List, Literal, Optional, Any

from pydantic import BaseModel, Field, model_validator

from src.core.schema_payloads import (
    DEFAULT_ROLE_ORDER,
    PayloadRole,
    PayloadSpec,
    infer_payloads_from_ids,
)


class MechanismType(str, Enum):
    INTERMEDIATE_TRANSFER = "intermediate_transfer"   # Reference (OtsA/OtsB)
    TARGET_COMPLEMENTATION = "target_complementation" # Split-reporter / biosensor
    REDOX_TRANSFER = "redox_transfer"                 # Electron transfer partners
    COVALENT_CAPTURE = "covalent_capture"             # Reversible -> Covalent
    TRANS_ACTIVATION = "trans_activation"             # Proximity-induced trans-phosphorylation
    PROTEASE_CLEAVAGE = "protease_cleavage"           # Proximity-dependent protease–substrate cleavage


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
    """
    Mechanism-aware design record (CLASP Docs §6).

    Prefer ``payloads: list[PayloadSpec]``. Legacy ``payload_ids`` remains
    accepted and is synchronized with ``payloads`` on validation.
    """

    design_id: str
    chassis: Literal["cell_free", "E_coli", "B_subtilis", "other"] = "E_coli"
    mechanism_type: MechanismType = MechanismType.INTERMEDIATE_TRANSFER
    sensor_id: str = "CaM_M13"
    scaffold: ScaffoldSpec
    payloads: List[PayloadSpec] = Field(default_factory=list)
    payload_ids: List[str] = Field(
        default_factory=list,
        description="Legacy convenience list; synced from/to payloads.",
    )
    reporter_id: Optional[str] = "NanoBiT"
    localization: str = "cytosol"
    operating_mode: Literal["reversible", "locking", "target_triggered"] = "reversible"

    @model_validator(mode="after")
    def _sync_payload_fields(self) -> DesignSpec:
        if self.payloads and not self.payload_ids:
            self.payload_ids = [p.payload_id for p in self.payloads]
        elif self.payload_ids and not self.payloads:
            self.payloads = infer_payloads_from_ids(self.mechanism_type, self.payload_ids)
        elif self.payloads and self.payload_ids:
            ids_from_payloads = [p.payload_id for p in self.payloads]
            if ids_from_payloads != list(self.payload_ids):
                # Explicit PayloadSpec list wins when both are provided inconsistently
                self.payload_ids = ids_from_payloads
        return self

    def role_map(self) -> dict[str, str]:
        return {p.payload_id: p.role.value for p in self.payloads}

    def payloads_with_role(self, role: PayloadRole) -> list[PayloadSpec]:
        return [p for p in self.payloads if p.role == role]


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
    layers: List[Any] = Field(default_factory=list)
    blocks_export: bool = False


# Re-export payload types for convenient imports from schema
__all__ = [
    "MechanismType",
    "EvidenceMaturity",
    "ControlPlan",
    "ScaffoldSpec",
    "MoCloPart",
    "PayloadRole",
    "PayloadSpec",
    "DEFAULT_ROLE_ORDER",
    "DesignSpec",
    "VerificationReport",
]
