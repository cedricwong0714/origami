"""SSDK chassis algebra. Synthetic radii are inputs, not measured payloads."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.docking.evaluate import evaluate_docking
from origami.ssdk.chassis import evaluate_chassis

client = TestClient(app)


def test_docking_chord_does_not_invent_a_radius():
    docking = evaluate_docking(8)
    assert docking["calibrated"] is False
    assert docking["clash_computable"] is False
    assert docking["indices"] == [0, 2]
    assert docking["chord_A"] == pytest.approx(24.27, rel=1e-2)
    assert "p_clash" not in docking
    assert "c_eff_M" not in docking


def test_docking_with_caller_radii_returns_clash_and_ceff():
    docking = evaluate_docking(8, radii_A=[20.0, 20.0])
    assert docking["clash_computable"] is True
    assert docking["radius_origin"] == "caller"
    assert 0.0 <= docking["p_clash"] <= 1.0
    assert docking["c_eff_M"] > 0
    assert docking["c_eff_sigma_M"] is not None
    assert (
        docking["c_eff_95_lower_M"] < docking["c_eff_M"] < docking["c_eff_95_upper_M"]
    )


def test_chassis_keeps_literature_tm_when_a_lab_tm_is_typed():
    report = evaluate_chassis({"n_repeats": 8, "lab_tm_C": 80.0})
    assert report["calibrated"] is False
    assert report["structure"]["rigid_screw"] is True
    assert report["structure"]["contour_nm"] == pytest.approx(6.733, rel=1e-2)
    stability = report["stability"]
    assert stability["tm_C"] == pytest.approx(73.46, abs=0.1)
    assert stability["lab_tm_C"] == pytest.approx(80.0)
    assert stability["lab_tm_above_assay"] is True
    assert stability["tm_C"] != stability["lab_tm_C"]
    assert report["docking"]["clash_computable"] is False
    assert report["kinetics"]["computable"] is False


def test_chassis_kinetics_runs_from_a_posted_concentration():
    report = evaluate_chassis(
        {
            "n_repeats": 14,
            "radii_A": [18.0, 22.0],
            "kinetics": {"mode": "recruitment_steady", "c_free_M": 1e-8},
        }
    )
    assert report["docking"]["clash_computable"] is True
    assert report["stability"]["past_longest_cited_length"] is True
    kinetics = report["kinetics"]
    assert kinetics["computable"] is True
    assert kinetics["simulation"]["calibrated"] is False
    assert kinetics["simulation"]["recruitment"]["theta_ss"] == pytest.approx(
        1e-8 / (1e-8 + 0.19e-9), rel=1e-6
    )


def test_api_rejects_a_non_positive_radius():
    response = client.post(
        "/api/ssdk/chassis",
        json={"n_repeats": 8, "radii_A": [20.0, -1.0]},
    )
    assert response.status_code == 400
    ok = client.post("/api/ssdk/chassis", json={"n_repeats": 8})
    assert ok.status_code == 200
    assert ok.json()["calibrated"] is False
