"""Quality section and uncertainty budget (synthetic replicates)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.lab.quality import run_quality
from origami.lab.uncertainty_budget import uncertainty_budget

client = TestClient(app)


def test_uncertainty_budget_from_replicates():
    out = uncertainty_budget([100.0, 108.0, 92.0, 101.0])
    assert out["computable"] is True
    assert out["cv"] > 0
    assert out["suggested_sigma_obs_rlu"] == pytest.approx(out["mean_rlu"] * out["cv"])


def test_quality_inter_day_and_irreversibility():
    out = run_quality(
        {
            "inter_day_rlu": [1.0, 1.1, 0.9],
            "competitor_fold": 20.0,
            "complex_fraction_after_h": 0.0,
        }
    )
    assert out["sections"]["inter_day_cv"]["computable"] is True
    assert out["pooled_gp_noise"]["computable"] is True
    assert out["sections"]["irreversibility"]["reversal_observed"] is False


def test_meta_endpoints():
    deps = client.get("/api/meta/dependencies")
    assert deps.status_code == 200
    assert "no_lab_data" in deps.json()
    cfg = client.get("/api/meta/active-learning-config")
    assert cfg.status_code == 200
    assert cfg.json()["config"]["version"]
