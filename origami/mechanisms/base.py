from __future__ import annotations

from typing import Protocol

from origami.schemas.design import DesignSpec


class MechanismProfile(Protocol):
    profile_id: str
    version: str

    def validate_inputs(self, design: DesignSpec) -> None: ...

    def required_parameters(self, design: DesignSpec) -> list[str]: ...

    def predict(self, design: DesignSpec) -> dict: ...
