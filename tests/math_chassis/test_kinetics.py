"""Stage-1 kinetics schema and simulate contract."""

from __future__ import annotations

import math

import pytest

from fastapi.testclient import TestClient

from origami.api.kinetics import get_kinetics_schema
from origami.api.structural import app

client = TestClient(app)
from origami.kinetics.rates import default_rate_slots
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.priors import CAM_M13_KD_M


def test_schema_marks_spy_rates_vacant():
    payload = get_kinetics_schema()
    assert payload["calibrated"] is False
    slots = {row["name"]: row for row in payload["rate_slots"]}
    assert slots["cam_m13_kd_M"]["status"] == "literature"
    assert slots["cam_m13_kd_M"]["value"] == pytest.approx(CAM_M13_KD_M.value)
    for name in ("spy_k_on_per_M_s", "spy_k_rev_per_s", "spy_k_bond_per_s"):
        assert slots[name]["status"] == "vacant"
        assert slots[name]["value"] is None


def test_recruitment_steady_without_kon():
    out = simulate_kinetics({"mode": "recruitment_steady", "c_free_M": 1e-9})
    rec = out["recruitment"]
    kd = CAM_M13_KD_M.value
    expected = 1e-9 / (1e-9 + kd)
    assert rec["theta_ss"] == pytest.approx(expected)
    assert rec["time_s"] is None
    assert out["derived"]["k_off_per_s"] is None


def test_recruitment_with_kon_derives_k_off():
    kon = 1e6
    out = simulate_kinetics(
        {"mode": "recruitment_steady", "c_free_M": 1e-8, "kon_per_M_s": kon}
    )
    assert out["recruitment"]["theta_t"] is not None
    assert out["derived"]["k_off_per_s"] == pytest.approx(kon * CAM_M13_KD_M.value)


def test_covalent_rejects_vacant_spy_rates():
    with pytest.raises(KineticsSimError) as exc:
        simulate_kinetics({"mode": "covalent_timecourse"})
    assert "spy_k_on_per_M_s" in str(exc.value)


def test_covalent_runs_with_explicit_rates():
    out = simulate_kinetics(
        {
            "mode": "covalent_timecourse",
            "spy_k_on_per_M_s": 1.0,
            "spy_k_rev_per_s": 0.1,
            "spy_k_bond_per_s": 0.05,
            "num_points": 20,
        }
    )
    assert out["calibrated"] is False
    series = out["series"]
    assert len(series["adduct_M"]) == 20
    assert series["adduct_M"][-1] >= series["adduct_M"][0]
    assert math.isfinite(series["adduct_M"][-1])


def test_api_schema_route():
    body = get_kinetics_schema()
    assert body["workflow_id"] == "stage1_scaffold_kinetics"


def test_http_kinetics_schema_and_simulate():
    schema = client.get("/api/kinetics/schema")
    assert schema.status_code == 200
    assert schema.json()["calibrated"] is False
    sim = client.post(
        "/api/kinetics/simulate",
        json={"mode": "recruitment_steady", "c_free_M": 1e-9},
    )
    assert sim.status_code == 200
    assert sim.json()["recruitment"]["theta_ss"] > 0


def test_default_slots_count():
    assert len(default_rate_slots()) == 4
