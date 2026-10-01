"""Assay-window calculations: line, decay half-life, and CV.

A luminescence number is admissible only inside a linear range the
caller stored from the NanoBiT linearity experiment. This module does
not invent that range.

The standard curve is the line ``RLU = a + b × amount``. Furimazine
decay, when the caller supplies a time series, is ``RLU = A exp(−k t)``
and the half-life is ``ln(2) / k``. Inter-day or inter-operator CV is
the sample standard deviation divided by the mean.

``calibrated`` stays false. A passing test of this arithmetic is not
scientific validation.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import curve_fit

from origami.assay.uncertainty import Z95, band, finite_number, optional_sigma

MODEL_NAME = "assay_window"
MODEL_VERSION = "1"

# Numerical bounds for the decay rate k in s^-1. They keep the optimizer
# off a zero or infinite rate. They are not a measured furimazine lifetime.
_K_FLOOR = 1e-12
_K_CEILING = 1e6


def _result(
    *,
    computable: bool,
    missing: list[str],
    warnings: list[str],
    model_name: str = MODEL_NAME,
    model_version: str = MODEL_VERSION,
    **payload: Any,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "computable": computable,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "model_name": model_name,
        "model_version": model_version,
        "missing": missing,
        "warnings": warnings
        + ["A passing test of this arithmetic is not scientific validation."],
    }
    body.update(payload)
    return body


def _series(name: str, values: object) -> np.ndarray:
    if not isinstance(values, (list, tuple)) or len(values) == 0:
        raise ValueError(f"{name} must be a non-empty list of numbers")
    return np.array(
        [finite_number(f"{name}[{i}]", v) for i, v in enumerate(values)], dtype=float
    )


def _linear(x: np.ndarray, intercept: float, slope: float) -> np.ndarray:
    return intercept + slope * x


def _decay(t_s: np.ndarray, amplitude: float, k_per_s: float) -> np.ndarray:
    return amplitude * np.exp(-k_per_s * t_s)


def fit_standard_curve(amount: object, rlu: object) -> dict[str, Any]:
    """Fit ``RLU = a + b × amount``. Refuse a slope that is not identifiable."""
    try:
        x = _series("amount", amount)
        y = _series("rlu", rlu)
    except ValueError as exc:
        return _result(computable=False, missing=[str(exc)], warnings=[])
    if x.size != y.size:
        return _result(
            computable=False,
            missing=["amount and rlu must have the same length"],
            warnings=[],
        )
    if x.size < 2 or float(np.ptp(x)) == 0.0:
        return _result(
            computable=False,
            missing=["at least two different amounts are required"],
            warnings=[],
        )
    try:
        coef, pcov = curve_fit(_linear, x, y, p0=(float(y[0]), 1.0))
    except (RuntimeError, ValueError) as exc:
        return _result(
            computable=False, missing=[f"line fit failed: {exc}"], warnings=[]
        )
    intercept = float(coef[0])
    slope = float(coef[1])
    se_intercept, se_slope = _parameter_se(pcov)
    if se_slope is None or not math.isfinite(slope) or se_slope > abs(slope):
        return _result(
            computable=False,
            missing=["slope is not identifiable from these points"],
            warnings=[],
        )
    return _result(
        computable=True,
        missing=[],
        warnings=[],
        equation="RLU = a + b × amount",
        intercept=intercept,
        intercept_sigma=se_intercept,
        slope=slope,
        slope_sigma=se_slope,
        slope_units="RLU per amount unit",
        intercept_95_lower=_lower(intercept, se_intercept),
        intercept_95_upper=_upper(intercept, se_intercept),
        slope_95_lower=_lower(slope, se_slope),
        slope_95_upper=_upper(slope, se_slope),
        n_points=int(x.size),
    )


def fit_half_life(time_min: object, rlu: object) -> dict[str, Any]:
    """Fit an exponential decay and return the half-life in minutes.

    Time in the request is minutes. The rate constant is in s^-1.
    ``t_half = ln(2) / k``. ``ln(2)`` is the change-of-base identity for
    a half-life, not a biological parameter.
    """
    try:
        t_min = _series("time_min", time_min)
        y = _series("rlu", rlu)
    except ValueError as exc:
        return _result(computable=False, missing=[str(exc)], warnings=[])
    if t_min.size != y.size:
        return _result(
            computable=False,
            missing=["time_min and rlu must have the same length"],
            warnings=[],
        )
    if t_min.size < 3 or np.any(t_min < 0) or np.any(y <= 0):
        return _result(
            computable=False,
            missing=["need at least three non-negative times and positive RLU"],
            warnings=[],
        )
    t_s = t_min * 60.0
    try:
        coef, pcov = curve_fit(
            _decay,
            t_s,
            y,
            p0=(float(y[0]), 1e-3),
            bounds=([0.0, _K_FLOOR], [np.inf, _K_CEILING]),
        )
    except (RuntimeError, ValueError) as exc:
        return _result(
            computable=False, missing=[f"decay fit failed: {exc}"], warnings=[]
        )
    amplitude = float(coef[0])
    k_per_s = float(coef[1])
    _se_a, se_k = _parameter_se(pcov)
    on_bound = k_per_s <= _K_FLOOR * 1.01 or k_per_s >= _K_CEILING * 0.99
    if se_k is None or not math.isfinite(k_per_s) or se_k > abs(k_per_s) or on_bound:
        return _result(
            computable=False,
            missing=["decay rate is not identifiable from these points"],
            warnings=[],
        )
    half_s = math.log(2.0) / k_per_s
    # σ(t_half) ≈ |dt/dk| σ_k = ln(2) / k^2 * σ_k
    half_sigma_s = math.log(2.0) / k_per_s**2 * se_k
    half_min = half_s / 60.0
    half_sigma_min = half_sigma_s / 60.0
    low, high = band(half_min, half_sigma_min)
    return _result(
        computable=True,
        missing=[],
        warnings=[
            "Minutes were converted to seconds by multiplying by 60, then the half-life was converted back."
        ],
        equation="RLU = A exp(-k t), t_half = ln(2) / k",
        k_per_s=k_per_s,
        k_sigma_per_s=se_k,
        half_life_min=half_min,
        half_life_sigma_min=half_sigma_min,
        half_life_95_lower_min=low,
        half_life_95_upper_min=high,
        amplitude_rlu=amplitude,
        n_points=int(t_min.size),
    )


def coefficient_of_variation(values: object) -> dict[str, Any]:
    """Sample CV = standard deviation / mean. Needs at least two values."""
    try:
        sample = _series("values", values)
    except ValueError as exc:
        return _result(computable=False, missing=[str(exc)], warnings=[])
    if sample.size < 2:
        return _result(
            computable=False,
            missing=["at least two replicates are required"],
            warnings=[],
        )
    mean = float(np.mean(sample))
    # Sample standard deviation (ddof=1). A statistical definition, not a
    # biological constant.
    sigma = float(np.std(sample, ddof=1))
    if mean == 0.0:
        return _result(
            computable=False,
            missing=["mean is zero, so CV is undefined"],
            warnings=[],
            mean=mean,
            sample_sigma=sigma,
            n_points=int(sample.size),
        )
    cv = sigma / abs(mean)
    return _result(
        computable=True,
        missing=[],
        warnings=[],
        equation="CV = sample standard deviation / |mean|",
        mean=mean,
        sample_sigma=sigma,
        cv=cv,
        n_points=int(sample.size),
    )


def admissibility(rlu: object, rlu_low: object, rlu_high: object) -> dict[str, Any]:
    """Say whether one RLU sits inside the caller-supplied linear range."""
    missing: list[str] = []
    try:
        value = finite_number("rlu", rlu)
    except ValueError as exc:
        missing.append(str(exc))
        value = None
    try:
        low = finite_number("rlu_low", rlu_low) if rlu_low is not None else None
    except ValueError as exc:
        missing.append(str(exc))
        low = None
    try:
        high = finite_number("rlu_high", rlu_high) if rlu_high is not None else None
    except ValueError as exc:
        missing.append(str(exc))
        high = None
    if low is None or high is None or value is None:
        return _result(
            computable=False,
            missing=missing or ["linear range was not stored"],
            warnings=[],
            admissible=None,
        )
    if high < low:
        return _result(
            computable=False,
            missing=["rlu_high must be >= rlu_low"],
            warnings=[],
            admissible=None,
        )
    inside = low <= value <= high
    return _result(
        computable=True,
        missing=[],
        warnings=[] if inside else ["This RLU is outside the stored linear range."],
        admissible=inside,
        rlu=value,
        rlu_low=low,
        rlu_high=high,
    )


def _parameter_se(pcov: np.ndarray) -> tuple[float | None, float | None]:
    if pcov is None or pcov.shape[0] < 2:
        return None, None
    ses: list[float | None] = []
    for index in (0, 1):
        variance = float(pcov[index, index])
        if not math.isfinite(variance) or variance < 0:
            ses.append(None)
        else:
            ses.append(math.sqrt(variance))
    return ses[0], ses[1]


def _lower(value: float, sigma: float | None) -> float | None:
    if sigma is None:
        return None
    return value - Z95 * sigma


def _upper(value: float, sigma: float | None) -> float | None:
    if sigma is None:
        return None
    return value + Z95 * sigma


def parse_sigma_list(name: str, values: object, n: int) -> list[float | None] | None:
    """Parse an optional sigma list. None means the whole list was omitted."""
    if values is None:
        return None
    if not isinstance(values, (list, tuple)) or len(values) != n:
        raise ValueError(f"{name} must have length {n} or be omitted")
    return [optional_sigma(f"{name}[{i}]", v) for i, v in enumerate(values)]
