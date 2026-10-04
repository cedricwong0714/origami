"""Named mechanism profiles already in ORIGAMI. New ODEs are rejected."""

from __future__ import annotations

from typing import Any

ALLOWED = {
    "recruitment_steady": {
        "equations": "Langmuir occupancy; optional mass-action time course",
        "required": ["c_free_M"],
        "optional": ["kon_per_M_s", "t_end_s"],
    },
    "covalent_timecourse": {
        "equations": "Lumped irreversible Spy adduct, or reversible + lock",
        "required": ["tag0_M", "catcher0_M"],
        "optional": ["spy_k_on_per_M_s"],
    },
    "nanobit_complementation": {
        "equations": "Reversible LgBiT–SmBiT binding",
        "required": ["lg0_M", "sm0_M"],
        "optional": ["nanobit_k_on_per_M_s", "nanobit_k_off_per_s"],
    },
}


class ProfileError(ValueError):
    """The profile is not one of the shipped kinetics modes."""


def validate_profile(body: dict[str, Any]) -> dict[str, Any]:
    name = body.get("mode")
    if name not in ALLOWED:
        raise ProfileError(
            "ORIGAMI will not compile a new ODE from a user equation string. "
            f"Use one of: {sorted(ALLOWED)}."
        )
    spec = ALLOWED[name]
    missing = [key for key in spec["required"] if key not in body]
    if missing:
        raise ProfileError(f"missing required fields for {name}: {missing}")
    return {
        "calibrated": False,
        "mode": name,
        "accepted": True,
        "equations": spec["equations"],
        "note": "This is a shipped mechanism. It is not a custom kinetics compiler.",
    }
