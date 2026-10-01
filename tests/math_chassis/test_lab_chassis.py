"""Algebra checks for the lab chassis.

Synthetic series below are chosen so the equations have a known answer.
They are not assay measurements and they are not scientific validation.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.assay.calcium import (
    fit_calcium_response,
    scrambled_ratio,
    temperature_luminosities,
)
from origami.assay.window import (
    admissibility,
    coefficient_of_variation,
    fit_half_life,
    fit_standard_curve,
)
from origami.bridging.ratios import bridging_ratios
from origami.kinetics.lock_fit import fit_lock, fraction_locked
from origami.lab.run import run_lab
from origami.lab.schema import lab_schema
from origami.priors import SPY_K_ON_PER_M_S

client = TestClient(app)


def test_schema_leaves_lab_slots_empty_and_omits_unmeasured_quantities():
    payload = lab_schema()
    assert payload["calibrated"] is False
    assert payload["confidence_tier"] == "hypothesis_only"
    assert payload["residual_gp"]["fitted"] is False
    names = {slot["name"] for slot in payload["slots"]}
    assert "concentration_uM" in names
    assert "fraction_locked" in names
    assert "tube2_rlu" in names
    for slot in payload["slots"]:
        assert slot["value"] is None
        assert slot["sigma"] is None
        assert slot["origin"] == "lab_measurement"
    blocked = " ".join(payload["not_collected"]).lower()
    assert "melting temperature" in blocked
    assert "payload radius" in blocked
    assert "k_rev" in blocked
    assert "k_bond" in blocked


def test_standard_curve_recovers_slope_and_omits_nothing_it_computed():
    amount = [0.0, 1.0, 2.0, 3.0]
    rlu = [5.0, 7.0, 9.0, 11.0]
    fitted = fit_standard_curve(amount, rlu)
    assert fitted["computable"] is True
    assert fitted["calibrated"] is False
    assert fitted["slope"] == pytest.approx(2.0)
    assert fitted["intercept"] == pytest.approx(5.0)
    assert fitted["slope_sigma"] is not None
    assert fitted["slope_sigma"] < 1e-6


def test_cv_of_one_value_is_not_stored_as_zero():
    result = coefficient_of_variation([4.0])
    assert result["computable"] is False
    assert "cv" not in result or result.get("cv") is None


def test_cv_of_identical_replicates_is_zero():
    result = coefficient_of_variation([3.0, 3.0, 3.0])
    assert result["computable"] is True
    assert result["cv"] == pytest.approx(0.0)
    assert result["sample_sigma"] == pytest.approx(0.0)


def test_half_life_of_a_known_exponential():
    # RLU = 100 * exp(-k t) with k = ln(2) / 600 s, so t_half = 10 min.
    k_per_s = math.log(2.0) / 600.0
    time_min = [0.0, 5.0, 10.0, 20.0]
    rlu = [100.0 * math.exp(-k_per_s * t * 60.0) for t in time_min]
    fitted = fit_half_life(time_min, rlu)
    assert fitted["computable"] is True
    assert fitted["half_life_min"] == pytest.approx(10.0, rel=1e-3)
    assert fitted["half_life_sigma_min"] is not None


def test_rlu_outside_the_stored_window_is_flagged():
    inside = admissibility(500.0, 100.0, 1000.0)
    outside = admissibility(50.0, 100.0, 1000.0)
    missing = admissibility(500.0, None, None)
    assert inside["admissible"] is True
    assert outside["admissible"] is False
    assert missing["computable"] is False
    assert missing["admissible"] is None


def test_calcium_ec50_is_recovered_and_does_not_replace_kd():
    ec50 = 1e-6
    ca = np.logspace(-8, -4, 12)
    rlu = 10.0 + (200.0 - 10.0) / (1.0 + (ec50 / ca) ** 1.5)
    fitted = fit_calcium_response(ca.tolist(), rlu.tolist())
    assert fitted["computable"] is True
    assert fitted["calibrated"] is False
    assert fitted["replaces_cam_m13_kd"] is False
    assert fitted["ec50_M"] == pytest.approx(ec50, rel=1e-2)
    assert fitted["hill_fixed_at_one"] is False
    assert fitted["ec50_sigma_M"] is not None


def test_three_calcium_points_do_not_produce_an_ec50():
    ec50 = 1e-6
    ca = [1e-8, 1e-6, 1e-4]
    rlu = [10.0 + 190.0 / (1.0 + ec50 / c) for c in ca]
    fitted = fit_calcium_response(ca, rlu)
    assert fitted["computable"] is False
    assert "ec50_M" not in fitted


def test_scrambled_ratio_omits_the_band_when_sigma_is_missing():
    result = scrambled_ratio(1000.0, 100.0)
    assert result["computable"] is True
    assert result["ratio"] == pytest.approx(0.1)
    assert result["ratio_sigma"] is None
    assert result["ratio_95_lower"] is None


def test_temperature_ratios_are_not_an_arrhenius_fit():
    result = temperature_luminosities(rlu_25_C=100.0, rlu_30_C=110.0, rlu_37_C=150.0)
    assert result["computable"] is True
    assert result["arrhenius_fit"] is False
    assert result["ratios"]["L37_over_L25"]["value"] == pytest.approx(1.5)
    assert result["ratios"]["L37_over_L25"]["sigma"] is None
    assert result["ratios"]["L30_over_L25"]["value"] == pytest.approx(1.1)


def test_second_order_lock_recovers_a_known_rate():
    tag0 = 10e-6
    catcher0 = 10e-6
    k = 1.4e3
    time_min = [0.0, 2.0, 5.0, 10.0, 30.0, 60.0]
    time_s = np.array(time_min) * 60.0
    fraction = fraction_locked(time_s, k, tag0, catcher0).tolist()
    fitted = fit_lock(
        {
            "time_min": time_min,
            "fraction_locked": fraction,
            "tag0_M": tag0,
            "catcher0_M": catcher0,
            "rate_law": "second_order",
            "sds_survives": True,
        }
    )
    assert fitted["computable"] is True
    assert fitted["calibrated"] is False
    assert fitted["k_lock_per_M_s"] == pytest.approx(k, rel=1e-2)
    assert fitted["literature_k_on_per_M_s"] == pytest.approx(SPY_K_ON_PER_M_S.value)
    assert "k_rev" not in fitted


def test_pseudo_first_order_reports_k_lock_as_k_obs_over_excess():
    k_obs = 0.01
    excess = 1e-4
    time_min = [0.0, 2.0, 5.0, 10.0, 30.0]
    fraction = [1.0 - math.exp(-k_obs * t * 60.0) for t in time_min]
    fitted = fit_lock(
        {
            "time_min": time_min,
            "fraction_locked": fraction,
            "tag0_M": excess,
            "catcher0_M": 1e-6,
            "rate_law": "pseudo_first_order",
            "excess_partner": "tag",
            "sds_survives": False,
        }
    )
    assert fitted["computable"] is True
    assert fitted["k_obs_per_s"] == pytest.approx(k_obs, rel=1e-2)
    assert fitted["k_lock_per_M_s"] == pytest.approx(k_obs / excess, rel=1e-2)
    assert any("not supported" in note for note in fitted["warnings"])


def test_flat_lock_series_is_not_given_a_rate():
    fitted = fit_lock(
        {
            "time_min": [0.0, 2.0, 5.0, 10.0],
            "fraction_locked": [0.0, 0.0, 0.0, 0.0],
            "tag0_M": 1e-5,
            "catcher0_M": 1e-5,
        }
    )
    assert fitted["computable"] is False
    assert "k_lock_per_M_s" not in fitted


def test_bridging_ratios_and_sign_pattern():
    result = bridging_ratios(
        {
            "tube1_rlu": 100.0,
            "tube2_rlu": 1000.0,
            "tube3_rlu": 200.0,
            "tube4_rlu": 300.0,
            "tube1_rlu_sigma": 10.0,
            "tube2_rlu_sigma": 20.0,
        }
    )
    assert result["computable"] is True
    assert result["calibrated"] is False
    assert result["signal_over_background"]["value"] == pytest.approx(10.0)
    assert result["signal_over_background"]["sigma"] is not None
    assert result["competition_over_bridge"]["sigma"] is None
    assert result["pattern_holds"] is True
    assert result["streptavidin_bridge_M"] == pytest.approx(50e-9)
    assert result["streptavidin_hook_M"] == pytest.approx(1e-6)


def test_bridging_without_tube_4_does_not_invent_a_ratio():
    result = bridging_ratios({"tube1_rlu": 1.0, "tube2_rlu": 2.0, "tube3_rlu": 1.0})
    assert result["computable"] is False
    assert "signal_over_background" not in result


def test_run_keeps_residual_gp_unfitted_and_does_not_move_the_screw():
    report = run_lab(
        {
            "prep": {"construct_id": "ctpr8", "n_repeats": 8, "expressed_n8": True},
            "observations": [
                {"n": 8, "y": 1.0, "assay": "bridging_fold"},
                {"n": 14, "y": 1.2, "assay": "bridging_fold"},
                {"n": 17, "y": 1.1, "assay": "bridging_fold"},
            ],
        }
    )
    assert report["calibrated"] is False
    assert report["residual_gp"]["fitted"] is False
    assert report["residual_gp"]["n_rows"] == 3
    assert report["prep"]["updates_screw"] is False
    assert report["prep"]["structure_context"]["n_repeats"] == 8
    assert report["prep"]["structure_context"]["calibrated"] is False
    assert report["lock"]["computable"] is False
    assert report["bridging"]["computable"] is False


def test_api_schema_and_run_reject_a_non_finite_value():
    schema = client.get("/api/lab/schema")
    assert schema.status_code == 200
    assert schema.json()["calibrated"] is False
    bad = client.post(
        "/api/lab/run",
        content='{"prep": {"concentration_uM": NaN}}',
        headers={"Content-Type": "application/json"},
    )
    assert bad.status_code == 400
    empty = client.post("/api/lab/run", json={})
    assert empty.status_code == 200
    assert empty.json()["bridging"]["computable"] is False
