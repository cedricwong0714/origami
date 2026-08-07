"""
Global sensitivity analysis (variance-based first-order Sobol indices).

Pure-numpy Saltelli-style estimator — no SALib dependency. Used to populate
PredictionResult.most_sensitive_parameter honestly from parameter ranges.
"""

from __future__ import annotations

from typing import Callable

import numpy as np


def sobol_first_order(
    model_func: Callable[[np.ndarray], float],
    bounds: list[tuple[float, float]],
    n_samples: int = 256,
    rng: np.random.Generator | None = None,
) -> dict[str, float]:
    """
    Estimate first-order Sobol indices S_i for each parameter.

    model_func(theta) -> scalar output
    bounds: list of (low, high) per parameter

    Returns dict mapping param index string to S_i (approximately in [0,1]).
    """
    rng = rng or np.random.default_rng(42)
    d = len(bounds)
    lows = np.array([b[0] for b in bounds], dtype=float)
    highs = np.array([b[1] for b in bounds], dtype=float)

    def sample(n: int) -> np.ndarray:
        u = rng.random((n, d))
        return lows + u * (highs - lows)

    A = sample(n_samples)
    B = sample(n_samples)
    fA = np.array([model_func(row) for row in A])
    fB = np.array([model_func(row) for row in B])
    var_y = float(np.var(np.concatenate([fA, fB]), ddof=1))
    if var_y < 1e-18:
        return {str(i): 0.0 for i in range(d)}

    indices: dict[str, float] = {}
    for i in range(d):
        AB_i = A.copy()
        AB_i[:, i] = B[:, i]
        fAB_i = np.array([model_func(row) for row in AB_i])
        # Saltelli first-order estimator
        Si = float(np.mean(fB * (fAB_i - fA)) / var_y)
        indices[str(i)] = max(0.0, min(1.0, Si))
    return indices


def most_sensitive_parameter(
    model_func: Callable[[np.ndarray], float],
    parameter_names: list[str],
    bounds: list[tuple[float, float]],
    n_samples: int = 128,
) -> tuple[str, dict[str, float]]:
    """Return (most_sensitive_name, {name: S_i})."""
    raw = sobol_first_order(model_func, bounds, n_samples=n_samples)
    named = {parameter_names[int(k)]: v for k, v in raw.items()}
    best = max(named, key=named.get) if named else parameter_names[0]
    return best, named
