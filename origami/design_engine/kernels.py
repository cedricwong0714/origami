"""Stationary kernels. Matrices, not elementwise linear maps."""

from __future__ import annotations

import numpy as np
from scipy.spatial.distance import cdist


def matern52(X: np.ndarray, Y: np.ndarray, lengthscale: float, variance: float) -> np.ndarray:
    X = np.atleast_2d(np.asarray(X, dtype=float))
    Y = np.atleast_2d(np.asarray(Y, dtype=float))
    if lengthscale <= 0 or variance <= 0:
        raise ValueError("kernel hyperparameters must be positive")
    r = cdist(X / lengthscale, Y / lengthscale, metric="euclidean")
    s = np.sqrt(5.0) * r
    return variance * (1.0 + s + (s**2) / 3.0) * np.exp(-s)
