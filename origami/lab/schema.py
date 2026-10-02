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
        _slot(
            "inter_day_rlu",
            "RLU",
            "quality",
            "Phase 3 / T4.11: replicate RLU across days (same construct, same operator optional).",
        ),
        _slot(
            "inter_operator_rlu",
            "RLU",
            "quality",
            "Replicate RLU across operators.",
        ),
        _slot(
            "plate_reader_reference_rlu",
            "RLU",
            "quality",
            "Instrument calibration check (Phase 3 exp 1).",
        ),
        _slot(
            "normalization_a_rlu",
            "RLU",
            "quality",
            "Normalization comparison method A (Phase 3 exp 3).",
        ),
        _slot(
            "normalization_b_rlu",
            "RLU",
            "quality",
            "Normalization comparison method B.",
        ),
        _slot(
            "fluo3_free_ca_M",
            "M",
            "quality",
            "Fluo-3 inferred free Ca2+ (Phase 3 exp 4).",
        ),
        _slot(
            "background_rlu",
            "RLU",
            "quality",
            "Empty-vector or lysis background (Phase 3 exp 5).",
        ),
        _slot(
            "expressed_rlu",
            "RLU",
            "quality",
            "Construct luminescence for signal/background (Phase 3 exp 5).",
        ),
        _slot(
            "linearity_amount",
            "caller amount unit",
            "quality",
            "NanoBiT linearity series amount (Phase 3 exp 6).",
        ),
        _slot(
            "linearity_rlu",
            "RLU",
            "quality",
            "NanoBiT linearity series RLU.",
        ),
        _slot(
            "freeze_thaw_rlu",
            "RLU",
            "quality",
            "Replicate RLU after freeze-thaw cycles (Phase 3 exp 8).",
        ),
        _slot(
            "lysis_soluble_fraction",
            "fraction",
            "quality",
            "Soluble fraction after lysis protocol (Phase 3 exp 9).",
        ),
        _slot(
            "negative_control_rlu",
            "RLU",
            "quality",
            "List of negative-control wells (Phase 3 exp 10).",
        ),
        _slot(
            "competitor_fold",
            "fold",
            "quality",
            "Spy competitor excess for irreversibility check (Phase 3 exp 11).",
        ),
        _slot(
            "complex_fraction_after_h",
            "fraction",
            "quality",
            "Covalent complex fraction after competition overnight.",
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
            "SpyCatcher k_rev (literature: no reversal observed; no numeric rate)",
            "SpyCatcher k_bond separate from lumped k_on",
            "enzyme k_cat and K_m",
        ],
        "sections": {
            "prep": "Records concentration and gel calls. Does not update screw coordinates and does not convert mass to a radius.",
            "assay_window": "Line RLU = a + b × amount, optional furimazine half-life, CV, and a linear-range flag.",
            "calcium": "Logistic EC50. Hill slope fixed at 1 when it is not identifiable. Three temperatures are ratios, not an activation energy.",
            "lock": "Lumped d[adduct]/dt = k_lock [Tag][Catcher], or a caller-chosen pseudo-first-order form. k_rev and k_bond are not fit.",
            "bridging": "tube2/tube1, tube3/tube2, and tube4/tube2. No fold-change cutoff.",
            "quality": (
                "Phase 3 calibration: CV budgets, linearity, Fluo-3, background, "
                "freeze-thaw, lysis, negative panel, Spy irreversibility. Vacant until posted."
            ),
        },
        "residual_gp": {
            "fitted": False,
            "reason": (
                "The residual Gaussian process stays unfitted. "
                "Bridging luminescence and calcium EC50 have no physics score on that scale in this chassis."
            ),
        },
    }
