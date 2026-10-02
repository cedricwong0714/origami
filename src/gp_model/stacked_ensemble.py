"""
Stacked ensemble predictor (CLASP Docs-6).

Layer 1: Mechanistic CLASP ODE (always active)
Layer 2: ResidualGP Matérn correction (active after fit, typically ≥4 points)
Layer 3: XGBoost meta-predictor (active only after ≥15 points AND xgboost installed)
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field

from src.core.clasp_assembly import CLASPParameters, predict_luminescence
from src.gp_model.residual_gp import ResidualGP
from src.gp_model.xgb_meta import InsufficientDataError, XGBoostMetaPredictor


class StackedPrediction(BaseModel):
    predicted_value: float
    uncertainty_95_lower: float
    uncertainty_95_upper: float
    confidence_tier: str
    mechanistic_prediction: float
    gp_correction: float
    xgb_correction: float = 0.0
    xgb_active: bool
    model_version: str = "stacked_ensemble_1.0.0"
    warnings: list[str] = Field(default_factory=list)


class StackedEnsemblePredictor:
    """Orchestrates the three-layer Stream 1 prediction stack."""

    def __init__(
        self,
        params: Optional[CLASPParameters] = None,
        version: str = "1.0.0",
    ):
        self.params = params or CLASPParameters()
        self.gp = ResidualGP()
        self.xgb = XGBoostMetaPredictor()
        self.n_observations = 0
        self.version = version
        self.calibrated_ranges: dict[str, tuple[float, float]] = {}
        self._feature_names = ["calcium_M", "E_T", "M_T"]

    def mechanistic_predict(
        self,
        calcium_M: float,
        E_T: float = 1e-6,
        M_T: float = 1e-6,
        t_end: float = 3600.0,
    ) -> float:
        series = np.asarray([calcium_M], dtype=float)
        return float(
            predict_luminescence(series, self.params, E_T=E_T, M_T=M_T, t_end=t_end)[0]
        )

    def to_features(
        self, calcium_M: float, E_T: float = 1e-6, M_T: float = 1e-6
    ) -> np.ndarray:
        return np.asarray([[calcium_M, E_T, M_T]], dtype=float)

    def fit_observations(
        self,
        X_design: np.ndarray,
        y_observed: np.ndarray,
        y_mechanistic: Optional[np.ndarray] = None,
        try_xgb: bool = True,
    ) -> dict[str, Any]:
        """
        Fit Layer 2 (always if ≥1 point) and Layer 3 (if ≥15 and xgboost present).
        """
        X = np.asarray(X_design, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        y_obs = np.asarray(y_observed, dtype=float)
        if y_mechanistic is None:
            y_mech = np.array(
                [self.mechanistic_predict(float(row[0]), float(row[1]) if X.shape[1] > 1 else 1e-6,
                                          float(row[2]) if X.shape[1] > 2 else 1e-6)
                 for row in X]
            )
        else:
            y_mech = np.asarray(y_mechanistic, dtype=float)

        self.gp.fit(X, y_obs, y_mech)
        self.n_observations = len(y_obs)
        # Default calibrated range on calcium
        self.calibrated_ranges = {
            "calcium_M": (float(np.min(X[:, 0])), float(np.max(X[:, 0]))),
        }

        xgb_status = "inactive"
        if try_xgb and len(y_obs) >= XGBoostMetaPredictor.MIN_SAMPLES_REQUIRED:
            try:
                # Train Layer 3 on the residual remaining after Layer 2 (GP)
                y_gp_pred, _ = self.gp.predict(X, y_mech)
                residuals_l2 = y_obs - y_gp_pred
                self.xgb.fit(X, residuals_l2, feature_names=self._feature_names[: X.shape[1]])
                xgb_status = "fitted"
            except (InsufficientDataError, ImportError) as exc:
                xgb_status = f"skipped: {exc}"

        return {
            "n_observations": self.n_observations,
            "gp_fitted": self.gp.is_fitted,
            "xgb_status": xgb_status,
            "xgb_loo_rmse": self.xgb.loo_rmse,
        }

    def predict(
        self,
        calcium_M: float,
        E_T: float = 1e-6,
        M_T: float = 1e-6,
        t_end: float = 3600.0,
    ) -> StackedPrediction:
        y_mech = self.mechanistic_predict(calcium_M, E_T=E_T, M_T=M_T, t_end=t_end)
        X = self.to_features(calcium_M, E_T, M_T)
        y_corrected, unc = self.gp.predict(X, np.asarray([y_mech]))
        y_corr = float(y_corrected[0])
        half_gp = float(unc[0])
        sigma_gp = half_gp / 1.96

        warnings_list: list[str] = []
        xgb_corr = 0.0
        if self.xgb.is_fitted:
            meta = float(self.xgb.predict(X)[0])
            xgb_corr = meta
            y_final = y_corr + meta
            # Propagate uncertainty from GP and XGBoost LOO RMSE
            loo_rmse = self.xgb.loo_rmse or 0.0
            sigma_total = float(np.sqrt(sigma_gp**2 + loo_rmse**2))
            half = 1.96 * sigma_total
        else:
            y_final = y_corr
            half = half_gp
            if self.n_observations < XGBoostMetaPredictor.MIN_SAMPLES_REQUIRED:
                warnings_list.append(
                    f"XGBoost Layer 3 inactive ({self.n_observations}/"
                    f"{XGBoostMetaPredictor.MIN_SAMPLES_REQUIRED} samples)."
                )

        tier = self.gp.get_confidence_tier(X, self.calibrated_ranges)[0]
        return StackedPrediction(
            predicted_value=y_final,
            uncertainty_95_lower=y_final - half,
            uncertainty_95_upper=y_final + half,
            confidence_tier=tier,
            mechanistic_prediction=y_mech,
            gp_correction=y_corr - y_mech,
            xgb_correction=xgb_corr,
            xgb_active=self.xgb.is_fitted,
            model_version=f"stacked_ensemble_{self.version}",
            warnings=warnings_list,
        )

    def get_xgb_feature_importance(self) -> dict[str, float]:
        """Return feature importance from the XGBoost layer if fitted."""
        return self.xgb.get_feature_importance()
