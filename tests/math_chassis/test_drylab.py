"""Dry-lab rows are measurements. Series are not averaged. GP stays unfitted.

Scientific basis: Phillips 2012 CTPRa DSC and Cortajarena 2011 DSC report
different Tm values at n=8. Averaging them would invent a melting temperature.
Failure mode: a panel that blends series, or a dataset that marks itself calibrated.
"""

from __future__ import annotations

from origami.drylab import drylab_dataset, stability_panel
from origami.stability.series import (
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPRA_DSC,
)


def test_stability_series_stay_unmixed() -> None:
    panel = stability_panel(37.0)
    phillips = [
        row
        for row in panel
        if row["series_id"] == PHILLIPS_2012_CTPRA_DSC and row["n_repeats"] == 8
    ]
    cortajarena = [
        row
        for row in panel
        if row["series_id"] == CORTAJARENA_2011_CTPRA_DSC and row["n_repeats"] == 8
    ]
    assert len(phillips) == 1
    assert len(cortajarena) == 1
    assert phillips[0]["tm_C"] == 74.0
    assert cortajarena[0]["tm_C"] == 78.9
    assert phillips[0]["thermal_state"] == "pass"
    missing = [
        row
        for row in panel
        if row["series_id"] == PHILLIPS_2012_CTPRA_DSC and row["n_repeats"] == 14
    ]
    assert missing[0]["thermal_state"] == "extrapolated"
    assert missing[0]["tm_C"] is None
    assert all(row["calibrated"] is False for row in panel)


def test_dataset_records_measurements_and_does_not_fit_the_gp() -> None:
    report = {
        "n_repeats": 8,
        "next_n": 8,
        "separation": {
            "next_delta_i": 3,
            "acquisition_name": "ucb",
            "candidates": [
                {
                    "delta_i": 4,
                    "chord_A": 10.0,
                    "chord_sigma_A": 0.2,
                    "facing_cosine": -1.0,
                    "p_clash": 0.0,
                    "c_eff_M": 1e-6,
                    "physics_score": 0.01,
                }
            ],
        },
    }
    confirmation = {
        "rows": [
            {
                "n_repeats": 8,
                "contour_nm": 6.7,
                "end_pair_chord_A": 12.0,
                "end_pair_chord_sigma_A": 0.3,
                "end_pair_facing_cosine": 0.7,
                "p_instability": 0.0,
                "end_pair_c_eff_M": 1e-8,
                "physics_score": 0.0,
                "rigid_screw": True,
            }
        ]
    }
    scene = {
        "n_repeats": 1,
        "residues_per_repeat": 2,
        "ca_A": [[10.0, 0.0, 0.0], [0.0, 10.0, 1.0]],
    }
    bundle = drylab_dataset(report, confirmation, scene, t_assay_C=37.0)
    assert bundle["calibrated"] is False
    assert bundle["gp_fitted"] is False
    assert bundle["active_learning"]["next_n"] == 8
    assert bundle["active_learning"]["next_delta_i"] == 3
    assert bundle["active_learning"]["gp_fitted"] is False
    observables = {row["observable"] for row in bundle["measurements"]}
    assert "chord_A" in observables
    assert "ca_radial_A" in observables
    assert "contour_nm" in observables
    radial = [row for row in bundle["measurements"] if row["observable"] == "ca_radial_A"]
    assert radial[0]["value_mean_A"] == 10.0
