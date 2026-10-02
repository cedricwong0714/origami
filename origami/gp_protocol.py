"""Common read interface over the two ResidualGP implementations.

``origami.design_engine.gp.ResidualGP`` (affine physics map plus Cholesky
Matern-5/2) and ``src.gp_model.residual_gp.ResidualGP`` (additive residual,
sklearn Matern-2.5 plus white noise) have different models and are NOT
numerically interchangeable. This adapter only gives callers one way to read
a prediction, without changing either model:

    mean, std = predict_mean_std(gp, X, physics)

Both return arrays of the same shape. ``std`` is the 1-sigma predictive
standard deviation. The design_engine posterior variance includes the noise
term; the sklearn path returns the latent residual std only (its 95%
half-width divided by 1.96). That difference is real and is reported by
``noise_included`` so a caller can account for it.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def predict_mean_std(gp: Any, X: np.ndarray, physics: np.ndarray) -> dict[str, Any]:
    """Return mean, std and which GP family produced them."""
    out = gp.predict(X, physics)
    if hasattr(out, "mean") and hasattr(out, "std"):
        return {
            "mean": np.asarray(out.mean, dtype=float),
            "std": np.asarray(out.std, dtype=float),
            "family": "design_engine_affine_cholesky",
            "noise_included": True,
        }
    mean, half = out
    return {
        "mean": np.asarray(mean, dtype=float),
        "std": np.asarray(half, dtype=float) / 1.96,
        "family": "sklearn_matern_additive",
        "noise_included": False,
    }
