"""One Expected Improvement implementation for both acquisition stacks.

EI for maximization at a Gaussian posterior N(mean, std^2) with incumbent
``best`` and exploration offset ``xi``:

    z = (mean - best - xi) / std
    EI = (mean - best - xi) * Phi(z) + std * phi(z)

The two callers historically differed in two places, and both differences
are kept as explicit arguments rather than silently unified:

  * ``xi``: origami.design_engine uses 0.0; src.experiment_design uses 0.01.
    The 0.01 is a numerical exploration offset from the earlier code, not a
    biological constant, and has no cited source.
  * tiny-std handling: design_engine floors std at ``std_floor`` (1e-12);
    src.experiment_design sets EI to exactly 0 where std <= ``zero_below``
    (1e-9). Pass one or the other.

Both public functions keep their old signatures and outputs.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm


def expected_improvement_core(
    mean: np.ndarray,
    std: np.ndarray,
    best: float,
    xi: float = 0.0,
    std_floor: float | None = None,
    zero_below: float | None = None,
) -> np.ndarray:
    """Expected Improvement with explicit tiny-std policy (see module docstring)."""
    if (std_floor is None) == (zero_below is None):
        raise ValueError("give exactly one of std_floor or zero_below")
    mean = np.asarray(mean, dtype=float)
    std = np.asarray(std, dtype=float)
    improvement = mean - best - xi
    if std_floor is not None:
        s = np.maximum(std, std_floor)
        z = improvement / s
        return improvement * norm.cdf(z) + s * norm.pdf(z)
    zero_mask = std <= zero_below
    s = np.where(zero_mask, 1.0, std)
    z = improvement / s
    ei = improvement * norm.cdf(z) + s * norm.pdf(z)
    ei[zero_mask] = 0.0
    return ei
