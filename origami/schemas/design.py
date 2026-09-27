from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

MechanismId = Literal[
    "intermediate_transfer",
    "target_induced_complementation",
    "redox_transfer",
    "covalent_capture",
]


class PayloadSpec(BaseModel):
    payload_id: str
    role: str
    fusion_terminus: Literal["N", "C"] = "C"
    repeat_index: int = Field(ge=0, description="Docking repeat index on the CTPR scaffold")
    radius_A: float = Field(gt=0, description="Spherical payload radius (Å)")
    linker_id: str = "gs_default"
    functional_site: str | None = None
    structure_id: str | None = None


class ScaffoldSpec(BaseModel):
    n_repeats: int = Field(ge=3, le=24)
    payloads: list[PayloadSpec]


class DesignSpec(BaseModel):
    design_id: str
    mechanism_profile: MechanismId = "intermediate_transfer"
    chassis: Literal["cell_free", "E_coli", "B_subtilis", "other"] = "cell_free"
    sensor_id: str = "CaM-M13"
    scaffold: ScaffoldSpec
    reporter_id: str | None = None
    localization: str = "soluble"
    operating_mode: Literal["reversible", "locking", "target_triggered"] = "reversible"

    @model_validator(mode="after")
    def payload_indices_in_range(self) -> "DesignSpec":
        n = self.scaffold.n_repeats
        for p in self.scaffold.payloads:
            if p.repeat_index >= n:
                raise ValueError(
                    f"payload {p.payload_id} docks at repeat {p.repeat_index}, "
                    f"but scaffold has only {n} repeats"
                )
        return self
