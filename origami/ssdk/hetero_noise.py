"""Second GP on residual scatter. It does not edit assay CVs.

The target is log(residual^2) of the luminescence residual fit. Three or more
wet rows are required. The predicted sigma is a model of leftover scatter,
not a plate-reader coefficient of variation, and it is not written into
``data/config/active_learning_config.json``.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import ConstantKernel, Matern, WhiteKernel

_MIN_POINTS = 3
_EPS = 1e-6


def residual_scatter(
    X_train: np.ndarray,
    residuals: np.ndarray,
    X_pred: np.ndarray,
) -> dict[str, Any]:
    """Predict a positive scatter sigma at ``X_pred``. Unfitted below 3 rows."""
    residuals = np.asarray(residuals, dtype=float).ravel()
    base: dict[str, Any] = {
        "fitted": False,
        "calibrated": False,
        "replaces_assay_cv": False,
        "origin": "residual_scatter_model",
        "confidence_tier": "hypothesis_only",
    }
    if residuals.size < _MIN_POINTS:
        base["reason"] = (
            f"Need at least {_MIN_POINTS} wet residuals to fit scatter. "
            "Assay CVs in the config file are unchanged."
        )
        return base
    y = np.log(residuals**2 + _EPS)
    kernel = (
        ConstantKernel(1.0, (1e-3, 1e2))
        * Matern(length_scale=1.0, length_scale_bounds=(1e-2, 1e2), nu=2.5)
        + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-5, 1.0))
    )
    gp = GaussianProcessRegressor(
        kernel=kernel,
        n_restarts_optimizer=1,
        normalize_y=True,
        random_state=0,
    )
    gp.fit(np.asarray(X_train, dtype=float), y)
    log_var = gp.predict(np.asarray(X_pred, dtype=float))
    sigma = np.sqrt(np.exp(np.clip(log_var, -20.0, 20.0)))
    base.update(
        fitted=True,
        sigma= [float(v) for v in sigma],
        reason=(
            "GP on log squared residual. Not an assay CV and not written to the config."
        ),
    )
    return base
