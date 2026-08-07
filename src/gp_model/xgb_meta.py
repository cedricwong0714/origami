"""
XGBoost meta-predictor (CLASP Docs-6 Layer 3).

Soft dependency: xgboost is optional. This layer activates only after
≥15 experimental samples. With fewer points it raises InsufficientDataError
and the stacked ensemble falls back to mechanistic + GP.
"""

from __future__ import annotations

from typing import Optional

import numpy as np


class InsufficientDataError(ValueError):
    """Raised when XGBoost is requested with too few samples."""


class MissingDependencyError(ImportError):
    """Raised when xgboost is not installed."""


class XGBoostMetaPredictor:
    """
    Meta-learner on mechanistic residuals. Gated at MIN_SAMPLES_REQUIRED=15.
    """

    MIN_SAMPLES_REQUIRED = 15

    def __init__(self):
        self.model = None
        self.is_fitted = False
        self.loo_rmse: Optional[float] = None
        self.feature_names: list[str] = []
        self._n_features: Optional[int] = None

    def _ensure_xgb(self):
        try:
            import xgboost as xgb  # noqa: F401
        except ImportError as exc:
            raise MissingDependencyError(
                "xgboost is not installed. Install with "
                "`pip install xgboost` or `pip install origami[ml]` "
                "before activating Layer 3. Until then use ResidualGP."
            ) from exc
        return __import__("xgboost")

    def fit(
        self,
        X: np.ndarray,
        y_residual: np.ndarray,
        feature_names: Optional[list[str]] = None,
    ) -> XGBoostMetaPredictor:
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        y_residual = np.asarray(y_residual, dtype=float)

        if len(X) < self.MIN_SAMPLES_REQUIRED:
            raise InsufficientDataError(
                f"XGBoost meta-predictor requires at least "
                f"{self.MIN_SAMPLES_REQUIRED} samples. You have {len(X)}. "
                f"Use the Gaussian Process layer instead."
            )

        xgb = self._ensure_xgb()
        from sklearn.metrics import mean_squared_error
        from sklearn.model_selection import LeaveOneOut

        self.model = xgb.XGBRegressor(
            n_estimators=100,
            max_depth=3,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
        )
        self.feature_names = feature_names or [f"f{i}" for i in range(X.shape[1])]
        self._n_features = X.shape[1]

        loo = LeaveOneOut()
        loo_predictions = np.zeros(len(y_residual))
        for train_idx, test_idx in loo.split(X):
            self.model.fit(X[train_idx], y_residual[train_idx])
            loo_predictions[test_idx] = self.model.predict(X[test_idx])
        self.loo_rmse = float(
            np.sqrt(mean_squared_error(y_residual, loo_predictions))
        )
        self.model.fit(X, y_residual)
        self.is_fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self.is_fitted or self.model is None:
            raise RuntimeError("XGBoostMetaPredictor must be fitted before predict.")
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return np.asarray(self.model.predict(X), dtype=float)

    def get_feature_importance(self) -> dict[str, float]:
        if not self.is_fitted or self.model is None:
            return {}
        return dict(zip(self.feature_names, self.model.feature_importances_.tolist()))
