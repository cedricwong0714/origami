"""Rate slots for the stage-1 kinetics workflow.

Vacant slots have ``value=None``. Nothing in this module invents a wet-lab
SpyTag or isopeptide-lock rate.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from origami.priors import CAM_M13_KD_M

RateStatus = Literal["literature", "vacant", "user_supplied"]

MODEL_NAME = "origami_stage1_kinetics"
MODEL_VERSION = "0.1.0"


@dataclass(frozen=True)
class RateSlot:
    name: str
    status: RateStatus
    value: float | None
    units: str
    source: str | None
    system: str | None
    method: str | None
    notes: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "value": self.value,
            "units": self.units,
            "source": self.source,
            "system": self.system,
            "method": self.method,
            "notes": self.notes,
        }


def literature_cam_m13_kd_slot() -> RateSlot:
    return RateSlot(
        name="cam_m13_kd_M",
        status="literature",
        value=float(CAM_M13_KD_M.value),
        units="M",
        source=CAM_M13_KD_M.source,
        system=CAM_M13_KD_M.system,
        method=CAM_M13_KD_M.method,
        notes=(
            "Peptide Kd at saturating Ca2+. Used for Langmuir θ_ss only. "
            "Not a CLASP fusion measurement. calibrated stays false."
        ),
    )


def vacant_spy_association_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_on_per_M_s",
        status="vacant",
        value=None,
        units="M^-1 s^-1",
        source=None,
        system="SpyTag/SpyCatcher on CLASP scaffold (planned stage-1)",
        method=None,
        notes=(
            "Vacant until a stage-1 SpyTag kinetics package is ingested. "
            "Do not use models/kinetic_models/covalent_capture.defaults.json "
            "as a wet-lab substitute on this workflow."
        ),
    )


def vacant_spy_off_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_rev_per_s",
        status="vacant",
        value=None,
        units="s^-1",
        source=None,
        system="SpyTag/SpyCatcher reversible complex (planned stage-1)",
        method=None,
        notes="Vacant until stage-1 ingestion. May be computed as k_on * Kd when both are measured.",
    )


def vacant_spy_lock_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_bond_per_s",
        status="vacant",
        value=None,
        units="s^-1",
        source=None,
        system="Isopeptide locking step after reversible capture (planned stage-1)",
        method=None,
        notes="Vacant until SDS-PAGE or plate-reader lock kinetics are recorded.",
    )


def default_rate_slots() -> tuple[RateSlot, ...]:
    return (
        literature_cam_m13_kd_slot(),
        vacant_spy_association_slot(),
        vacant_spy_off_slot(),
        vacant_spy_lock_slot(),
    )


def apply_user_rates(
    slots: tuple[RateSlot, ...],
    overrides: dict[str, float] | None,
) -> list[RateSlot]:
    """Mark user-supplied numeric overrides without filling vacant defaults."""
    overrides = overrides or {}
    out: list[RateSlot] = []
    for slot in slots:
        if slot.name in overrides:
            raw = overrides[slot.name]
            if not isinstance(raw, (int, float)) or isinstance(raw, bool):
                raise TypeError(f"{slot.name} override must be a number")
            value = float(raw)
            if value != value or value in (float("inf"), float("-inf")):
                raise ValueError(f"{slot.name} must be finite")
            out.append(
                RateSlot(
                    name=slot.name,
                    status="user_supplied",
                    value=value,
                    units=slot.units,
                    source="user_entered_in_simulate_request",
                    system=slot.system,
                    method="POST /api/kinetics/simulate",
                    notes="Override for this request only. calibrated stays false.",
                )
            )
        else:
            out.append(slot)
    return out
