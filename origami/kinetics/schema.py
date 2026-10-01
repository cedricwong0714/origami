"""Public schema for the stage-1 kinetics workflow."""

from __future__ import annotations

from typing import Any

from origami.kinetics.rates import (
    MODEL_NAME,
    MODEL_VERSION,
    default_rate_slots,
)


def kinetics_schema() -> dict[str, Any]:
    """Describe literature priors vs vacant lab measurements."""
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
                "notes": "Langmuir steady state. Peptide Kd, not a fusion Kd.",
            },
            {
                "name": "k_off_from_k_on_kd",
                "formula": "kon_per_M_s * cam_m13_kd_M",
                "units": "s^-1",
                "requires": ["kon_per_M_s"],
                "optional_slot": "cam_m13_kd_M",
                "notes": (
                    "Derived only when the user supplies recruitment k_on. "
                    "Not invented from Kd alone as a Spy rate."
                ),
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
                "mode": "nanobit_complementation",
                "description": (
                    "Reversible bimolecular LgBiT + SmBiT using Dixon 2016 "
                    "k_on and k_off. The printed 190 μM Kd is reported beside "
                    "k_off/k_on and is not substituted into the ODE."
                ),
                "required_fields": ["lg0_M", "sm0_M"],
                "optional_fields": [
                    "nanobit_k_on_per_M_s",
                    "nanobit_k_off_per_s",
                    "t_end_s",
                    "num_points",
                    "use_literature_priors",
                ],
            },
            {
                "mode": "covalent_timecourse",
                "description": (
                    "Default: lumped irreversible bimolecular adduct using "
                    "Zakeri 2012 spy_k_on. Three-step ODE if lab supplies "
                    "spy_k_rev and spy_k_bond."
                ),
                "required_fields": [],
                "optional_fields": [
                    "tag0_M",
                    "catcher0_M",
                    "spy_k_on_per_M_s",
                    "spy_k_rev_per_s",
                    "spy_k_bond_per_s",
                    "t_end_s",
                    "num_points",
                    "use_literature_priors",
                ],
            },
        ],
        "note": (
            "Literature priors emulate a fusion path so the ODE can run. "
            "They are not Hong Kong team measurements. Lab fields stay "
            "null until stage-1 data. NanoBiT complementation integrates "
            "the Dixon k_on and k_off when lg0_M and sm0_M are posted. "
            "The printed Kd is not substituted for k_off/k_on. "
            "calibrated stays false. confidence_tier is hypothesis_only."
        ),
    }
