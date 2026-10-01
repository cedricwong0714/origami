"""Fit an apparent SpyCatcher lock rate to a gel time course.

The rate law is the lumped irreversible step already integrated in
``origami.kinetics.covalent``:

    d[adduct]/dt = k_lock [Tag][Catcher]

``fraction_locked`` is adduct divided by the limiting partner
(the smaller of the two starting concentrations). Times in the request
are minutes and are converted to seconds by multiplying by 60.

Six points determine one rate. They do not determine a separate
``k_rev`` and ``k_bond``, so the three-step ODE is not fit.

When the caller sets ``rate_law`` to ``pseudo_first_order``, the
fraction is ``1 − exp(−k_obs t)`` and

    k_lock = k_obs / [partner in excess]

The caller names which partner is in excess. This module does not
invent an excess threshold.

A fit whose standard error exceeds the rate, or whose rate sits on the
optimizer bound, is not reported. The Zakeri 2012 literature k_on is
returned beside a successful lab fit. It is not overwritten in
``origami.priors``.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any, Literal

import numpy as np
from scipy.optimize import curve_fit

from origami.assay.uncertainty import Z95, finite_number
from origami.assay.window import _result, _series
from origami.priors import SPY_K_ON_PER_M_S

# Numerical bounds on k_lock (M^-1 s^-1) and k_obs (s^-1). A fit that
# sits on either bound is not identifiable. These are not measured rates.
_RATE_FLOOR = 1e-8
_RATE_CEILING = 1e8

RateLaw = Literal["second_order", "pseudo_first_order"]
MODEL_NAME = "spy_lock_fit"
MODEL_VERSION = "1"


def _lock_result(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("model_name", MODEL_NAME)
    kwargs.setdefault("model_version", MODEL_VERSION)
    return _result(**kwargs)


def fit_lock(body: dict[str, Any]) -> dict[str, Any]:
    """Fit k_lock from ``time_min`` and ``fraction_locked``."""
    if not isinstance(body, dict):
        return _lock_result(
            computable=False, missing=["lock body must be an object"], warnings=[]
        )
    try:
        t_min = _series("time_min", body.get("time_min"))
        fraction = _series("fraction_locked", body.get("fraction_locked"))
        tag0 = finite_number("tag0_M", body.get("tag0_M"))
        catcher0 = finite_number("catcher0_M", body.get("catcher0_M"))
    except ValueError as exc:
        return _lock_result(computable=False, missing=[str(exc)], warnings=[])
    if t_min.size != fraction.size:
        return _lock_result(
            computable=False,
            missing=["time_min and fraction_locked must have the same length"],
            warnings=[],
        )
    if t_min.size < 3 or np.any(t_min < 0):
        return _lock_result(
            computable=False,
            missing=["at least three non-negative times are required"],
            warnings=[],
        )
    if np.any(fraction < 0) or np.any(fraction > 1):
        return _lock_result(
            computable=False,
            missing=["fraction_locked must be between 0 and 1"],
            warnings=[],
        )
    if tag0 <= 0 or catcher0 <= 0:
        return _lock_result(
            computable=False,
            missing=["tag0_M and catcher0_M must be > 0"],
            warnings=[],
        )

    law = body.get("rate_law", "second_order")
    if law not in ("second_order", "pseudo_first_order"):
        return _lock_result(
            computable=False,
            missing=["rate_law must be second_order or pseudo_first_order"],
            warnings=[],
        )
    sds = body.get("sds_survives")
    warnings = _sds_warnings(sds)
    t_s = t_min * 60.0
    if law == "second_order":
        fitted = _fit_second_order(t_s, fraction, tag0, catcher0)
    else:
        fitted = _fit_pseudo_first_order(t_s, fraction, body, tag0, catcher0)
    if not fitted["computable"]:
        fitted["warnings"] = warnings + fitted["warnings"]
        fitted["sds_survives"] = sds if isinstance(sds, bool) else None
        return fitted
    fitted["warnings"] = (
        warnings
        + [
            "Minutes were converted to seconds by multiplying by 60.",
            "k_rev and k_bond were not fit.",
            "The Zakeri 2012 k_on is a literature reference beside this fit, not a replacement of the lab rate.",
        ]
        + fitted["warnings"]
    )
    fitted["sds_survives"] = sds if isinstance(sds, bool) else None
    fitted["literature_k_on_per_M_s"] = SPY_K_ON_PER_M_S.value
    fitted["literature_k_on_sigma_per_M_s"] = SPY_K_ON_PER_M_S.sigma
    fitted["literature_source"] = SPY_K_ON_PER_M_S.source
    return fitted


def product_M(
    t_s: np.ndarray, k_per_M_s: float, tag0: float, catcher0: float
) -> np.ndarray:
    """Integrated adduct concentration for the lumped irreversible law."""
    t = np.asarray(t_s, dtype=float)
    k = float(k_per_M_s)
    if k == 0.0:
        return np.zeros_like(t, dtype=float)
    # Relative switch between the equal-start closed form and the
    # unequal-start closed form. 1e-8 is floating-point bookkeeping,
    # not a concentration that counts as biologically equal.
    if abs(tag0 - catcher0) / max(tag0, catcher0) < 1e-8:
        a = 0.5 * (tag0 + catcher0)
        return (a * a * k * t) / (1.0 + a * k * t)
    delta = tag0 - catcher0
    x = delta * k * t
    out = np.empty(t.shape, dtype=float)
    for index, xi in enumerate(np.atleast_1d(x)):
        if xi > 60.0:
            out[index] = catcher0 if delta > 0 else tag0
        elif xi < -60.0:
            out[index] = tag0 if delta < 0 else catcher0
        else:
            exponential = math.exp(float(xi))
            out[index] = (
                tag0 * catcher0 * (exponential - 1.0) / (tag0 * exponential - catcher0)
            )
    return out


def fraction_locked(
    t_s: np.ndarray, k_per_M_s: float, tag0: float, catcher0: float
) -> np.ndarray:
    """Adduct divided by the limiting starting concentration."""
    limit = min(tag0, catcher0)
    return product_M(t_s, k_per_M_s, tag0, catcher0) / limit


def _fit_second_order(
    t_s: np.ndarray,
    fraction: np.ndarray,
    tag0: float,
    catcher0: float,
) -> dict[str, Any]:
    def model(time_s: np.ndarray, k_per_M_s: float) -> np.ndarray:
        return fraction_locked(time_s, k_per_M_s, tag0, catcher0)

    guess = _second_order_guess(t_s, fraction, tag0, catcher0)
    try:
        coef, pcov = curve_fit(
            model,
            t_s,
            fraction,
            p0=(guess,),
            bounds=(_RATE_FLOOR, _RATE_CEILING),
            maxfev=20000,
        )
    except (RuntimeError, ValueError) as exc:
        return _lock_result(
            computable=False, missing=[f"lock fit failed: {exc}"], warnings=[]
        )
    k = float(coef[0])
    se = _one_se(pcov)
    if _rate_refused(k, se, _RATE_FLOOR, _RATE_CEILING):
        return _lock_result(
            computable=False,
            missing=["k_lock is not identifiable from these points"],
            warnings=[],
        )
    low = None if se is None else k - Z95 * se
    high = None if se is None else k + Z95 * se
    return _lock_result(
        computable=True,
        missing=[],
        warnings=[],
        equation="d[adduct]/dt = k_lock [Tag][Catcher]",
        rate_law="second_order",
        k_lock_per_M_s=k,
        k_lock_sigma_per_M_s=se,
        k_lock_95_lower_per_M_s=low,
        k_lock_95_upper_per_M_s=high,
        n_points=int(t_s.size),
        tag0_M=tag0,
        catcher0_M=catcher0,
    )


def _fit_pseudo_first_order(
    t_s: np.ndarray,
    fraction: np.ndarray,
    body: dict[str, Any],
    tag0: float,
    catcher0: float,
) -> dict[str, Any]:
    excess = body.get("excess_partner")
    if excess == "tag":
        excess_M = tag0
    elif excess == "catcher":
        excess_M = catcher0
    else:
        return _lock_result(
            computable=False,
            missing=["pseudo_first_order requires excess_partner 'tag' or 'catcher'"],
            warnings=[],
        )

    def model(time_s: np.ndarray, k_obs: float) -> np.ndarray:
        return 1.0 - np.exp(-k_obs * time_s)

    guess = _first_order_guess(t_s, fraction)
    try:
        coef, pcov = curve_fit(
            model,
            t_s,
            fraction,
            p0=(guess,),
            bounds=(_RATE_FLOOR, _RATE_CEILING),
            maxfev=20000,
        )
    except (RuntimeError, ValueError) as exc:
        return _lock_result(
            computable=False, missing=[f"lock fit failed: {exc}"], warnings=[]
        )
    k_obs = float(coef[0])
    se_obs = _one_se(pcov)
    if _rate_refused(k_obs, se_obs, _RATE_FLOOR, _RATE_CEILING):
        return _lock_result(
            computable=False,
            missing=["k_obs is not identifiable from these points"],
            warnings=[],
        )
    k_lock = k_obs / excess_M
    se_lock = None if se_obs is None else se_obs / excess_M
    low = None if se_lock is None else k_lock - Z95 * se_lock
    high = None if se_lock is None else k_lock + Z95 * se_lock
    return _lock_result(
        computable=True,
        missing=[],
        warnings=[
            "k_lock = k_obs / [partner in excess]. The caller chose which partner is in excess."
        ],
        equation="fraction = 1 - exp(-k_obs t); k_lock = k_obs / [excess]",
        rate_law="pseudo_first_order",
        excess_partner=excess,
        excess_M=excess_M,
        k_obs_per_s=k_obs,
        k_obs_sigma_per_s=se_obs,
        k_lock_per_M_s=k_lock,
        k_lock_sigma_per_M_s=se_lock,
        k_lock_95_lower_per_M_s=low,
        k_lock_95_upper_per_M_s=high,
        n_points=int(t_s.size),
        tag0_M=tag0,
        catcher0_M=catcher0,
    )


def _sds_warnings(sds: object) -> list[str]:
    if sds is True:
        return [
            "The SDS irreversibility flag was recorded as true. That licenses the irreversible rate law for this row."
        ]
    if sds is False:
        return [
            "The SDS irreversibility flag was recorded as false. The irreversible rate law is not supported by that gel."
        ]
    return ["The SDS irreversibility flag was not recorded."]


def _second_order_guess(
    t_s: np.ndarray, fraction: np.ndarray, tag0: float, catcher0: float
) -> float:
    order = np.argsort(t_s)
    t_sorted = t_s[order]
    f_sorted = fraction[order]
    for index in range(t_sorted.size - 1):
        dt = float(t_sorted[index + 1] - t_sorted[index])
        df = float(f_sorted[index + 1] - f_sorted[index])
        if dt > 0 and df > 0:
            # df/dt ≈ k * max(tag, catch) at early time, because
            # dP/dt(0) = k tag catch and f = P / min(tag, catch).
            slope = df / dt
            guess = slope / max(tag0, catcher0)
            return float(min(max(guess, _RATE_FLOOR * 10), _RATE_CEILING / 10))
    return 1e3


def _first_order_guess(t_s: np.ndarray, fraction: np.ndarray) -> float:
    order = np.argsort(t_s)
    t_sorted = t_s[order]
    f_sorted = np.clip(fraction[order], 0.0, 0.999)
    for index in range(t_sorted.size):
        if t_sorted[index] > 0 and f_sorted[index] > 0:
            remaining = max(1.0 - float(f_sorted[index]), 1e-6)
            guess = -math.log(remaining) / float(t_sorted[index])
            return float(min(max(guess, _RATE_FLOOR * 10), _RATE_CEILING / 10))
    return 1e-3


def _one_se(pcov: np.ndarray) -> float | None:
    if pcov is None or pcov.size < 1:
        return None
    variance = float(pcov[0, 0])
    if not math.isfinite(variance) or variance < 0:
        return None
    return math.sqrt(variance)


def _rate_refused(rate: float, se: float | None, floor: float, ceiling: float) -> bool:
    if not math.isfinite(rate) or se is None or not math.isfinite(se):
        return True
    # A 95% band that reaches 0 does not establish a positive rate.
    if Z95 * se >= abs(rate):
        return True
    return rate <= floor * 1.01 or rate >= ceiling * 0.99
