"""Map a docking effective concentration onto sourced kinetic rates.

Spy uses the Zakeri 2012 apparent bimolecular rate as a tethered
pseudo-first-order step:

    k_obs = k_on * C_eff
    t_half = ln(2) / k_obs

NanoBiT occupancy uses the printed Dixon Kd:

    θ = C_eff / (C_eff + Kd)

The relaxation rate uses the printed k_on and k_off:

    k_relax = k_on * C_eff + k_off

Neither calculation invents a payload radius. A missing C_eff leaves
the block uncomputed. k_rev and k_bond stay out of this map.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

from origami.kinetics.nanobit import kinetic_kd_M
from origami.priors import (
    NANOBIT_K_OFF_PER_S,
    NANOBIT_K_ON_PER_M_S,
    NANOBIT_KD_M,
    SPY_K_ON_PER_M_S,
)

_Z95 = 1.96
_LN2 = math.log(2.0)


def local_kinetics(
    c_eff_M: float | None,
    c_eff_sigma_M: float | None,
    *,
    spy_k_on_per_M_s: float | None = None,
    spy_k_on_sigma: float | None = None,
) -> dict[str, Any]:
    """Return tethered Spy and NanoBiT scalars at one effective concentration."""
    if c_eff_M is None or not math.isfinite(c_eff_M) or c_eff_M <= 0:
        return {
            "computable": False,
            "calibrated": False,
            "confidence_tier": "hypothesis_only",
            "missing": ["effective concentration from two payload radii"],
            "spy_k_rev_per_s": None,
            "spy_k_bond_per_s": None,
        }
    literature_on = spy_k_on_per_M_s is None
    k_on = float(SPY_K_ON_PER_M_S.value if literature_on else spy_k_on_per_M_s)
    if not math.isfinite(k_on) or k_on <= 0:
        return {
            "computable": False,
            "calibrated": False,
            "confidence_tier": "hypothesis_only",
            "missing": ["spy k_on must be finite and > 0"],
            "spy_k_rev_per_s": None,
            "spy_k_bond_per_s": None,
        }
    k_on_sigma = (
        SPY_K_ON_PER_M_S.sigma
        if literature_on
        else (None if spy_k_on_sigma is None else float(spy_k_on_sigma))
    )
    if k_on_sigma is not None and (not math.isfinite(k_on_sigma) or k_on_sigma < 0):
        k_on_sigma = None
    sigma_c = (
        None
        if c_eff_sigma_M is None
        or not math.isfinite(c_eff_sigma_M)
        or c_eff_sigma_M < 0
        else float(c_eff_sigma_M)
    )
    k_obs = k_on * c_eff_M
    k_obs_sigma = _product_sigma(k_on, k_on_sigma, c_eff_M, sigma_c)
    half, half_sigma, half_note = _half_life(k_obs, k_obs_sigma)
    theta, theta_sigma = _langmuir_theta(c_eff_M, sigma_c, float(NANOBIT_KD_M.value))
    theta_low = _low(theta, theta_sigma)
    theta_high = _high(theta, theta_sigma)
    theta_note = (
        "The occupancy band is the delta method on C_eff. "
        "The printed Kd has no standard error, so that uncertainty is omitted."
    )
    if (
        theta_low is not None
        and theta_high is not None
        and (theta_low < 0 or theta_high > 1)
    ):
        theta_note += " The linear band leaves [0, 1]. It is reported unclipped."
    kon_nb = float(NANOBIT_K_ON_PER_M_S.value)
    koff_nb = float(NANOBIT_K_OFF_PER_S.value)
    relax = kon_nb * c_eff_M + koff_nb
    relax_sigma = None if sigma_c is None else kon_nb * sigma_c
    return {
        "computable": True,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "missing": [],
        "spy_k_rev_per_s": None,
        "spy_k_bond_per_s": None,
        "spy": {
            "k_on_per_M_s": k_on,
            "k_on_sigma": k_on_sigma,
            "k_on_origin": "literature_prior" if literature_on else "caller",
            "k_obs_per_s": k_obs,
            "k_obs_sigma_per_s": k_obs_sigma,
            "k_obs_95_lower_per_s": _low(k_obs, k_obs_sigma),
            "k_obs_95_upper_per_s": _high(k_obs, k_obs_sigma),
            "t_half_s": half,
            "t_half_sigma_s": half_sigma,
            "t_half_note": half_note,
            "source": SPY_K_ON_PER_M_S.source,
            "equation": "k_obs = k_on * C_eff; t_half = ln(2) / k_obs",
            "note": (
                "Tethered pseudo-first-order step at this effective concentration. "
                "It is not the well-mixed 10 μM Zakeri mixing condition. "
                "k_rev and k_bond are not in this calculation."
            ),
        },
        "nanobit": {
            "printed_kd_M": float(NANOBIT_KD_M.value),
            "printed_kd_sigma_M": NANOBIT_KD_M.sigma,
            "kinetic_kd_M": kinetic_kd_M(kon_nb, koff_nb),
            "k_on_per_M_s": kon_nb,
            "k_off_per_s": koff_nb,
            "theta_ss": theta,
            "theta_sigma": theta_sigma,
            "theta_95_lower": theta_low,
            "theta_95_upper": theta_high,
            "theta_note": theta_note,
            "k_relax_per_s": relax,
            "k_relax_sigma_per_s": relax_sigma,
            "equation": "theta = C_eff / (C_eff + Kd_printed); k_relax = k_on * C_eff + k_off",
            "note": (
                "Occupancy uses the printed 190 μM Kd. "
                "k_relax uses the printed k_on and k_off. "
                "Those k_on and k_off have no printed standard error, "
                "so their uncertainty is omitted. "
                "kinetic_kd_M is k_off / k_on and is not substituted for the printed Kd."
            ),
        },
    }


def _product_sigma(
    a: float,
    sigma_a: float | None,
    b: float,
    sigma_b: float | None,
) -> float | None:
    if sigma_a is None and sigma_b is None:
        return None
    var = 0.0
    if sigma_a is not None and a != 0:
        var += (sigma_a / a) ** 2
    if sigma_b is not None and b != 0:
        var += (sigma_b / b) ** 2
    if var == 0.0 and sigma_a is None and sigma_b is None:
        return None
    return abs(a * b) * math.sqrt(var)


def _half_life(
    k_obs: float, sigma: float | None
) -> tuple[float | None, float | None, str]:
    if k_obs <= 0:
        return None, None, "k_obs is not positive, so the half-life is omitted."
    if sigma is not None and _Z95 * sigma >= abs(k_obs):
        return (
            None,
            None,
            "The 95% band on k_obs reaches zero, so the half-life is omitted.",
        )
    half = _LN2 / k_obs
    half_sigma = None if sigma is None else _LN2 * sigma / (k_obs**2)
    return (
        half,
        half_sigma,
        "t_half = ln(2) / k_obs from the tethered pseudo-first-order step.",
    )


def _langmuir_theta(
    c_eff_M: float, sigma_c: float | None, kd_M: float
) -> tuple[float, float | None]:
    theta = c_eff_M / (c_eff_M + kd_M)
    if sigma_c is None:
        return theta, None
    derivative = kd_M / (c_eff_M + kd_M) ** 2
    return theta, abs(derivative) * sigma_c


def _low(value: float, sigma: float | None) -> float | None:
    if sigma is None:
        return None
    return value - _Z95 * sigma


def _high(value: float, sigma: float | None) -> float | None:
    if sigma is None:
        return None
    return value + _Z95 * sigma
