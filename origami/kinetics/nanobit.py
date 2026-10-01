"""Reversible NanoBiT complementation from the Dixon 2016 rates.

The ODE uses the printed association and dissociation rates:

    d[complex]/dt = k_on [Lg][Sm] − k_off [complex]

The kinetic dissociation constant is k_off / k_on. The printed 190 μM
Kd is returned beside that quotient. It is not substituted into the
ODE. k_on is the paper's approximate 500 M^-1 s^-1 and has no printed
standard error, so the rate uncertainty stays omitted.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp

from origami.priors import NANOBIT_K_OFF_PER_S, NANOBIT_K_ON_PER_M_S, NANOBIT_KD_M

# Numerical comparison of k_off/k_on with the printed Kd. Not a biological tolerance.
_KD_MATCH_RELATIVE = 1e-2


class NanoBitError(ValueError):
    """The complementation request is not usable."""


def kinetic_kd_M(k_on_per_M_s: float, k_off_per_s: float) -> float:
    """Return k_off / k_on. This is not the printed 190 μM cell."""
    if k_on_per_M_s <= 0 or k_off_per_s <= 0:
        raise NanoBitError("k_on and k_off must be > 0")
    return float(k_off_per_s / k_on_per_M_s)


def equilibrium_complex_M(
    lg0_M: float,
    sm0_M: float,
    kd_M: float,
) -> float:
    """Solve kon (L−x)(S−x) = koff x for the complex concentration x.

    ``kd_M`` here is the dissociation constant of the law being solved.
    Callers that want the Dixon ODE pass k_off / k_on.
    """
    if lg0_M < 0 or sm0_M < 0 or kd_M <= 0:
        raise NanoBitError("concentrations must be >= 0 and Kd must be > 0")
    total = lg0_M + sm0_M + kd_M
    disc = total * total - 4.0 * lg0_M * sm0_M
    if disc < 0 and disc > -1e-18:
        disc = 0.0
    if disc < 0:
        raise NanoBitError("equilibrium discriminant is negative")
    return float(0.5 * (total - math.sqrt(disc)))


def simulate_nanobit_complementation(
    *,
    lg0_M: float,
    sm0_M: float,
    k_on_per_M_s: float | None = None,
    k_off_per_s: float | None = None,
    t_end_s: float | None = None,
    num_points: int = 80,
) -> dict[str, Any]:
    """Integrate untethered LgBiT + SmBiT mass action."""
    kon = float(NANOBIT_K_ON_PER_M_S.value if k_on_per_M_s is None else k_on_per_M_s)
    koff = float(NANOBIT_K_OFF_PER_S.value if k_off_per_s is None else k_off_per_s)
    _require_positive("lg0_M", lg0_M)
    _require_positive("sm0_M", sm0_M)
    if kon <= 0 or koff <= 0:
        raise NanoBitError("k_on and k_off must be > 0")
    if num_points < 2:
        raise NanoBitError("num_points must be >= 2")
    kd_kinetic = kinetic_kd_M(kon, koff)
    printed = float(NANOBIT_KD_M.value)
    if t_end_s is None:
        # Twenty times 1 / (k_on * max(C) + k_off). A numerical window, not an assay endpoint.
        relax = kon * max(lg0_M, sm0_M) + koff
        t_end_s = 20.0 / relax
    if t_end_s <= 0:
        raise NanoBitError("t_end_s must be > 0")

    def rhs(_t: float, y: np.ndarray) -> np.ndarray:
        lg, sm, _complex = (float(v) for v in y)
        formed = kon * lg * sm - koff * _complex
        return np.array([-formed, -formed, formed])

    t_eval = np.linspace(0.0, float(t_end_s), int(num_points))
    sol = solve_ivp(
        rhs,
        (0.0, float(t_end_s)),
        np.array([float(lg0_M), float(sm0_M), 0.0]),
        t_eval=t_eval,
        rtol=1e-6,
        atol=1e-12,
    )
    if not sol.success:
        raise NanoBitError(f"NanoBiT ODE failed: {sol.message}")
    equilibrium = equilibrium_complex_M(lg0_M, sm0_M, kd_kinetic)
    warnings = [
        "Dixon 2016 rates are for untethered fragments, not a fusion.",
        (
            "k_on is printed as approximately 500 M^-1 s^-1 and has no "
            "standard error. That uncertainty is omitted, not stored as zero."
        ),
        "A passing integration is not scientific validation.",
    ]
    if abs(kd_kinetic - printed) / printed > _KD_MATCH_RELATIVE:
        warnings.append(
            "k_off / k_on is "
            f"{kd_kinetic:.6g} M. The printed Kd is {printed:.6g} M. "
            "The ODE uses k_on and k_off. The printed Kd is not substituted."
        )
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "units": {"concentration": "M", "time": "s"},
        "rates_used": {
            "nanobit_k_on_per_M_s": kon,
            "nanobit_k_on_sigma": NANOBIT_K_ON_PER_M_S.sigma,
            "nanobit_k_off_per_s": koff,
            "nanobit_k_off_sigma": NANOBIT_K_OFF_PER_S.sigma,
            "printed_kd_M": printed,
            "printed_kd_sigma_M": NANOBIT_KD_M.sigma,
            "kinetic_kd_M": kd_kinetic,
            "path": "reversible_bimolecular",
            "k_on_origin": "literature_prior" if k_on_per_M_s is None else "caller",
            "k_off_origin": "literature_prior" if k_off_per_s is None else "caller",
        },
        "equilibrium_complex_M": equilibrium,
        "equilibrium_uses": "k_off / k_on",
        "time_s": [float(x) for x in sol.t],
        "series": {
            "lg_M": [float(x) for x in sol.y[0]],
            "sm_M": [float(x) for x in sol.y[1]],
            "complex_M": [float(x) for x in sol.y[2]],
        },
        "assumptions": [
            "Well-mixed reversible bimolecular mass action.",
            "The kinetic Kd is k_off / k_on from Dixon et al. 2016.",
            "The printed 190 μM Kd is reported and is not the ODE parameter.",
        ],
        "warnings": warnings,
        "sources": {
            "k_on": NANOBIT_K_ON_PER_M_S.source,
            "k_off": NANOBIT_K_OFF_PER_S.source,
            "printed_kd": NANOBIT_KD_M.source,
        },
    }


def _require_positive(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise NanoBitError(f"{name} must be a number")
    if not math.isfinite(float(value)) or float(value) < 0:
        raise NanoBitError(f"{name} must be finite and >= 0")
