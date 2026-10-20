"""Scaffold-length kinetics from the screw and the Gaussian chain.

For each repeat count the docking-site chord is the separation. The
Gaussian chain turns that separation into a local concentration. Occupancy
and the tethered lock half-life are then evaluated at that concentration.

The peptide Kd, the Zakeri on-rate, the Dixon rates, and the team locking
fit stay parameters. They are not the result. The result is how those
parameters change from n = 3 to n = 24.

calibrated stays false. This is not a measurement on a CLASP fusion.
"""

from __future__ import annotations

import math
from typing import Any

from origami.dry_lab_md import TEAM_KLOCK
from origami.physical.geometry import build_ctpr
from origami.physical.linkers import gaussian_chain_ceff_M
from origami.physical.recruitment import steady_occupancy
from origami.priors import (
    CAM_M13_KD_M,
    LINKER_SIGMA_A,
    N_REPEATS_MAX,
    N_REPEATS_MIN,
    NANOBIT_K_OFF_PER_S,
    NANOBIT_K_ON_PER_M_S,
    NANOBIT_KD_M,
    SPY_K_ON_PER_M_S,
)

_LN2 = math.log(2.0)
_Z95 = 1.96


def _half_life_s(rate_per_M_s: float, c_eff_M: float) -> float | None:
    if rate_per_M_s <= 0 or c_eff_M <= 0:
        return None
    seconds = _LN2 / (rate_per_M_s * c_eff_M)
    if not math.isfinite(seconds):
        return None
    return float(seconds)


def _theta_band(c_eff_M: float, kd_M: float, kd_sigma_M: float | None) -> tuple[float, float, float]:
    theta = steady_occupancy(c_eff_M, kd_M)
    if kd_sigma_M is None or kd_sigma_M <= 0:
        return theta, theta, theta
    kd_lo = max(kd_M - _Z95 * kd_sigma_M, kd_M * 1e-6)
    kd_hi = kd_M + _Z95 * kd_sigma_M
    # A larger Kd binds less, so the occupancy bounds swap.
    return theta, steady_occupancy(c_eff_M, kd_hi), steady_occupancy(c_eff_M, kd_lo)


def scaffold_kinetic_sweep(
    n_min: int = N_REPEATS_MIN,
    n_max: int = N_REPEATS_MAX,
) -> dict[str, Any]:
    """Occupancy and tethered half-life at every library length."""
    if n_min < 1 or n_max < n_min:
        raise ValueError("n_min and n_max must satisfy 1 <= n_min <= n_max")
    kinetic_kd = float(NANOBIT_K_OFF_PER_S.value) / float(NANOBIT_K_ON_PER_M_S.value)
    printed_kd = float(NANOBIT_KD_M.value)
    rows: list[dict[str, Any]] = []
    for n_repeats in range(int(n_min), int(n_max) + 1):
        chord_A = build_ctpr(n_repeats).end_to_end_A(0, n_repeats - 1)
        c_eff_M = float(gaussian_chain_ceff_M(chord_A))
        theta, theta_lo, theta_hi = _theta_band(
            c_eff_M,
            float(CAM_M13_KD_M.value),
            CAM_M13_KD_M.sigma,
        )
        rows.append(
            {
                "n_repeats": n_repeats,
                "chord_A": chord_A,
                "c_eff_M": c_eff_M,
                "theta_cam": theta,
                "theta_cam_95_lower": theta_lo,
                "theta_cam_95_upper": theta_hi,
                "t_half_literature_s": _half_life_s(float(SPY_K_ON_PER_M_S.value), c_eff_M),
                "t_half_team_s": _half_life_s(float(TEAM_KLOCK.value), c_eff_M),
                "theta_nanobit_kinetic": steady_occupancy(c_eff_M, kinetic_kd),
                "theta_nanobit_printed": steady_occupancy(c_eff_M, printed_kd),
            }
        )
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "linker_sigma_A": float(LINKER_SIGMA_A.value),
        "cam_kd_M": float(CAM_M13_KD_M.value),
        "spy_literature_per_M_s": float(SPY_K_ON_PER_M_S.value),
        "spy_team_per_M_s": float(TEAM_KLOCK.value),
        "nanobit_kinetic_kd_M": kinetic_kd,
        "nanobit_printed_kd_M": printed_kd,
        "rows": rows,
        "assumptions": [
            "Separation is the docking-site chord of the CTPR screw.",
            "Local concentration is the Gaussian chain at that chord.",
            "Cam occupancy uses the peptide Kd. It is not a fusion measurement.",
            "Spy half-life is ln(2) / (k C_eff), with the partner held at C_eff.",
            "The literature Spy rate and the team locking fit are both evaluated. They are not averaged.",
            "NanoBiT kinetic occupancy uses k_off / k_on. The printed 190 μM Kd is a separate curve.",
        ],
    }
