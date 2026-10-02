"""Test wiring of wet-lab observations to SSDK residual Gaussian Process and BO."""

from __future__ import annotations

import pytest

from origami.lab.run import run_lab


def test_lab_run_with_fit_residual_gp():
    # Submit 3 distinct surrogate observations from lab (e.g. bridging fold across CTPR-8, 14, 17)
    body = {
        "prep": {"construct_id": "ctpr_series", "expressed_n8": True, "expressed_n14": True},
        "observations": [
            {"n": 8, "y": 1.0, "sigma": 0.05, "source": "wet_lab_bridging"},
            {"n": 14, "y": 1.45, "sigma": 0.08, "source": "wet_lab_bridging"},
            {"n": 3, "y": 1.15, "sigma": 0.06, "source": "wet_lab_bridging"},
        ],
        "fit_residual_gp": True,
        "acquisition": "ucb",
    }
    report = run_lab(body)

    assert report["calibrated"] is False
    assert report["residual_gp"]["fitted"] is True
    assert report["residual_gp"]["n_rows"] == 3
    assert set(report["residual_gp"]["distinct_lengths"]) == {3, 8, 14}
    assert report["residual_gp"]["next_n"] is not None
    assert report["residual_gp"]["acquisition"] == "UCB(κ=1.8)"
    assert len(report["residual_gp"]["candidates"]) > 0


def test_lab_run_fit_residual_gp_empty_observations():
    body = {
        "fit_residual_gp": True,
        "observations": [],
    }
    report = run_lab(body)
    assert report["residual_gp"]["fitted"] is False
    assert report["residual_gp"]["n_rows"] == 0
