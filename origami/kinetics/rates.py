"""Rate slots for the stage-1 kinetics workflow.

Literature priors are explicit. Lab measurements stay null until ingestion.
Vacant Spy reversible/lock rates are not filled from unsourced JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from origami.priors import (
    CAM_M13_KD_M,
    NANOBIT_K_OFF_PER_S,
    NANOBIT_K_ON_PER_M_S,
    NANOBIT_KD_M,
    SPY_K_ON_PER_M_S,
)

RateStatus = Literal["literature", "vacant", "user_supplied"]
RateOrigin = Literal["literature_prior", "lab_measurement"]

MODEL_NAME = "origami_stage1_kinetics"
MODEL_VERSION = "0.2.0"


@dataclass(frozen=True)
class RateSlot:
    name: str
    status: RateStatus
    origin: RateOrigin
    value: float | None
    lab_value: float | None
    units: str
    source: str | None
    system: str | None
    method: str | None
    notes: str
    sigma: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "origin": self.origin,
            "value": self.value,
            "lab_value": self.lab_value,
            "units": self.units,
            "source": self.source,
            "system": self.system,
            "method": self.method,
            "notes": self.notes,
            "sigma": self.sigma,
        }


def literature_cam_m13_kd_slot() -> RateSlot:
    return RateSlot(
        name="cam_m13_kd_M",
        status="literature",
        origin="literature_prior",
        value=float(CAM_M13_KD_M.value),
        lab_value=None,
        units="M",
        source=CAM_M13_KD_M.source,
        system=CAM_M13_KD_M.system,
        method=CAM_M13_KD_M.method,
        notes=(
            "Peptide Kd at saturating Ca2+. Used for Langmuir θ_ss only. "
            "Not a CLASP fusion measurement. calibrated stays false."
        ),
        sigma=CAM_M13_KD_M.sigma,
    )


def literature_spy_association_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_on_per_M_s",
        status="literature",
        origin="literature_prior",
        value=float(SPY_K_ON_PER_M_S.value),
        lab_value=None,
        units="M^-1 s^-1",
        source=SPY_K_ON_PER_M_S.source,
        system=SPY_K_ON_PER_M_S.system,
        method=SPY_K_ON_PER_M_S.method,
        notes=SPY_K_ON_PER_M_S.notes,
        sigma=SPY_K_ON_PER_M_S.sigma,
    )


def vacant_spy_off_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_rev_per_s",
        status="vacant",
        origin="lab_measurement",
        value=None,
        lab_value=None,
        units="s^-1",
        source=None,
        system="SpyTag/SpyCatcher reversible complex (not in Zakeri 2012)",
        method=None,
        notes=(
            "Vacant. Zakeri 2012 reports an apparent second-order covalent "
            "rate, not k_rev. Keeble 2019 koff is SpyTag003, not this pair. "
            "Lab SDS-PAGE / SPR can fill this in ~2 weeks. "
            "Default covalent simulate uses the lumped irreversible path."
        ),
        sigma=None,
    )


def vacant_spy_lock_slot() -> RateSlot:
    return RateSlot(
        name="spy_k_bond_per_s",
        status="vacant",
        origin="lab_measurement",
        value=None,
        lab_value=None,
        units="s^-1",
        source=None,
        system="Isopeptide locking step after reversible capture",
        method=None,
        notes=(
            "Vacant. Not printed in Zakeri 2012. The repo JSON "
            "covalent_capture.defaults.json k_bond=2.0 is relative and unsourced. "
            "clasp_assembly k_lock=0.003 s^-1 is not used here. "
            "Lab lock kinetics can replace the lumped path."
        ),
        sigma=None,
    )


def literature_nanobit_kd_slot() -> RateSlot:
    return RateSlot(
        name="nanobit_kd_M",
        status="literature",
        origin="literature_prior",
        value=float(NANOBIT_KD_M.value),
        lab_value=None,
        units="M",
        source=NANOBIT_KD_M.source,
        system=NANOBIT_KD_M.system,
        method=NANOBIT_KD_M.method,
        notes=NANOBIT_KD_M.notes,
        sigma=NANOBIT_KD_M.sigma,
    )


def literature_nanobit_on_slot() -> RateSlot:
    return RateSlot(
        name="nanobit_k_on_per_M_s",
        status="literature",
        origin="literature_prior",
        value=float(NANOBIT_K_ON_PER_M_S.value),
        lab_value=None,
        units="M^-1 s^-1",
        source=NANOBIT_K_ON_PER_M_S.source,
        system=NANOBIT_K_ON_PER_M_S.system,
        method=NANOBIT_K_ON_PER_M_S.method,
        notes=NANOBIT_K_ON_PER_M_S.notes,
        sigma=NANOBIT_K_ON_PER_M_S.sigma,
    )


def literature_nanobit_off_slot() -> RateSlot:
    return RateSlot(
        name="nanobit_k_off_per_s",
        status="literature",
        origin="literature_prior",
        value=float(NANOBIT_K_OFF_PER_S.value),
        lab_value=None,
        units="s^-1",
        source=NANOBIT_K_OFF_PER_S.source,
        system=NANOBIT_K_OFF_PER_S.system,
        method=NANOBIT_K_OFF_PER_S.method,
        notes=NANOBIT_K_OFF_PER_S.notes,
        sigma=NANOBIT_K_OFF_PER_S.sigma,
    )


def default_rate_slots() -> tuple[RateSlot, ...]:
    return (
        literature_cam_m13_kd_slot(),
        literature_spy_association_slot(),
        vacant_spy_off_slot(),
        vacant_spy_lock_slot(),
        literature_nanobit_kd_slot(),
        literature_nanobit_on_slot(),
        literature_nanobit_off_slot(),
    )


def apply_user_rates(
    slots: tuple[RateSlot, ...],
    overrides: dict[str, float] | None,
) -> list[RateSlot]:
    """Mark user-supplied numeric overrides. Explicit nulls clear a literature prior."""
    overrides = overrides or {}
    out: list[RateSlot] = []
    for slot in slots:
        if slot.name not in overrides:
            out.append(slot)
            continue
        raw = overrides[slot.name]
        if raw is None:
            out.append(
                RateSlot(
                    name=slot.name,
                    status="vacant",
                    origin="lab_measurement",
                    value=None,
                    lab_value=None,
                    units=slot.units,
                    source=None,
                    system=slot.system,
                    method=None,
                    notes="Cleared for this request. Literature prior not used.",
                    sigma=None,
                )
            )
            continue
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            raise TypeError(f"{slot.name} override must be a number")
        value = float(raw)
        if value != value or value in (float("inf"), float("-inf")):
            raise ValueError(f"{slot.name} must be finite")
        out.append(
            RateSlot(
                name=slot.name,
                status="user_supplied",
                origin="lab_measurement",
                value=value,
                lab_value=value,
                units=slot.units,
                source="user_entered_in_simulate_request",
                system=slot.system,
                method="POST /api/kinetics/simulate",
                notes="Lab override for this request only. calibrated stays false.",
                sigma=None,
            )
        )
    return out
