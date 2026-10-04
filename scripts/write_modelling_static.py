"""Write a static snapshot of the modelling sandbox for Vercel.

Vercel cannot run Streamlit or numpy. This file is a saved lookup of
evaluate_chassis, the Phillips length series, one bound-fraction row,
one Spy time course, and one empty-reading next-length suggestion.
"""

from __future__ import annotations

import json
from pathlib import Path

from origami.priors import DEFAULT_PAYLOAD_RADIUS_A
from sandbox.modelling_service import (
    length_series,
    run_binding,
    score_length,
    suggest_next_length,
)

OUT = Path("web/modelling-static")


def _write(name: str, payload: object) -> None:
    path = OUT / name
    path.write_text(json.dumps(payload, indent=2) + "\n")
    print(path)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    radius = float(DEFAULT_PAYLOAD_RADIUS_A.value)
    series = length_series(3, 24)
    series_clash = length_series(3, 24, radii_A=[radius, radius])
    n8 = score_length(8)
    n8_clash = score_length(8, radii_A=[radius, radius])
    bound = run_binding("recruitment_steady", c_free_M=1e-8)
    spy = run_binding("covalent_timecourse", tag0_M=1e-5, catcher0_M=1e-5)
    nxt = suggest_next_length(3, 14, observations=[])
    rec = bound["recruitment"]
    snapshot = {
        "note": (
            "Saved from the live Python chassis. Vercel serves this JSON. "
            "It does not run Streamlit. Numbers are not lab measurements."
        ),
        "radius_A_2bbm": radius,
        "n8": {
            "n_repeats": n8["n_repeats"],
            "contour_nm": n8["structure"]["contour_nm"],
            "tm_C": n8["stability"]["tm_C"],
            "chord_A": n8["docking"]["chord_A"],
            "indices": n8["docking"]["indices"],
            "clash_computable": n8["docking"]["clash_computable"],
        },
        "n8_with_2bbm_radii": {
            "p_clash": n8_clash["docking"]["p_clash"],
            "c_eff_M": n8_clash["docking"]["c_eff_M"],
            "clash_computable": n8_clash["docking"]["clash_computable"],
        },
        "bound_fraction_at_1e-8_M": {
            "c_free_M": rec["c_free_M"],
            "kd_M": rec["kd_M"],
            "theta_ss": rec["theta_ss"],
            "theta_95_lower": rec["theta_95_lower"],
            "theta_95_upper": rec["theta_95_upper"],
        },
        "next_length_empty_readings": {
            "n_min": 3,
            "n_max": 14,
            "next_n": nxt["next_n"],
            "learner_family": nxt.get("learner_family"),
        },
        "spy_lock": {
            "path": spy["rates_used"]["path"],
            "k_on": spy["rates_used"]["spy_k_on_per_M_s"],
            "time_s": spy["time_s"],
            "adduct_M": spy["series"]["adduct_M"],
        },
        "series": series,
        "series_with_2bbm_radii": series_clash,
    }
    _write("snapshot.json", snapshot)


if __name__ == "__main__":
    main()
