"""Exercise the XGBoost residual layer at its 15-row software gate.

The rows are synthetic. A fitted tree is not a calibrated AES model.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("xgboost")

from src.gp_model.stacked_ensemble import StackedEnsemblePredictor
from src.gp_model.xgb_meta import InsufficientDataError, XGBoostMetaPredictor


def test_xgb_meta_rejects_fewer_than_fifteen_rows():
    model = XGBoostMetaPredictor()
    X = np.arange(14, dtype=float).reshape(-1, 1)
    y = 0.1 * X.ravel()
    with pytest.raises(InsufficientDataError):
        model.fit(X, y)


def test_xgb_meta_fits_fifteen_synthetic_residuals():
    model = XGBoostMetaPredictor()
    X = np.arange(15, dtype=float).reshape(-1, 1)
    y = 0.1 * X.ravel()
    model.fit(X, y, feature_names=["x"])
    pred = model.predict(np.array([[7.0]]))
    assert pred.shape == (1,)
    assert np.isfinite(pred[0])
    assert model.loo_rmse is not None
    assert model.loo_rmse >= 0.0
    assert set(model.get_feature_importance()) == {"x"}


def test_stacked_ensemble_activates_xgb_at_fifteen_rows():
    predictor = StackedEnsemblePredictor()
    calcium = np.logspace(-7, -4, 15)
    X = np.column_stack([calcium, np.full(15, 1e-6), np.full(15, 1e-6)])
    y = np.linspace(10.0, 200.0, 15)
    report = predictor.fit_observations(X, y, try_xgb=True)
    assert report["xgb_status"] == "fitted"
    assert report["gp_fitted"] is True
    prediction = predictor.predict(float(calcium[7]))
    assert prediction.xgb_active is True
    assert prediction.uncertainty_95_lower <= prediction.predicted_value
    assert prediction.predicted_value <= prediction.uncertainty_95_upper
