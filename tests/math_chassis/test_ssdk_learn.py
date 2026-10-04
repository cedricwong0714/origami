"""Surrogate active learning on the SSDK library.

The y values in these tests are synthetic inputs that check the algebra.
They are not assay results and they are not scientific validation.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.ssdk.learn import learn_ssdk

client = TestClient(app)


def test_no_observations_recommends_a_length_without_fitting():
    report = learn_ssdk({"n_min": 8, "n_max": 12, "observations": []})
    assert report["calibrated"] is False
    assert report["gp_fitted"] is False
    assert report["alpha_fixed_at_one"] is True
    assert report["alpha"] == pytest.approx(1.0)
    assert report["next_n"] in range(8, 13)
    assert report["radius_origin"] == "placeholder"
    first = report["candidates"][0]
    assert first["posterior_mean"] == pytest.approx(first["physics_score"])
    assert report["slices"]["kinetics"]["computable"] is False
    assert report["slices"]["structure"]["rows"][0]["calibrated"] is False


def test_two_surrogate_rows_move_the_posterior_and_stay_unfitted():
    report = learn_ssdk(
        {
            "n_min": 6,
            "n_max": 14,
            "observations": [
                {"n_repeats": 8, "y": 0.4, "sigma": 0.05, "source": "surrogate"},
                {"n_repeats": 12, "y": 0.9, "sigma": 0.05, "source": "surrogate"},
            ],
        }
    )
    assert report["gp_fitted"] is False
    assert report["alpha"] == pytest.approx(1.0)
    assert report["next_n"] not in {8, 12}
    by_n = {row["n_repeats"]: row for row in report["candidates"]}
    assert by_n[8]["posterior_mean"] == pytest.approx(0.4, abs=0.2)
    assert by_n[12]["posterior_mean"] == pytest.approx(0.9, abs=0.2)
    assert by_n[8]["posterior_std"] > 0


def test_three_lengths_fit_the_residual_and_do_not_edit_stability():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 17,
            "payload_radii_A": [20.0, 22.0],
            "observations": [
                {"n_repeats": 8, "y": 0.3, "source": "surrogate"},
                {"n_repeats": 14, "y": 0.6, "source": "surrogate"},
                {"n_repeats": 17, "y": 0.5, "source": "surrogate"},
            ],
        }
    )
    assert report["gp_fitted"] is True
    assert report["hyperparameters_optimized"] is True
    assert report["radius_origin"] == "caller"
    assert report["next_n"] not in {8, 14, 17}
    assert report["calibrated"] is False
    stability = {row["n_repeats"]: row for row in report["slices"]["stability"]["rows"]}
    assert stability[8]["tm_C"] is not None
    assert stability[14]["past_longest_cited_length"] is True
    assert all(
        row["calibrated"] is False for row in report["slices"]["stability"]["rows"]
    )
    assert any("sigma was omitted" in note for note in report["warnings"])


def test_chassis_snapshot_follows_the_primary_next_length():
    """The primary next length is scored by the same chassis as the chassis command.

    The y values are absent. This checks wiring, not a wet result.
    """
    from origami.physical.geometry import build_ctpr
    from origami.physical.structure import structural_report

    report = learn_ssdk({"n_min": 8, "n_max": 12, "observations": []})
    snap = report["chassis_at_next_n"]
    assert snap["n_repeats"] == report["recommendation"]["next_n"]
    assert snap["n_repeats"] == report["next_n"]
    assert snap["calibrated"] is False
    assert snap["replaces_slices"] is False
    assert snap["kinetics"]["computable"] is False
    assert snap["docking"]["clash_computable"] is False
    expected = structural_report(build_ctpr(snap["n_repeats"]))
    assert snap["structure"]["contour_nm"] == pytest.approx(expected.contour_nm)
    assert snap["structure"]["rigid_screw"] is expected.rigid_screw
    assert report["slices"]["kinetics"]["computable"] is False
    assert "clash_computable" not in report["slices"]["docking"]["rows"][0]


def test_caller_radii_and_kinetics_mode_reach_the_snapshot_only():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 12,
            "payload_radii_A": [20.0, 22.0],
            "kinetics": {"mode": "covalent_timecourse"},
            "observations": [],
        }
    )
    snap = report["chassis_at_next_n"]
    assert snap["docking"]["clash_computable"] is True
    assert snap["docking"]["radii_A"] == [20.0, 22.0]
    assert snap["kinetics"]["computable"] is True
    assert snap["calibrated"] is False
    thinner = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 12,
            "observations": [],
            "kinetics": {"k_lock_per_M_s": 1400.0},
        }
    )
    assert thinner["slices"]["kinetics"]["computable"] is True
    assert thinner["chassis_at_next_n"]["kinetics"]["computable"] is False


def test_bad_indices_keep_the_learn_response():
    report = learn_ssdk(
        {"n_min": 8, "n_max": 10, "observations": [], "indices": [1]}
    )
    assert report["next_n"] in range(8, 11)
    assert report["chassis_at_next_n"]["computable"] is False
    assert report["slices"]["structure"]["rows"]


def test_api_rejects_a_non_positive_sigma():
    response = client.post(
        "/api/ssdk/learn",
        json={
            "n_min": 8,
            "n_max": 10,
            "observations": [{"n_repeats": 8, "y": 1.0, "sigma": 0}],
        },
    )
    assert response.status_code == 400
    empty = client.post(
        "/api/ssdk/learn", json={"n_min": 8, "n_max": 10, "observations": []}
    )
    assert empty.status_code == 200
    assert empty.json()["gp_fitted"] is False
