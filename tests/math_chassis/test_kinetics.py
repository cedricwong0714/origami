"""Stage-1 kinetics schema and simulate contract."""

from __future__ import annotations

import math
import warnings

import pytest
from fastapi.testclient import TestClient

from origami.api.kinetics import get_kinetics_schema
from origami.api.structural import app
from origami.kinetics.rates import default_rate_slots
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.priors import CAM_M13_KD_M, NANOBIT_KD_M, SPY_K_ON_PER_M_S

client = TestClient(app)


def test_schema_literature_and_vacant_slots():
    payload = get_kinetics_schema()
    assert payload["calibrated"] is False
    assert payload["confidence_tier"] == "hypothesis_only"
    slots = {row["name"]: row for row in payload["rate_slots"]}
    assert slots["cam_m13_kd_M"]["status"] == "literature"
    assert slots["cam_m13_kd_M"]["origin"] == "literature_prior"
    assert slots["cam_m13_kd_M"]["value"] == pytest.approx(CAM_M13_KD_M.value)
    assert slots["cam_m13_kd_M"]["lab_value"] is None
    assert slots["spy_k_on_per_M_s"]["status"] == "literature"
    assert slots["spy_k_on_per_M_s"]["value"] == pytest.approx(SPY_K_ON_PER_M_S.value)
    assert slots["spy_k_on_per_M_s"]["value"] == pytest.approx(1.4e3)
    assert "10.1073/pnas.1115485109" in slots["spy_k_on_per_M_s"]["source"]
    for name in ("spy_k_rev_per_s", "spy_k_bond_per_s"):
        assert slots[name]["status"] == "vacant"
        assert slots[name]["value"] is None
        assert slots[name]["lab_value"] is None
        assert slots[name]["origin"] == "lab_measurement"
        assert slots[name]["sigma"] is None
    assert slots["nanobit_kd_M"]["value"] == pytest.approx(NANOBIT_KD_M.value)
    assert slots["nanobit_kd_M"]["sigma"] is None
    assert slots["nanobit_k_on_per_M_s"]["sigma"] is None


def test_literature_constants_match_priors_module():
    assert SPY_K_ON_PER_M_S.value == pytest.approx(1.4e3)
    assert SPY_K_ON_PER_M_S.sigma == pytest.approx(43.0)
    assert SPY_K_ON_PER_M_S.calibrated is False
    assert CAM_M13_KD_M.value == pytest.approx(0.19e-9)


def test_recruitment_steady_without_kon():
    out = simulate_kinetics({"mode": "recruitment_steady", "c_free_M": 1e-9})
    rec = out["recruitment"]
    kd = CAM_M13_KD_M.value
    expected = 1e-9 / (1e-9 + kd)
    assert rec["theta_ss"] == pytest.approx(expected)
    assert rec["time_s"] is None
    assert out["derived"]["k_off_per_s"] is None
    assert out["calibrated"] is False
    assert out["confidence_tier"] == "hypothesis_only"


def test_recruitment_with_kon_derives_k_off():
    kon = 1e6
    out = simulate_kinetics(
        {"mode": "recruitment_steady", "c_free_M": 1e-8, "kon_per_M_s": kon}
    )
    assert out["recruitment"]["theta_t"] is not None
    assert out["derived"]["k_off_per_s"] == pytest.approx(kon * CAM_M13_KD_M.value)


def test_covalent_runs_without_body_rates():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = simulate_kinetics({"mode": "covalent_timecourse", "num_points": 20})
    assert out["calibrated"] is False
    assert out["confidence_tier"] == "hypothesis_only"
    assert out["rates_used"]["spy_k_on_per_M_s"] == pytest.approx(1.4e3)
    assert out["rates_used"]["path"] == "lumped_irreversible"
    assert out["rates_used"]["spy_k_rev_per_s"] is None
    series = out["series"]
    assert len(series["adduct_M"]) == 20
    assert series["adduct_M"][-1] >= series["adduct_M"][0]
    assert math.isfinite(series["adduct_M"][-1])


def test_lab_override_wins_three_step():
    out = simulate_kinetics(
        {
            "mode": "covalent_timecourse",
            "spy_k_on_per_M_s": 1.0,
            "spy_k_rev_per_s": 0.1,
            "spy_k_bond_per_s": 0.05,
            "tag0_M": 1.0,
            "catcher0_M": 1.0,
            "num_points": 20,
        }
    )
    assert out["rates_used"]["spy_k_on_per_M_s"] == pytest.approx(1.0)
    assert out["rates_used"]["path"] == "three_step"
    assert out["calibrated"] is False


def test_clearing_priors_without_lab_rate_errors():
    with pytest.raises(KineticsSimError) as exc:
        simulate_kinetics(
            {
                "mode": "covalent_timecourse",
                "use_literature_priors": False,
            }
        )
    assert "spy_k_on_per_M_s" in str(exc.value)


def test_null_sigma_not_stored_as_zero():
    payload = get_kinetics_schema()
    slots = {row["name"]: row for row in payload["rate_slots"]}
    assert slots["spy_k_rev_per_s"]["sigma"] is None
    assert slots["nanobit_kd_M"]["sigma"] is None


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
    cov = client.post(
        "/api/kinetics/simulate",
        json={"mode": "covalent_timecourse", "num_points": 8},
    )
    assert cov.status_code == 200
    assert cov.json()["calibrated"] is False


def test_default_slots_count():
    assert len(default_rate_slots()) == 7
