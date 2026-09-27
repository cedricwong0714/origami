"""Signal-gated recruitment occupancy.

Mass-action for one class of sites:

    dθ/dt = k_on * C_free * (1 − θ) − k_off * θ
    k_off = k_on * K_d
    θ_ss = C_free / (C_free + K_d)

K_d default is the published CaM–M13 peptide value. k_on is not in that
paper and is never invented: without k_on the result is steady state only.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp

from origami.io.signal_pairs import SignalPair
from origami.priors import CAM_M13_KD_M


@dataclass
class OccupancyResult:
    theta_ss: float
    theta_95_lower: float
    theta_95_upper: float
    kd_M: float
    kd_sigma_M: float
    c_free_M: float
    kon_per_M_s: float | None
    time_s: np.ndarray | None
    theta_t: np.ndarray | None
    units: str = "site_occupancy_fraction"
    confidence_tier: str = "literature_supported"
    calibrated: bool = False
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def steady_occupancy(c_free_M: float, kd_M: float) -> float:
    if c_free_M < 0 or kd_M <= 0:
        raise ValueError("C_free must be >= 0 and Kd must be > 0")
    return float(c_free_M / (c_free_M + kd_M))


def _rhs(_t: float, theta: np.ndarray, kon: float, c_free: float, koff: float) -> np.ndarray:
    th = float(theta[0])
    return np.array([kon * c_free * (1.0 - th) - koff * th])


def recruitment_occupancy(
    c_free_M: float,
    kon_per_M_s: float | None = None,
    kd_M: float | None = None,
    kd_sigma_M: float | None = None,
    t_end_s: float | None = None,
    signal_on: bool = True,
) -> OccupancyResult:
    kd = CAM_M13_KD_M.value if kd_M is None else kd_M
    sig = CAM_M13_KD_M.sigma if kd_sigma_M is None else kd_sigma_M
    if not signal_on:
        return OccupancyResult(
            theta_ss=0.0,
            theta_95_lower=0.0,
            theta_95_upper=0.0,
            kd_M=kd,
            kd_sigma_M=sig,
            c_free_M=c_free_M,
            kon_per_M_s=kon_per_M_s,
            time_s=None,
            theta_t=None,
            assumptions=["signal_on=False forces k_on_eff = 0 (binary gate, not a 4-site Ca2+ model)."],
            warnings=["No time course: association is off."],
        )
    theta = steady_occupancy(c_free_M, kd)
    kd_lo = max(kd - 1.96 * sig, kd * 1e-6)
    kd_hi = kd + 1.96 * sig
    # Higher Kd → lower occupancy. Bounds are the Kd interval, not a full posterior.
    theta_hi = steady_occupancy(c_free_M, kd_lo)
    theta_lo = steady_occupancy(c_free_M, kd_hi)
    assumptions = [
        "Langmuir single-site mass action.",
        "Free concentration is not depleted by binding.",
        "Kd interval is the published peptide Kd ± 1.96σ, not a CLASP fusion measurement.",
    ]
    warnings = [
        "Not this project's wet-lab calibration.",
    ]
    time_s = None
    theta_t = None
    if kon_per_M_s is not None:
        if kon_per_M_s <= 0:
            raise ValueError("kon must be > 0 when provided")
        koff = kon_per_M_s * kd
        if t_end_s is None:
            rate = kon_per_M_s * c_free_M + koff
            t_end_s = 20.0 / max(rate, 1e-12)
        sol = solve_ivp(
            _rhs,
            (0.0, float(t_end_s)),
            np.array([0.0]),
            args=(kon_per_M_s, c_free_M, koff),
            dense_output=False,
            rtol=1e-6,
            atol=1e-9,
        )
        if not sol.success:
            raise RuntimeError(f"recruitment ODE failed: {sol.message}")
        time_s = sol.t
        theta_t = sol.y[0]
        assumptions.append("k_off = k_on * Kd. k_on is user-supplied, not from the Kd paper.")
    else:
        warnings.append("No kon supplied, so only steady-state occupancy is returned.")
    return OccupancyResult(
        theta_ss=theta,
        theta_95_lower=theta_lo,
        theta_95_upper=theta_hi,
        kd_M=kd,
        kd_sigma_M=sig,
        c_free_M=c_free_M,
        kon_per_M_s=kon_per_M_s,
        time_s=time_s,
        theta_t=theta_t,
        assumptions=assumptions,
        warnings=warnings,
    )


def occupancy_for_pair(
    pair: SignalPair,
    c_free_M: float,
    signal_on: bool = True,
    t_end_s: float | None = None,
) -> OccupancyResult:
    """Occupancy for one signal pair at a free signal concentration.

    Forwards ``pair.kd_M``, ``pair.kon_per_M_s``, and ``pair.kd_sigma_M`` to
    ``recruitment_occupancy``. The steady state is the Langmuir isotherm

        θ_ss = C_free / (C_free + K_d)

    with K_d = ``pair.kd_M``. If ``kon_per_M_s`` is None, the result is
    steady state only (``time_s`` and ``theta_t`` are None). kon is not
    filled in.

    ``recruitment_occupancy`` treats a missing sigma as
    ``CAM_M13_KD_M.sigma``. This wrapper does not. When ``pair.kd_sigma_M``
    is None, the call passes ``kd_sigma_M=0`` so the occupancy interval is
    exactly ``(theta_ss, theta_ss)``, and a warning states that this Kd has
    no reported uncertainty. A supplied sigma, including the CaM–M13 prior
    on ``default_cam_m13_pair``, is passed through unchanged.
    """
    # None would be replaced inside recruitment_occupancy by the CaM–M13
    # sigma. Zero width is the explicit "no reported uncertainty" interval.
    sigma_for_call = 0.0 if pair.kd_sigma_M is None else pair.kd_sigma_M
    result = recruitment_occupancy(
        c_free_M=c_free_M,
        kon_per_M_s=pair.kon_per_M_s,
        kd_M=pair.kd_M,
        kd_sigma_M=sigma_for_call,
        t_end_s=t_end_s,
        signal_on=signal_on,
    )
    if pair.kd_sigma_M is None:
        result.warnings.append(
            "Kd has no reported uncertainty. The occupancy interval is the "
            "point estimate (theta_ss, theta_ss) and does not use "
            "CAM_M13_KD_M.sigma."
        )
        result.assumptions = [
            item
            for item in result.assumptions
            if "published peptide Kd" not in item
        ]
        result.assumptions.append(
            "No Kd sigma was supplied for this pair, so the occupancy "
            "interval has zero width."
        )
    elif not _uses_published_cam_m13_uncertainty(pair):
        result.assumptions = [
            item
            for item in result.assumptions
            if "published peptide Kd" not in item
        ]
        result.assumptions.append(
            "Kd interval uses the sigma supplied on this signal pair, "
            "not CAM_M13_KD_M.sigma."
        )
    return result


def _uses_published_cam_m13_uncertainty(pair: SignalPair) -> bool:
    return (
        pair.kd_M == CAM_M13_KD_M.value
        and pair.kd_sigma_M == CAM_M13_KD_M.sigma
        and pair.kd_source == CAM_M13_KD_M.source
    )
