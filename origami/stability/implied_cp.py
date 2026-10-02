"""Back-calculate the constant ΔCp implied by a printed ΔG, ΔHcal and Tm.

Gibbs-Helmholtz with constant ΔCp (see origami.stability.thermo):

    ΔG(T) = ΔHcal (1 - T/Tm) + ΔCp ((T - Tm) - T ln(T/Tm))

Solving for ΔCp given the printed ΔG at T gives the value that makes the
published numbers self-consistent. It is a derived, model-dependent number,
NOT the ΔCp Phillips et al. 2012 used and NOT a literature value. The
source of that ΔCp is unresolved. ``calibrated`` is always false.
First-order uncertainty uses independent Gaussian errors on ΔHcal and ΔG and
treats Tm as exact, so it understates the true spread.
"""

from __future__ import annotations

import math
from typing import Any

_C_TO_K = 273.15  # unit definition


def implied_delta_cp(
    t_c: float,
    tm_c: float,
    delta_h_cal: float,
    delta_g: float,
    delta_h_sigma: float | None = None,
    delta_g_sigma: float | None = None,
) -> dict[str, Any]:
    """Return the constant ΔCp (kcal mol-1 K-1) implied by ΔG(T), ΔHcal and Tm."""
    vals = (t_c, tm_c, delta_h_cal, delta_g)
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in vals):
        raise ValueError("all inputs must be finite numbers")
    t, tm = t_c + _C_TO_K, tm_c + _C_TO_K
    if t <= 0 or tm <= 0:
        raise ValueError("temperatures must be above absolute zero")
    if t == tm:
        raise ValueError("T equals Tm: ΔG is 0 there and ΔCp is not identifiable")
    bracket = (t - tm) - t * math.log(t / tm)
    cp = (delta_g - delta_h_cal * (1.0 - t / tm)) / bracket
    sigma = None
    if delta_h_sigma is not None and delta_g_sigma is not None:
        sigma = math.sqrt(
            (delta_g_sigma / bracket) ** 2
            + (delta_h_sigma * (1.0 - t / tm) / bracket) ** 2
        )
    return {
        "delta_cp_implied": cp,
        "delta_cp_sigma_first_order": sigma,
        "units": "kcal mol-1 K-1",
        "origin": "derived_from_printed_delta_g_not_literature",
        "calibrated": False,
    }
