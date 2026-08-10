"""Payload role vocabulary and PayloadSpec (CLASP Docs §6)."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, List, Literal, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from src.core.schema import MechanismType


class PayloadRole(str, Enum):
    UPSTREAM_ENZYME = "upstream_enzyme"
    DOWNSTREAM_ENZYME = "downstream_enzyme"
    RECOGNITION_COMPONENT = "recognition_component"
    REPORTER_FRAGMENT = "reporter_fragment"
    REDOX_DONOR = "redox_donor"
    REDOX_ACCEPTOR = "redox_acceptor"
    COVALENT_TAG = "covalent_tag"
    COVALENT_CATCHER = "covalent_catcher"
    KINASE_DONOR = "kinase_donor"
    KINASE_ACCEPTOR = "kinase_acceptor"
    PROTEASE_EFFECTOR = "protease_effector"
    CLEAVAGE_TARGET = "cleavage_target"


DEFAULT_ROLE_ORDER: dict[str, list[PayloadRole]] = {
    "intermediate_transfer": [
        PayloadRole.UPSTREAM_ENZYME,
        PayloadRole.DOWNSTREAM_ENZYME,
    ],
    "target_complementation": [
        PayloadRole.RECOGNITION_COMPONENT,
        PayloadRole.REPORTER_FRAGMENT,
    ],
    "redox_transfer": [
        PayloadRole.REDOX_DONOR,
        PayloadRole.REDOX_ACCEPTOR,
    ],
    "covalent_capture": [
        PayloadRole.COVALENT_TAG,
        PayloadRole.COVALENT_CATCHER,
    ],
    "trans_activation": [
        PayloadRole.KINASE_DONOR,
        PayloadRole.KINASE_ACCEPTOR,
    ],
    "protease_cleavage": [
        PayloadRole.PROTEASE_EFFECTOR,
        PayloadRole.CLEAVAGE_TARGET,
    ],
}


class PayloadSpec(BaseModel):
    payload_id: str
    role: PayloadRole
    fusion_terminus: Literal["N", "C"] = "C"
    linker_id: str = "Linker_GGGGS3"
    functional_site: Optional[str] = None
    structure_id: Optional[str] = None
    approximate_radius_nm: float = Field(default=2.0, gt=0)


def infer_payloads_from_ids(mechanism_type: MechanismType, payload_ids: List[str]) -> List[PayloadSpec]:
    """Build PayloadSpec list from legacy IDs using mechanism-default role order."""
    roles = DEFAULT_ROLE_ORDER.get(mechanism_type.value, [])
    payloads: List[PayloadSpec] = []
    for i, pid in enumerate(payload_ids):
        role = roles[i] if i < len(roles) else (
            roles[-1] if roles else PayloadRole.RECOGNITION_COMPONENT
        )
        payloads.append(
            PayloadSpec(
                payload_id=pid,
                role=role,
                fusion_terminus="C",
                linker_id="Linker_GGGGS3",
            )
        )
    return payloads
