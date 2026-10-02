"""Lab intake schema for the experiments this team is running.

Slots are empty until a measurement is posted. This list does not
include a melting temperature, a payload radius, a fusion Kd, or
separate SpyCatcher k_rev and k_bond. Those quantities are not in the
lab plan, and this schema does not invent them.
"""

from __future__ import annotations

from typing import Any

SCHEMA_VERSION = "1"


def _slot(
    name: str,
    units: str,
    section: str,
    description: str,
) -> dict[str, Any]:
    return {
        "name": name,
        "units": units,
        "section": section,
        "description": description,
        "origin": "lab_measurement",
        "value": None,
        "sigma": None,
    }


def lab_schema() -> dict[str, Any]:
    """Return the vacant slot list and the equations each section can run."""
    slots = [
        _slot(
            "concentration_uM",
            "µM",
            "prep",
            "BCA or Bradford concentration of the sample you will use downstream.",
        ),
        _slot(
            "soluble_fraction",
            "fraction",
            "prep",
            "Supernatant signal divided by supernatant plus pellet, if you quantified the gel.",
        ),
        _slot(
            "n_repeats",
            "repeats",
            "prep",
            "Scaffold length. The geometry series is CTPR-8 and CTPR-14, with CTPR-3 as biomarker baseline.",
        ),
        _slot(
            "ca_M",
            "M",
            "calcium",
            "Free calcium concentrations for the dose–response, after the Fluo-3 buffer check.",
        ),
        _slot(
            "calcium_rlu",
            "RLU",
            "calcium",
            "Luminescence at each free calcium concentration.",
        ),
        _slot(
            "wt_rlu",
            "RLU",
            "calcium",
            "Wild-type M13 luminescence for the specificity ratio.",
        ),
        _slot(
            "scrambled_rlu",
            "RLU",
            "calcium",
            "Scrambled M13 luminescence for the specificity ratio.",
        ),
        _slot("rlu_25_C", "RLU", "calcium", "CaM–M13 luminescence at 25 °C."),
        _slot("rlu_30_C", "RLU", "calcium", "CaM–M13 luminescence at 30 °C."),
        _slot("rlu_37_C", "RLU", "calcium", "CaM–M13 luminescence at 37 °C."),
        _slot(
            "time_min",
            "min",
            "lock",
            "SDS-PAGE time points. The protocol uses 0, 2, 5, 10, 30, and 60 min.",
        ),
        _slot(
            "fraction_locked",
            "fraction",
            "lock",
            "Adduct divided by the limiting partner at each time.",
        ),
        _slot(
            "tag0_M",
            "M",
            "lock",
            "Starting SpyTag concentration from the BCA and the accepted sequence mass.",
        ),
        _slot(
            "catcher0_M",
            "M",
            "lock",
            "Starting SpyCatcher concentration from the BCA and the accepted sequence mass.",
        ),
        _slot("tube1_rlu", "RLU", "bridging", "Tube 1, no target."),
        _slot("tube2_rlu", "RLU", "bridging", "Tube 2, bridging streptavidin."),
        _slot(
            "tube3_rlu",
            "RLU",
            "bridging",
            "Tube 3, streptavidin pre-blocked with biotin.",
        ),
        _slot(
            "tube4_rlu",
            "RLU",
            "bridging",
            "Tube 4, streptavidin at the hook-effect setpoint.",
        ),
        _slot(
            "amount",
            "caller amount unit",
            "assay_window",
            "Standard-curve amounts (for example fmol of NanoLuc).",
        ),
        _slot(
            "standard_rlu",
            "RLU",
            "assay_window",
            "Standard-curve luminescence at each amount.",
        ),
        _slot(
            "rlu_low", "RLU", "assay_window", "Lower end of the NanoBiT linear range."
        ),
        _slot(
            "rlu_high", "RLU", "assay_window", "Upper end of the NanoBiT linear range."
        ),
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "slots": slots,
        "not_collected": [
            "melting temperature",
            "circular dichroism",
            "size-exclusion elution volume",
            "cryo-EM coordinates",
            "payload radius",
            "fusion CaM–M13 Kd",
            "SpyCatcher k_rev",
            "SpyCatcher k_bond",
            "enzyme k_cat and K_m",
        ],
        "sections": {
            "prep": "Records concentration and gel calls. Does not update screw coordinates and does not convert mass to a radius.",
            "assay_window": "Line RLU = a + b × amount, optional furimazine half-life, CV, and a linear-range flag.",
            "calcium": "Logistic EC50. Hill slope fixed at 1 when it is not identifiable. Three temperatures are ratios, not an activation energy.",
            "lock": "Lumped d[adduct]/dt = k_lock [Tag][Catcher], or a caller-chosen pseudo-first-order form. k_rev and k_bond are not fit.",
            "bridging": "tube2/tube1, tube3/tube2, and tube4/tube2. No fold-change cutoff.",
        },
        "residual_gp": {
            "fitted": False,
            "reason": (
                "The residual Gaussian process stays unfitted. "
                "Bridging luminescence and calcium EC50 have no physics score on that scale in this chassis."
            ),
        },
    }
