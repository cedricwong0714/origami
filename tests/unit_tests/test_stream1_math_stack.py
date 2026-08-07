"""Unit tests for Docs-6 prediction stack, Fisher/EIG, freeze workflow."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from src.calibration.fisher import FisherInformationDesigner
from src.calibration.fit import fit_model_with_identifiability_check
from src.core.clasp_assembly import CLASPParameters, predict_luminescence
from src.experiment_design.bayesian_selector import BayesianExperimentSelector
from src.gp_model.residual_gp import ResidualGP
from src.gp_model.stacked_ensemble import StackedEnsemblePredictor
from src.gp_model.xgb_meta import InsufficientDataError, XGBoostMetaPredictor
from src.predictions.freeze import (
    compare_to_frozen,
    freeze_prediction,
    verify_frozen_checksum,
)


def test_residual_gp_corrects_and_returns_uncertainty():
    gp = ResidualGP()
    X = np.linspace(0, 1, 6).reshape(-1, 1)
    y_mech = np.ones(6)
    y_obs = y_mech + 0.2
    gp.fit(X, y_obs, y_mech)
    y_corr, unc = gp.predict(X, y_mech)
    assert gp.is_fitted
    assert np.all(unc >= 0)
    assert np.mean(y_corr) > np.mean(y_mech)


def test_xgb_rejects_small_data():
    xgb = XGBoostMetaPredictor()
    X = np.random.randn(5, 2)
    with pytest.raises(InsufficientDataError):
        xgb.fit(X, np.zeros(5))


def test_stacked_ensemble_layers():
    ens = StackedEnsemblePredictor()
    # mechanistic only
    pred0 = ens.predict(calcium_M=2e-6)
    assert pred0.xgb_active is False
    assert pred0.predicted_value > 0
    assert pred0.uncertainty_95_lower <= pred0.predicted_value <= pred0.uncertainty_95_upper

    # fit GP with synthetic residuals
    ca = np.logspace(-7, -4, 6)
    X = np.column_stack([ca, np.full(6, 1e-6), np.full(6, 1e-6)])
    y_mech = np.array([ens.mechanistic_predict(float(c)) for c in ca])
    y_obs = y_mech * 1.1
    status = ens.fit_observations(X, y_obs, y_mechanistic=y_mech, try_xgb=False)
    assert status["gp_fitted"] is True
    pred1 = ens.predict(calcium_M=2e-6)
    assert pred1.confidence_tier in {"interpolated", "extrapolated", "hypothesis_only"}


def test_fisher_identifiability_on_toy_linear():
    # y = a * x + b
    def model(theta, conditions):
        x = conditions.reshape(-1)
        return theta[0] * x + theta[1]

    designer = FisherInformationDesigner(model, ["a", "b"], noise_variance=0.01)
    theta = np.array([2.0, 1.0])
    conditions = np.linspace(0, 1, 10)
    report = designer.identifiability_report(theta, conditions, threshold_rel=10.0)
    assert report["d_optimality"] > 0
    assert len(report["parameter_names"]) == 2


def test_fit_with_identifiability():
    def model(theta, conditions):
        x = conditions.reshape(-1)
        return theta[0] * np.exp(-theta[1] * x)

    x = np.linspace(0, 2, 12)
    true = np.array([1.5, 0.8])
    y = model(true, x) + 0.01 * np.random.default_rng(0).normal(size=len(x))
    result = fit_model_with_identifiability_check(
        model,
        ["amp", "decay"],
        theta0=np.array([1.0, 1.0]),
        conditions=x,
        observations=y,
        bounds=(np.array([0.1, 0.01]), np.array([5.0, 5.0])),
        noise_variance=0.01,
    )
    assert result.success
    assert result.rmse < 0.1
    assert "amp" in result.fitted_values


def test_eig_recommends_ranked_list():
    gp = ResidualGP()
    X = np.linspace(0, 1, 8).reshape(-1, 1)
    y_mech = np.sin(2 * np.pi * X[:, 0])
    y_obs = y_mech + 0.05 * np.random.default_rng(1).normal(size=8)
    gp.fit(X, y_obs, y_mech)
    selector = BayesianExperimentSelector(gp)
    recs = selector.recommend(X, y_mech, objective="information_gain", n_recommendations=3)
    assert len(recs) == 3
    assert recs[0].rank == 1
    assert recs[0].acquisition_score >= recs[1].acquisition_score


def test_freeze_and_compare_roundtrip(tmp_path: Path):
    path = freeze_prediction(
        "unit_test_freeze_v1",
        design_spec={"scaffold": "CTPR5"},
        predictions={
            "short": {
                "predicted_value": 0.4,
                "uncertainty_95_lower": 0.2,
                "uncertainty_95_upper": 0.6,
                "confidence_tier": "hypothesis_only",
            },
            "opt": {
                "predicted_value": 0.7,
                "uncertainty_95_lower": 0.5,
                "uncertainty_95_upper": 0.9,
                "confidence_tier": "hypothesis_only",
            },
        },
        model_version="test_1.0.0",
        output_dir=tmp_path,
    )
    assert verify_frozen_checksum(path)
    cmp_path = compare_to_frozen(
        path,
        observations={"short": 0.45, "opt": 0.95},
        comparison_id="unit_test_cmp",
        output_dir=tmp_path,
    )
    payload = json.loads(cmp_path.read_text(encoding="utf-8"))
    assert payload["comparisons"]["short"]["within_95ci"] is True
    assert payload["comparisons"]["opt"]["within_95ci"] is False


def test_freeze_rejects_overwrite(tmp_path: Path):
    from src.compliance.data_integrity import DataOverwriteError

    kwargs = dict(
        prediction_id="no_overwrite",
        design_spec={},
        predictions={
            "a": {
                "predicted_value": 1.0,
                "uncertainty_95_lower": 0.5,
                "uncertainty_95_upper": 1.5,
                "confidence_tier": "hypothesis_only",
            }
        },
        model_version="1.0.0",
        output_dir=tmp_path,
    )
    freeze_prediction(**kwargs)
    with pytest.raises(DataOverwriteError):
        freeze_prediction(**kwargs)


def test_hill_n_matches_origami_invariant():
    """Docs-6 lists Linse n_h=2.5; ORIGAMI invariant wins (n=4)."""
    assert CLASPParameters().n_h == 4.0
    assert CLASPParameters().k_c_M == 2e-6


def test_sobol_identifies_dominant_parameter():
    from src.analysis.sensitivity import most_sensitive_parameter

    # y = 10*x0 + 0.1*x1  → x0 dominates
    def model(theta):
        return 10.0 * theta[0] + 0.1 * theta[1]

    best, scores = most_sensitive_parameter(
        model, ["x0", "x1"], [(0.0, 1.0), (0.0, 1.0)], n_samples=64
    )
    assert best == "x0"
    assert scores["x0"] > scores["x1"]
