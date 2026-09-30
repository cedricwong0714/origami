"""Public schema for the stage-1 kinetics workflow."""

from __future__ import annotations

from typing import Any

from origami.kinetics.rates import (
    MODEL_NAME,
    MODEL_VERSION,
    default_rate_slots,
)


def kinetics_schema() -> dict[str, Any]:
    """Describe vacant vs literature rate slots and what can be computed."""
    slots = default_rate_slots()
    return {
        "workflow_id": "stage1_scaffold_kinetics",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "rate_slots": [slot.to_dict() for slot in slots],
        "computed_from_literature": [
            {
                "name": "recruitment_theta_ss",
                "formula": "C_free / (C_free + cam_m13_kd_M)",
                "units": "fraction",
                "requires": ["c_free_M"],
                "uses_slot": "cam_m13_kd_M",
                "notes": "Langmuir steady state. Does not use vacant SpyTag rates.",
            },
            {
                "name": "k_off_from_k_on_kd",
                "formula": "spy_k_on_per_M_s * cam_m13_kd_M",
                "units": "s^-1",
                "requires": ["spy_k_on_per_M_s"],
                "optional_slot": "cam_m13_kd_M",
                "notes": "Derived only when the user supplies k_on in simulate; not a default.",
            },
        ],
        "simulate_modes": [
            {
                "mode": "recruitment_steady",
                "description": "CaM–M13 Langmuir occupancy at fixed free signal.",
                "required_fields": ["c_free_M"],
                "optional_fields": ["kon_per_M_s", "t_end_s"],
            },
            {
                "mode": "covalent_timecourse",
                "description": "Tag/Catcher reversible complex plus locking ODE.",
                "required_fields": [
                    "tag0_M",
                    "catcher0_M",
                    "spy_k_on_per_M_s",
                    "spy_k_rev_per_s",
                    "spy_k_bond_per_s",
                ],
                "optional_fields": ["t_end_s", "num_points"],
            },
        ],
        "note": (
            "SpyTag association, off-rate, and lock-rate slots are vacant until "
            "stage-1 ingestion. This API does not silently load "
            "models/kinetic_models/covalent_capture.defaults.json. "
            "calibrated stays false."
        ),
    }
