"""Per-series length curves for melting temperature and unfolding ΔG.

The literature rows of one series are the data. The number reported at
a repeat count is this model evaluated at that count. It is not a copied
table cell, and it is not an average of two papers.

With at least four points the curve is

    y(n) = y_inf - (y_inf - y_1) * exp(-(n - 1) / lambda)

with y_inf, y_1, and lambda positive. That is a rod whose ends matter
less as it gets longer: the value moves from y_1 toward y_inf. With two
or three points that three-parameter form is not fit. A straight line
y(n) = a + b*n is fit instead. With fewer than two points, no curve is
invented.

Parameters and the 95% band come from ``scipy.optimize.curve_fit``.
The band is value ± 1.96 σ from the linearized covariance. It is a
linear approximation, not a wet-lab confidence interval. A parameter
whose covariance variance is not finite is non-identifiable.

ΔHcal and ΔCp are not parameters of this fit. They are not read from
the literature file, because that file does not contain them, and they
are not filled in. Series are not pooled. ``calibrated`` stays false.
A passing test of this arithmetic is not scientific validation.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from scipy.optimize import OptimizeWarning, curve_fit

from origami.stability.series import (
    companion_delta_g_rows,
    load_named_series,
)
from origami.stability.table import ThermalObservation

# Software identity of this length curve. Not a biological constant.
MODEL_NAME = "ctpr_length_curve"
MODEL_VERSION = "1"

# Standard-normal 97.5 percentile. The 95% band is value ± this factor
# times the linearized standard deviation. It is not a biological
# parameter and it is not a wet-lab confidence interval.
_Z95 = 1.96

# Numerical floor passed to curve_fit so y_inf, y_1, and lambda stay
# positive. It is not a measured concentration, temperature, or length.
# Predictions for the checked-in Phillips ΔG column are insensitive to
# moving this floor between 1e-4 and 1e-16; the optimizer sits on it
# when the printed column is still rising.
_POSITIVITY_FLOOR = 1e-8

SATURATING_EQUATION = "y(n) = y_inf - (y_inf - y_1) * exp(-(n-1)/lambda)"
LINE_EQUATION = "y(n) = a + b*n"

_SATURATING_NAMES = ("y_inf", "y_1", "lambda")
_LINE_NAMES = ("a", "b")

_TWO_POINT_WARNING = (
    "Two points determine a line. A length far from those points is weakly constrained."
)
_SHORT_LINE_WARNING = (
    "Fewer than four points, so the three-parameter saturating form was not fit. "
    "A straight line was fit. A length far from these points is weakly constrained."
)
_NO_CURVE_WARNING = "Fewer than two points. No curve was fit."
_DUPLICATE_WARNING = (
    "Duplicate repeat counts in one series were not averaged. No curve was fit."
)
_NO_DELTA_G_WARNING = (
    "This series has no delta_G rows. None were borrowed from another series."
)
_MIXED_UNITS_WARNING = (
    "Rows in this series do not share one units string. They were not converted and were not fit."
)
_DIVERGED_WARNING = "curve_fit did not converge on these points. No curve was invented."
_BOUND_WARNING = (
    "A fitted parameter sits on the positivity bound. "
    "The saturating parameters are weakly separated for these points. "
    "The calculated value is still the model at n. "
    "The 95% band is a linear approximation of the fit covariance, "
    "not a wet-lab confidence interval."
)

FitForm = Literal["saturating", "line", "not_fit"]


@dataclass(frozen=True)
class FittedParameter:
    """One coefficient from curve_fit.

    ``standard_error`` is the square root of the covariance diagonal
    when that variance is finite and non-negative. The parameter is
    non-identifiable, and ``standard_error`` is None, when the variance
    is not finite. A value sitting on the positivity bound is still
    reported; the fit warning says that standard error is not an
    interior estimate.
    """

    name: str
    value: float
    units: str
    standard_error: float | None
    identifiable: bool


@dataclass(frozen=True)
class LengthPrediction:
    """Model value at one repeat count.

    ``sigma`` is the linearized standard deviation. The 95% band is
    value ± 1.96 σ when that sigma is finite. ``band_label`` is
    ``linear approximation`` and is not a wet-lab confidence interval.
    ``confidence_tier`` is ``hypothesis_only`` because the functional
    form is an assumption and this chassis has no wet-lab calibration.
    ``past_longest_cited_length`` is a separate fact about n. It does
    not replace the value.
    """

    n_repeats: int
    value: float | None
    units: str
    sigma: float | None
    band_95_low: float | None
    band_95_high: float | None
    band_label: str | None
    confidence_tier: str
    calibrated: bool
    human_review_required: bool
    model_name: str
    model_version: str
    past_longest_cited_length: bool
    longest_cited_n: int | None
    length_note: str | None
    form: FitForm


@dataclass(frozen=True)
class LengthFit:
    """A curve fit to one observable of one series."""

    form: FitForm
    equation: str
    parameters: tuple[FittedParameter, ...]
    n_points: int
    n_repeats: tuple[int, ...]
    values: tuple[float, ...]
    units: str
    warnings: tuple[str, ...]
    longest_cited_n: int | None
    _theta: tuple[float, ...]
    _pcov: tuple[tuple[float, ...], ...] | None

    def predict(self, n_repeats: int) -> LengthPrediction:
        """Evaluate the fitted model at ``n_repeats``.

        The returned value is the equation at the fitted coefficients.
        It is not looked up from a table. Outside the cited lengths the
        same equation is evaluated, and ``length_note`` says when n is
        past the longest cited length.
        """
        if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
            raise TypeError("n_repeats must be an integer")
        if n_repeats < 1:
            raise ValueError("n_repeats must be an integer >= 1")
        past = (
            self.longest_cited_n is not None and n_repeats > self.longest_cited_n
        )
        note = None
        if past and self.longest_cited_n is not None:
            note = (
                f"{n_repeats} is past the longest cited length in this series "
                f"({self.longest_cited_n})."
            )
        if self.form == "not_fit" or not self._theta:
            return _empty_prediction(
                n_repeats,
                self.units,
                self.form,
                past,
                self.longest_cited_n,
                note,
            )
        value = _evaluate(self.form, float(n_repeats), self._theta)
        sigma = _prediction_sigma(self.form, float(n_repeats), self._theta, self._pcov)
        low, high = _band(value, sigma)
        return LengthPrediction(
            n_repeats=n_repeats,
            value=value,
            units=self.units,
            sigma=sigma,
            band_95_low=low,
            band_95_high=high,
            band_label=None if low is None else "linear approximation",
            confidence_tier="hypothesis_only",
            calibrated=False,
            human_review_required=True,
            model_name=MODEL_NAME,
            model_version=MODEL_VERSION,
            past_longest_cited_length=past,
            longest_cited_n=self.longest_cited_n,
            length_note=note,
            form=self.form,
        )


def fit_length_curve(
    n_repeats: Sequence[int],
    values: Sequence[float],
    *,
    units: str,
) -> LengthFit:
    """Fit one observable against repeat count.

    Four or more points use the saturating form. Two or three points
    use a line. Fewer than two points, a duplicated repeat count, a
    non-finite value, or a failed optimizer returns ``not_fit``.
    Duplicate counts are not averaged.
    """
    if not isinstance(units, str) or units.strip() == "":
        raise ValueError("units must be a non-empty string")
    if len(n_repeats) != len(values):
        raise ValueError("n_repeats and values must have the same length")
    cleaned_n: list[int] = []
    cleaned_y: list[float] = []
    for n_value, y_value in zip(n_repeats, values, strict=True):
        if isinstance(n_value, bool) or not isinstance(n_value, int):
            raise TypeError("each repeat count must be an integer")
        if n_value < 1:
            raise ValueError("each repeat count must be an integer >= 1")
        if isinstance(y_value, bool) or not isinstance(y_value, (int, float)):
            raise TypeError("each value must be a number")
        y_float = float(y_value)
        if not math.isfinite(y_float):
            return _not_fit(
                units,
                ("A non-finite value was not fit.",),
                tuple(int(n) for n in n_repeats),
                tuple(float(y) for y in values if isinstance(y, (int, float))),
            )
        cleaned_n.append(n_value)
        cleaned_y.append(y_float)

    order = sorted(range(len(cleaned_n)), key=lambda index: cleaned_n[index])
    ns = tuple(cleaned_n[index] for index in order)
    ys = tuple(cleaned_y[index] for index in order)
    if len(ns) != len(set(ns)):
        return _not_fit(units, (_DUPLICATE_WARNING,), ns, ys)
    if len(ns) < 2:
        return _not_fit(units, (_NO_CURVE_WARNING,), ns, ys)
    if len(ns) < 4:
        return _fit_line(ns, ys, units)
    return _fit_saturating(ns, ys, units)


def fit_named_tm(series_id: str, path: Path | None = None) -> LengthFit:
    """Fit Tm(n) using only the Tm rows of ``series_id``."""
    rows = load_named_series(series_id, path)
    return _fit_rows(rows, units_if_empty="C")


def fit_named_delta_g(series_id: str, path: Path | None = None) -> LengthFit:
    """Fit unfolding ΔG(n) using only that series' ΔG rows.

    A series with no ΔG rows stays ``not_fit``. Rows are not borrowed
    from another paper.
    """
    rows = companion_delta_g_rows(series_id, path)
    if not rows:
        return _not_fit("", (_NO_DELTA_G_WARNING,), (), ())
    return _fit_rows(rows, units_if_empty="")


def fit_public_dict(fit: LengthFit) -> dict[str, object]:
    """JSON-ready description of one fit. Coefficients are the fit, not literature constants."""
    return {
        "form": fit.form,
        "equation": fit.equation,
        "n_points": fit.n_points,
        "n_repeats": list(fit.n_repeats),
        "values": [_plain_float(value) for value in fit.values],
        "units": fit.units,
        "longest_cited_n": fit.longest_cited_n,
        "warnings": list(fit.warnings),
        "parameters": [
            {
                "name": parameter.name,
                "value": _plain_float(parameter.value),
                "units": parameter.units,
                "standard_error": _plain_float(parameter.standard_error),
                "identifiable": parameter.identifiable,
            }
            for parameter in fit.parameters
        ],
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "confidence_tier": "hypothesis_only",
        "calibrated": False,
        "human_review_required": True,
    }


def saturating_value(n_repeats: float, y_inf: float, y_1: float, lam: float) -> float:
    """Saturating length curve. ``lam`` must be positive."""
    if lam <= 0:
        raise ValueError("lambda must be positive")
    return float(
        y_inf - (y_inf - y_1) * math.exp(-(float(n_repeats) - 1.0) / lam)
    )


def line_value(n_repeats: float, a: float, b: float) -> float:
    """Straight line in repeat count."""
    return float(a + b * float(n_repeats))


def _fit_rows(rows: Sequence[ThermalObservation], *, units_if_empty: str) -> LengthFit:
    if not rows:
        return _not_fit(units_if_empty, (_NO_CURVE_WARNING,), (), ())
    units = {row.units for row in rows}
    if len(units) != 1:
        ns = tuple(int(row.n_repeats) for row in rows)
        ys = tuple(float(row.value) for row in rows)
        return _not_fit("", (_MIXED_UNITS_WARNING,), ns, ys)
    unit = next(iter(units))
    return fit_length_curve(
        [int(row.n_repeats) for row in rows],
        [float(row.value) for row in rows],
        units=unit,
    )


def _fit_saturating(
    ns: tuple[int, ...],
    ys: tuple[float, ...],
    units: str,
) -> LengthFit:
    n_array = np.asarray(ns, dtype=float)
    y_array = np.asarray(ys, dtype=float)
    try:
        theta, pcov = _curve_fit_saturating(n_array, y_array)
    except RuntimeError:
        return _not_fit(units, (_DIVERGED_WARNING,), ns, ys)
    parameters = _parameters_from_covariance(
        _SATURATING_NAMES,
        theta,
        pcov,
        [_units_for(name, units) for name in _SATURATING_NAMES],
    )
    warnings_out = [_weak_separation_warning(parameters, theta)]
    warnings_out = [item for item in warnings_out if item]
    return LengthFit(
        form="saturating",
        equation=SATURATING_EQUATION,
        parameters=tuple(parameters),
        n_points=len(ns),
        n_repeats=ns,
        values=ys,
        units=units,
        warnings=tuple(warnings_out),
        longest_cited_n=max(ns),
        _theta=tuple(float(value) for value in theta),
        _pcov=_pcov_tuple(pcov),
    )


def _fit_line(ns: tuple[int, ...], ys: tuple[float, ...], units: str) -> LengthFit:
    n_array = np.asarray(ns, dtype=float)
    y_array = np.asarray(ys, dtype=float)
    try:
        theta, pcov = _curve_fit_line(n_array, y_array)
    except RuntimeError:
        return _not_fit(units, (_DIVERGED_WARNING,), ns, ys)
    parameters = _parameters_from_covariance(
        _LINE_NAMES,
        theta,
        pcov,
        [units, f"{units} per repeat"],
    )
    if len(ns) == 2:
        line_warning = _TWO_POINT_WARNING
    else:
        line_warning = _SHORT_LINE_WARNING
    return LengthFit(
        form="line",
        equation=LINE_EQUATION,
        parameters=tuple(parameters),
        n_points=len(ns),
        n_repeats=ns,
        values=ys,
        units=units,
        warnings=(line_warning,),
        longest_cited_n=max(ns),
        _theta=tuple(float(value) for value in theta),
        _pcov=_pcov_tuple(pcov),
    )


def _curve_fit_saturating(
    n_array: np.ndarray,
    y_array: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    y_first = float(y_array[0])
    y_last = float(y_array[-1])
    n_first = float(n_array[0])
    n_last = float(n_array[-1])
    span = y_last - y_first
    n_span = n_last - n_first
    if n_span <= 0:
        raise RuntimeError("repeat counts are not increasing")
    floor = _POSITIVITY_FLOOR
    y1_a = y_first if y_first > floor else floor * 10.0
    yinf_a = y_last + abs(span)
    if yinf_a <= floor:
        yinf_a = abs(y_last) + abs(span) + 1.0
    lam_a = n_span
    slope = span / n_span
    lam_b = n_span * 10.0
    y1_b = y_first - slope * (n_first - 1.0)
    if y1_b <= floor:
        y1_b = floor * 10.0
    yinf_b = y1_b + abs(slope) * lam_b
    if yinf_b <= floor:
        yinf_b = yinf_a
    starts = ((yinf_a, y1_a, lam_a), (yinf_b, y1_b, lam_b))
    best: tuple[tuple[float, float], np.ndarray, np.ndarray] | None = None
    last_error: Exception | None = None
    for start in starts:
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", OptimizeWarning)
                theta, pcov = curve_fit(
                    _saturating_array,
                    n_array,
                    y_array,
                    p0=np.asarray(start, dtype=float),
                    bounds=(floor, np.inf),
                    maxfev=50000,
                )
        except (RuntimeError, ValueError) as exc:
            last_error = exc
            continue
        residual = y_array - _saturating_array(n_array, *theta)
        rss = float(np.dot(residual, residual))
        magnitude = float(np.dot(theta, theta))
        score = (rss, magnitude)
        if best is None or score < best[0]:
            best = (score, np.asarray(theta, dtype=float), np.asarray(pcov, dtype=float))
    if best is None:
        raise RuntimeError(f"curve_fit did not converge ({last_error})")
    return best[1], best[2]


def _curve_fit_line(
    n_array: np.ndarray,
    y_array: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    n_span = float(n_array[-1] - n_array[0])
    if n_span == 0:
        raise RuntimeError("repeat counts are not increasing")
    slope = float(y_array[-1] - y_array[0]) / n_span
    intercept = float(y_array[0]) - slope * float(n_array[0])
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", OptimizeWarning)
            theta, pcov = curve_fit(
                _line_array,
                n_array,
                y_array,
                p0=np.asarray((intercept, slope), dtype=float),
                maxfev=10000,
            )
    except (RuntimeError, ValueError) as exc:
        raise RuntimeError(f"curve_fit did not converge ({exc})") from exc
    return np.asarray(theta, dtype=float), np.asarray(pcov, dtype=float)


def _saturating_array(
    n_array: np.ndarray,
    y_inf: float,
    y_1: float,
    lam: float,
) -> np.ndarray:
    n_values = np.asarray(n_array, dtype=float)
    return y_inf - (y_inf - y_1) * np.exp(-(n_values - 1.0) / lam)


def _line_array(n_array: np.ndarray, a: float, b: float) -> np.ndarray:
    return a + b * np.asarray(n_array, dtype=float)


def _parameters_from_covariance(
    names: tuple[str, ...],
    theta: np.ndarray,
    pcov: np.ndarray,
    units: list[str],
) -> list[FittedParameter]:
    parameters: list[FittedParameter] = []
    for index, name in enumerate(names):
        value = float(theta[index])
        variance = _variance_at(pcov, index)
        if variance is None:
            parameters.append(
                FittedParameter(
                    name=name,
                    value=value,
                    units=units[index],
                    standard_error=None,
                    identifiable=False,
                )
            )
            continue
        parameters.append(
            FittedParameter(
                name=name,
                value=value,
                units=units[index],
                standard_error=math.sqrt(variance),
                identifiable=True,
            )
        )
    return parameters


def _variance_at(pcov: np.ndarray, index: int) -> float | None:
    if pcov.ndim != 2 or pcov.shape[0] <= index or pcov.shape[1] <= index:
        return None
    variance = float(pcov[index, index])
    if not math.isfinite(variance):
        return None
    if variance < 0:
        if variance > -1e-12:
            return 0.0
        return None
    return variance


def _weak_separation_warning(
    parameters: Sequence[FittedParameter],
    theta: np.ndarray,
) -> str | None:
    """Warn when the positive saturating fit is not an interior estimate.

    The warning does not change the equation. A series with at least
    four points stays on the saturating form.
    """
    for value in theta:
        if float(value) <= _POSITIVITY_FLOOR * (1.0 + 1e-6):
            return _BOUND_WARNING
    for parameter in parameters:
        if (
            parameter.standard_error is not None
            and parameter.standard_error > abs(parameter.value)
        ):
            return _BOUND_WARNING
    return None


def _prediction_sigma(
    form: FitForm,
    n_repeats: float,
    theta: tuple[float, ...],
    pcov: tuple[tuple[float, ...], ...] | None,
) -> float | None:
    if pcov is None:
        return None
    matrix = np.asarray(pcov, dtype=float)
    if matrix.shape != (len(theta), len(theta)):
        return None
    if not np.isfinite(matrix).all():
        return None
    gradient = _gradient(form, n_repeats, theta)
    variance = float(gradient @ matrix @ gradient)
    if not math.isfinite(variance):
        return None
    if variance < 0:
        if variance > -1e-10:
            variance = 0.0
        else:
            return None
    return math.sqrt(variance)


def _gradient(form: FitForm, n_repeats: float, theta: tuple[float, ...]) -> np.ndarray:
    if form == "line":
        return np.asarray((1.0, n_repeats), dtype=float)
    y_inf, y_1, lam = theta
    decay = math.exp(-(n_repeats - 1.0) / lam)
    d_inf = 1.0 - decay
    d_1 = decay
    d_lam = (y_inf - y_1) * decay * (n_repeats - 1.0) / (lam * lam)
    return np.asarray((d_inf, d_1, d_lam), dtype=float)


def _evaluate(form: FitForm, n_repeats: float, theta: tuple[float, ...]) -> float:
    if form == "line":
        return line_value(n_repeats, theta[0], theta[1])
    return saturating_value(n_repeats, theta[0], theta[1], theta[2])


def _band(value: float | None, sigma: float | None) -> tuple[float | None, float | None]:
    if value is None or sigma is None:
        return None, None
    if not math.isfinite(value) or not math.isfinite(sigma):
        return None, None
    low = value - _Z95 * sigma
    high = value + _Z95 * sigma
    if not math.isfinite(low) or not math.isfinite(high):
        return None, None
    return low, high


def _empty_prediction(
    n_repeats: int,
    units: str,
    form: FitForm,
    past: bool,
    longest_cited_n: int | None,
    note: str | None,
) -> LengthPrediction:
    return LengthPrediction(
        n_repeats=n_repeats,
        value=None,
        units=units,
        sigma=None,
        band_95_low=None,
        band_95_high=None,
        band_label=None,
        confidence_tier="hypothesis_only",
        calibrated=False,
        human_review_required=True,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        past_longest_cited_length=past,
        longest_cited_n=longest_cited_n,
        length_note=note,
        form=form,
    )


def _not_fit(
    units: str,
    warnings_out: tuple[str, ...],
    ns: tuple[int, ...],
    ys: tuple[float, ...],
) -> LengthFit:
    longest = max(ns) if ns else None
    return LengthFit(
        form="not_fit",
        equation="",
        parameters=(),
        n_points=len(ns),
        n_repeats=ns,
        values=ys,
        units=units,
        warnings=warnings_out,
        longest_cited_n=longest,
        _theta=(),
        _pcov=None,
    )


def _pcov_tuple(pcov: np.ndarray) -> tuple[tuple[float, ...], ...]:
    rows: list[tuple[float, ...]] = []
    for row in np.asarray(pcov, dtype=float):
        rows.append(tuple(float(value) for value in row))
    return tuple(rows)


def _units_for(name: str, units: str) -> str:
    if name == "lambda":
        return "repeats"
    return units


def _plain_float(value: float | None) -> float | None:
    if value is None:
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number
