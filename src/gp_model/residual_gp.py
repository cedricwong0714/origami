"""
Residual Gaussian Process correction (CLASP Docs-6 Layer 2).

Learns the systematic discrepancy between mechanistic predictions and
experimental observations. Uses a Matérn(ν=2.5) kernel — more appropriate
than RBF for small biological datasets that may be non-smooth.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel
from sklearn.preprocessing import StandardScaler


class ResidualGP:
    """
    GP residual corrector for small-data CLASP calibration.

    The GP does not learn biology from scratch — only where the
    mechanistic model is systematically wrong.
    """

    def __init__(self, n_restarts: int = 10):
        kernel = (
            ConstantKernel(1.0, (1e-3, 1e3))
            * Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e3), nu=2.5)
            + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 1e1))
        )
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            n_restarts_optimizer=n_restarts,
            normalize_y=True,
            alpha=1e-6,
            random_state=42,
        )
        self.scaler_X = StandardScaler()
        self.is_fitted = False
        self.n_observations = 0

    def fit(
        self,
        X_design: np.ndarray,
        y_observed: np.ndarray,
        y_mechanistic: np.ndarray,
    ) -> ResidualGP:
        X = np.asarray(X_design, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        residuals = np.asarray(y_observed, dtype=float) - np.asarray(
            y_mechanistic, dtype=float
        )
        X_scaled = self.scaler_X.fit_transform(X)
        self.gp.fit(X_scaled, residuals)
        self.is_fitted = True
        self.n_observations = len(residuals)
        return self

    def predict(
        self,
        X_design: np.ndarray,
        y_mechanistic: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns (y_corrected, uncertainty_95_half_width).

        If unfitted, returns the mechanistic prediction with a wide
        prior half-width of 0.5 (relative units).
        """
        y_mech = np.asarray(y_mechanistic, dtype=float)
        if not self.is_fitted:
            return y_mech, np.ones_like(y_mech) * 0.5

        X = np.asarray(X_design, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        X_scaled = self.scaler_X.transform(X)
        residual_mean, residual_std = self.gp.predict(X_scaled, return_std=True)
        y_corrected = y_mech + residual_mean
        uncertainty_95 = 1.96 * residual_std
        return y_corrected, uncertainty_95

    def get_confidence_tier(
        self,
        X_design: np.ndarray,
        calibrated_ranges: Optional[dict[str, tuple[float, float]]] = None,
    ) -> list[str]:
        X = np.asarray(X_design, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        tiers: list[str] = []
        for row in X:
            if not self.is_fitted:
                tiers.append("hypothesis_only")
            elif calibrated_ranges and self._is_within_ranges(row, calibrated_ranges):
                tiers.append("interpolated")
            elif self.is_fitted:
                tiers.append("extrapolated")
            else:
                tiers.append("hypothesis_only")
        return tiers

    @staticmethod
    def _is_within_ranges(
        x: np.ndarray, ranges: dict[str, tuple[float, float]]
    ) -> bool:
        values = list(ranges.values())
        for i, (lo, hi) in enumerate(values):
            if i >= len(x):
                break
            if not (lo <= float(x[i]) <= hi):
                return False
        return True
