"""Two-state Gibbs–Helmholtz arithmetic for caller-supplied inputs.

This module evaluates the standard two-state Gibbs–Helmholtz equation
that is zero at the melting temperature. It is the relation Phillips
et al. 2012 (DOI 10.1002/pro.2018) used to obtain unfolding ΔG at
10°C from calorimetric ΔH (ΔHcal), Tm, and ΔCp. It is not a new fit,
not an interpolation of Tm across repeat counts, and not a DSC trace.

Let T and Tm be kelvin, ΔH_m = ΔH(Tm), and ΔCp be constant:

    ΔH(T) = ΔH_m + ΔCp * (T - Tm)
    ΔS(Tm) = ΔH_m / Tm
    ΔS(T) = ΔS(Tm) + ΔCp * ln(T / Tm)
    ΔG(T) = ΔH(T) - T * ΔS(T)

ΔS(Tm) = ΔH_m / Tm only because ΔG(Tm) = 0 for this two-state model.
The same ΔG is:

    ΔG(T) = ΔH_m * (1 - T/Tm) + ΔCp * ((T - Tm) - T * ln(T/Tm))

Temperatures are accepted in °C and converted explicitly:

    T_K = t_C + 273.15

Outputs are reported in the unit of the Phillips Table I ΔG column:
ΔG and ΔH in kcal mol-1, ΔS and ΔCp in kcal mol-1 K-1. A caller who
sends kJ is converted with 1 kcal = 4.184 kJ, and that conversion is
recorded. ``calibrated`` is always false: this is arithmetic on cited
or caller-supplied inputs, not a wet-lab validation.

ΔH, ΔS, and ΔCp are never read from memory and are never back-calculated
from Tm or from a printed ΔG. ``thermo_prefill`` copies ΔH and ΔCp only
when the literature JSON actually has those fields.

ΔG at the melting temperature does not need those inputs. For a two-state
transition, ΔG(Tm) = 0 by definition. That identity is the only ΔG this
module computes from Tm alone. A curve of ΔH(T), ΔS(T), and ΔG(T) away
from Tm still requires caller-supplied ΔHcal and ΔCp. Missing calorimetry
leaves the curve empty. It does not hide ΔG(Tm), and it does not draw a
line of zeros.
"""

from __future__ import annotations

import json
import math
from typing import Any

from origami.stability.series import delta_g_at_n, literature_table_path, load_named_series
from origami.stability.table import ThermalObservation

# Unit definition, not a biological parameter.
# Celsius and kelvin differ by this offset (the kelvin scale).
_CELSIUS_TO_KELVIN = 273.15

# Unit definition, not a biological parameter.
# Exact factor required by this calculator: 1 kcal = 4.184 kJ.
_KJ_PER_KCAL = 4.184

# Two-sided normal 95% factor requested for this calculator.
# Not a biological parameter and not a fitted uncertainty.
_COVERAGE_95 = 1.96

_ENERGY_UNITS = "kcal mol-1"
_ENTROPY_UNITS = "kcal mol-1 K-1"

# Extra JSON keys that would count as a cited enthalpy or ΔCp.
# The checked-in literature table does not use these names.
_DELTA_H_KEYS = (
    "delta_h",
    "delta_H",
    "delta_hcal",
    "delta_Hcal",
    "DeltaHcal",
    "delta_H_cal",
    "dHcal",
)
_DELTA_CP_KEYS = (
    "delta_cp",
    "delta_Cp",
    "DeltaCp",
    "delta_CP",
    "dCp",
)

EQUATION_TEXT = (
    "For a two-state unfold, temperatures are kelvin "
    "(T_K = t_C + 273.15). "
    "ΔG(Tm) = 0 by definition. That identity does not need ΔH or ΔS. "
    "It holds only for a two-state melt. "
    "A temperature curve away from Tm still needs caller-supplied "
    "ΔHcal and ΔCp. ΔHcal is ΔH at Tm. ΔCp is assumed constant. "
    "ΔH(T) = ΔHcal + ΔCp * (T - Tm). "
    "ΔS(T) = ΔHcal / Tm + ΔCp * ln(T / Tm). "
    "ΔG(T) = ΔH(T) - T * ΔS(T). "
    "The same ΔG is ΔHcal * (1 - T/Tm) + ΔCp * ((T - Tm) - T * ln(T/Tm))."
)

# Temperature named for the Phillips et al. 2012 Table I unfolding ΔG
# column. This is the temperature that table states, not a value derived
# from Tm and not a fitted parameter.
# Source: data/stability/README.md, "Unfolding ΔG at 10°C", Phillips et al.
# 2012, DOI 10.1002/pro.2018, Table I. The same temperature is named in
# origami.stability.series.delta_g_at_n.
_PHILLIPS_TABLE_I_DELTA_G_T_C = 10.0

_TWO_STATE_IDENTITY = (
    "For a two-state transition, ΔG(Tm) = 0 by definition. "
    "Temperatures are kelvin: T_K = t_C + 273.15. "
    "This identity holds only for a two-state melt. "
    "It is not a wet-lab fit. calibrated is false. "
    "No uncertainty band is attached to this zero. "
    "ΔH and ΔS are not required and were not calculated from Tm."
)

# Display window for the temperature curve. Not a biological parameter,
# not a DSC setpoint, and not a literature range.
_DEFAULT_CURVE_T_MIN_C = 0.0
_DEFAULT_CURVE_T_MAX_C = 100.0
_DEFAULT_CURVE_POINTS = 101
_MAX_CURVE_POINTS = 401

_CURVE_LABEL = (
    "Calculation from the supplied ΔHcal, ΔCp, and Tm. "
    "calibrated is false. This is not a measurement of the "
    "Hong Kong team fusion."
)


class ThermoInputError(ValueError):
    """A temperature, energy, or heat-capacity input cannot be used."""


def _as_finite(name: str, value: object) -> float:
    """Require a real finite number. Booleans and strings are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ThermoInputError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ThermoInputError(f"{name} must be a finite number")
    return number


def _as_optional_sigma(name: str, value: object) -> float | None:
    """None means the caller did not supply a sigma. Do not invent one."""
    if value is None:
        return None
    number = _as_finite(name, value)
    if number < 0:
        raise ThermoInputError(f"{name} must be >= 0")
    return number


def _celsius_to_kelvin(name: str, t_c: float) -> float:
    t_k = t_c + _CELSIUS_TO_KELVIN
    if t_k <= 0:
        raise ThermoInputError(f"{name} must be > 0 K (got {t_k} K from {t_c} C)")
    return t_k


def _to_kcal(value: float, units: str) -> tuple[float, bool]:
    if units == "kcal":
        return value, False
    if units == "kJ":
        return value / _KJ_PER_KCAL, True
    raise ThermoInputError("units must be 'kcal' or 'kJ'")


def _quadrature(partials: list[tuple[float, float]]) -> float:
    """Independent first-order uncertainty: sqrt(sum (∂f/∂x * σ_x)^2)."""
    variance = 0.0
    for partial, sigma in partials:
        variance += (partial * sigma) ** 2
    return math.sqrt(variance)


def _band(value: float, sigma: float) -> tuple[float, float]:
    half = _COVERAGE_95 * sigma
    return value - half, value + half


def gibbs_helmholtz_report(
    t_c: object,
    tm_c: object,
    delta_h: object,
    delta_cp: object,
    *,
    units: object = "kcal",
    delta_h_sigma: object = None,
    delta_cp_sigma: object = None,
    tm_sigma_c: object = None,
) -> dict[str, Any]:
    """Evaluate ΔG, ΔH, and ΔS at one temperature.

    Parameters
    ----------
    t_c, tm_c:
        Evaluation temperature and melting temperature, in °C.
        Converted with T_K = t_C + 273.15 before the equation.
    delta_h:
        ΔH at Tm (ΔH_m), in kcal mol-1 or kJ mol-1 according to
        ``units``. This is the calorimetric enthalpy at Tm when the
        caller is reproducing the Phillips column.
    delta_cp:
        Constant ΔCp, in kcal mol-1 K-1 or kJ mol-1 K-1. Zero is
        allowed. A negative value is computed and warned about.
    units:
        ``kcal`` (default) or ``kJ``. kJ inputs are converted with
        1 kcal = 4.184 kJ. Outputs stay in kcal.
    delta_h_sigma, delta_cp_sigma, tm_sigma_c:
        Optional 1-sigma uncertainties in the same unit as the matching
        input (Tm sigma in °C). If any of the three is omitted, every
        output sigma is null. Missing sigmas are not treated as zero.

    Returns
    -------
    dict
        ΔG, ΔH(T), and ΔS(T), both temperatures in °C and K, units,
        assumptions, warnings, and uncertainty fields. ``calibrated``
        is false.

    Raises
    ------
    ThermoInputError
        Non-finite inputs, T <= 0 K, Tm <= 0 K, a non-finite ΔCp,
        a negative sigma, or an unknown unit.
    """
    t_c_value = _as_finite("t_c", t_c)
    tm_c_value = _as_finite("tm_c", tm_c)
    delta_h_value = _as_finite("delta_h", delta_h)
    delta_cp_value = _as_finite("delta_cp", delta_cp)
    if not isinstance(units, str):
        raise ThermoInputError("units must be 'kcal' or 'kJ'")
    sigma_h_in = _as_optional_sigma("delta_h_sigma", delta_h_sigma)
    sigma_c_in = _as_optional_sigma("delta_cp_sigma", delta_cp_sigma)
    sigma_tm_c = _as_optional_sigma("tm_sigma_c", tm_sigma_c)

    t_k = _celsius_to_kelvin("T", t_c_value)
    tm_k = _celsius_to_kelvin("Tm", tm_c_value)

    delta_h_kcal, converted_h = _to_kcal(delta_h_value, units)
    delta_cp_kcal, converted_c = _to_kcal(delta_cp_value, units)
    if converted_h != converted_c:
        raise ThermoInputError("units must be 'kcal' or 'kJ'")
    converted = converted_h

    sigma_h = None if sigma_h_in is None else _to_kcal(sigma_h_in, units)[0]
    sigma_c = None if sigma_c_in is None else _to_kcal(sigma_c_in, units)[0]
    # Tm sigma is a temperature in °C. The kelvin offset does not change it.
    sigma_tm = sigma_tm_c

    # ΔH(T) = ΔH_m + ΔCp * (T - Tm)
    delta_h_t = delta_h_kcal + delta_cp_kcal * (t_k - tm_k)
    # ΔS(Tm) = ΔH_m / Tm because ΔG(Tm) = 0 for this two-state model.
    delta_s_tm = delta_h_kcal / tm_k
    log_ratio = math.log(t_k / tm_k)
    delta_s_t = delta_s_tm + delta_cp_kcal * log_ratio
    delta_g_from_hs = delta_h_t - t_k * delta_s_t
    delta_g_compact = delta_h_kcal * (1.0 - t_k / tm_k) + delta_cp_kcal * (
        (t_k - tm_k) - t_k * log_ratio
    )
    if not math.isfinite(delta_g_from_hs) or not math.isfinite(delta_h_t) or not math.isfinite(delta_s_t):
        raise ThermoInputError("Gibbs–Helmholtz result is not finite")
    if abs(delta_g_from_hs - delta_g_compact) > 1e-9:
        raise ThermoInputError(
            "the two ΔG expressions disagree "
            f"({delta_g_from_hs} vs {delta_g_compact})"
        )

    warnings: list[str] = []
    if delta_cp_kcal < 0:
        warnings.append(
            "ΔCp is negative. Protein unfolding ΔCp is usually positive. "
            "The supplied value was still used."
        )
    if converted:
        warnings.append(
            "Inputs were converted from kJ to kcal using 1 kcal = 4.184 kJ."
        )

    supplied = {
        "delta_h": sigma_h is not None,
        "delta_cp": sigma_c is not None,
        "tm": sigma_tm is not None,
    }
    missing = [name for name, present in supplied.items() if not present]
    uncertainty_defined = not missing
    if uncertainty_defined:
        assert sigma_h is not None and sigma_c is not None and sigma_tm is not None
        d_g_d_h = 1.0 - t_k / tm_k
        d_g_d_c = (t_k - tm_k) - t_k * log_ratio
        d_g_d_tm = delta_h_kcal * (t_k / tm_k**2) + delta_cp_kcal * (t_k / tm_k - 1.0)
        d_h_d_h = 1.0
        d_h_d_c = t_k - tm_k
        d_h_d_tm = -delta_cp_kcal
        d_s_d_h = 1.0 / tm_k
        d_s_d_c = log_ratio
        d_s_d_tm = -delta_h_kcal / tm_k**2 - delta_cp_kcal / tm_k
        sigma_g = _quadrature(
            [(d_g_d_h, sigma_h), (d_g_d_c, sigma_c), (d_g_d_tm, sigma_tm)]
        )
        sigma_h_out = _quadrature(
            [(d_h_d_h, sigma_h), (d_h_d_c, sigma_c), (d_h_d_tm, sigma_tm)]
        )
        sigma_s = _quadrature(
            [(d_s_d_h, sigma_h), (d_s_d_c, sigma_c), (d_s_d_tm, sigma_tm)]
        )
        g_low, g_high = _band(delta_g_from_hs, sigma_g)
        h_low, h_high = _band(delta_h_t, sigma_h_out)
        s_low, s_high = _band(delta_s_t, sigma_s)
        uncertainty_note = (
            "95% band is value ± 1.96 sigma from a first-order independent "
            "propagation of the supplied ΔH, ΔCp, and Tm sigmas. "
            "T is treated as exact."
        )
    else:
        sigma_g = None
        sigma_h_out = None
        sigma_s = None
        g_low = g_high = None
        h_low = h_high = None
        s_low = s_high = None
        if len(missing) == 3:
            uncertainty_note = (
                "Uncertainty was not supplied. Output uncertainty is null."
            )
        else:
            joined = ", ".join(missing)
            uncertainty_note = (
                f"Uncertainty was not supplied for {joined}. "
                "Output uncertainty is null. Missing sigmas were not treated as zero."
            )

    assumptions = [
        "Two-state melt: ΔG(Tm) = 0, so ΔS(Tm) = ΔH_m / Tm. "
        "That equality is the model condition, not a measured entropy.",
        "ΔCp is constant between T and Tm.",
        "Temperatures in the equation are kelvin: T_K = t_C + 273.15.",
        "This is the Gibbs–Helmholtz relation Phillips et al. 2012 "
        "(DOI 10.1002/pro.2018) used to obtain unfolding ΔG at 10°C "
        "from ΔHcal, Tm, and ΔCp. It is not a new fit.",
        "calibrated is false. These numbers are arithmetic on the inputs, "
        "not a wet-lab validation and not a DSC trace of a fusion protein.",
        "The result is not a measurement of the Hong Kong team fusion.",
        "Tm was not interpolated across repeat counts, and thermal series "
        "were not averaged.",
        "The evaluation temperature T has no sigma in this calculator and "
        "is treated as exact.",
    ]

    return {
        "calibrated": False,
        "model": "two_state_gibbs_helmholtz",
        "equation": EQUATION_TEXT,
        "delta_g": delta_g_from_hs,
        "delta_g_compact": delta_g_compact,
        "delta_h": delta_h_t,
        "delta_s": delta_s_t,
        "delta_s_at_tm": delta_s_tm,
        "delta_g_units": _ENERGY_UNITS,
        "delta_h_units": _ENERGY_UNITS,
        "delta_s_units": _ENTROPY_UNITS,
        "delta_cp": delta_cp_kcal,
        "delta_cp_units": _ENTROPY_UNITS,
        "delta_h_at_tm": delta_h_kcal,
        "t_c": t_c_value,
        "t_k": t_k,
        "tm_c": tm_c_value,
        "tm_k": tm_k,
        "t_units": "C",
        "t_k_units": "K",
        "tm_units": "C",
        "tm_k_units": "K",
        "input_units": units,
        "unit_conversion_applied": converted,
        "unit_conversion_factor_kJ_per_kcal": _KJ_PER_KCAL if converted else None,
        "uncertainty_defined": uncertainty_defined,
        "uncertainty_note": uncertainty_note,
        "delta_g_sigma": sigma_g,
        "delta_g_95_lower": g_low,
        "delta_g_95_upper": g_high,
        "delta_h_sigma": sigma_h_out,
        "delta_h_95_lower": h_low,
        "delta_h_95_upper": h_high,
        "delta_s_sigma": sigma_s,
        "delta_s_95_lower": s_low,
        "delta_s_95_upper": s_high,
        "assumptions": assumptions,
        "warnings": warnings,
    }


def _delta_g_identity_at_tm(tm_c: object) -> dict[str, Any] | None:
    """ΔG(Tm) = 0 when Tm is finite. None when Tm was not supplied.

    A non-finite Tm raises ``ThermoInputError``. ``None`` means the caller
    did not give a melting temperature, so this function does not invent ΔG.
    ΔH, ΔS, and ΔCp are not arguments. They are not inferred.
    """
    if tm_c is None:
        return None
    tm_c_value = _as_finite("tm_c", tm_c)
    tm_k = _celsius_to_kelvin("Tm", tm_c_value)
    return {
        "delta_g_at_tm": 0.0,
        "delta_g_units": _ENERGY_UNITS,
        "tm_c": tm_c_value,
        "tm_k": tm_k,
        "uncertainty_defined": False,
        "delta_g_sigma": None,
        "delta_g_95_lower": None,
        "delta_g_95_upper": None,
        "uncertainty_note": (
            "No uncertainty band is attached to ΔG(Tm) = 0. "
            "The identity holds only for a two-state melt. "
            "It is not a wet-lab fit."
        ),
    }


def _no_curve(missing: list[str], tm_c: object) -> dict[str, Any]:
    """An absent curve. Missing calorimetry is not filled with zeros.

    A finite Tm still reports ΔG(Tm) = 0. That single value is not a
    plotted curve. A missing Tm leaves ``delta_g_at_tm`` null.
    """
    if len(missing) == 1:
        lead = f"{missing[0]} is missing."
    else:
        lead = f"{' and '.join(missing)} are missing."
    identity = _delta_g_identity_at_tm(tm_c)
    if identity is None:
        message = (
            f"{lead} Calorimetry inputs are missing. "
            "No ΔH(T), ΔS(T), or ΔG(T) curve is computed. "
            "No melting temperature was supplied, so ΔG was not invented."
        )
        assumptions = [
            "No finite melting temperature was supplied, so ΔG was not invented.",
            "ΔHcal and ΔCp were not both supplied, so the Gibbs–Helmholtz "
            "equation was not evaluated. Missing calorimetry inputs are "
            "not replaced with zero.",
        ]
        tm_c_value = None
        tm_k = None
        delta_g_at_tm = None
        delta_g_units = None
        uncertainty_note = (
            "No ΔG was reported, so no uncertainty band was attached."
        )
    else:
        message = (
            f"{lead} Calorimetry inputs are missing. "
            "No ΔH(T), ΔS(T), or ΔG(T) curve is computed. "
            "ΔG at the melting temperature is 0. "
            "You do not need ΔH or ΔS for that value."
        )
        assumptions = [
            _TWO_STATE_IDENTITY,
            "ΔHcal and ΔCp were not both supplied, so no temperature curve "
            "was computed. Missing calorimetry inputs are not replaced "
            "with zero and are not plotted.",
        ]
        tm_c_value = identity["tm_c"]
        tm_k = identity["tm_k"]
        delta_g_at_tm = identity["delta_g_at_tm"]
        delta_g_units = identity["delta_g_units"]
        uncertainty_note = identity["uncertainty_note"]
    return {
        "calibrated": False,
        "model": "two_state_gibbs_helmholtz",
        "equation": EQUATION_TEXT,
        "has_curve": False,
        "message": message,
        "result_label": _CURVE_LABEL,
        "missing_inputs": missing,
        "points": [],
        "delta_g": None,
        "delta_h": None,
        "delta_s": None,
        "delta_g_at_tm": delta_g_at_tm,
        "delta_g_units": delta_g_units,
        "delta_h_units": None,
        "delta_s_units": None,
        "tm_c": tm_c_value,
        "tm_k": tm_k,
        "t_units": "C",
        "t_k_units": "K",
        "uncertainty_defined": False,
        "uncertainty_note": uncertainty_note,
        "delta_g_sigma": None,
        "delta_g_95_lower": None,
        "delta_g_95_upper": None,
        "warnings": [],
        "assumptions": assumptions,
    }


def _curve_grid(
    t_min_c: float,
    t_max_c: float,
    n_points: int,
    tm_c: float,
) -> list[float]:
    """Even °C samples. Tm replaces the nearest sample when it lies inside."""
    step = (t_max_c - t_min_c) / (n_points - 1)
    values = [t_min_c + step * index for index in range(n_points)]
    values[-1] = t_max_c
    if t_min_c <= tm_c <= t_max_c:
        nearest = min(range(n_points), key=lambda index: abs(values[index] - tm_c))
        values[nearest] = tm_c
    return values


def gibbs_helmholtz_curves(
    tm_c: object,
    delta_h: object,
    delta_cp: object,
    *,
    t_min_c: object = _DEFAULT_CURVE_T_MIN_C,
    t_max_c: object = _DEFAULT_CURVE_T_MAX_C,
    n_points: object = _DEFAULT_CURVE_POINTS,
    units: object = "kcal",
) -> dict[str, Any]:
    """ΔH(T), ΔS(T), and ΔG(T) on a temperature grid.

    ``delta_h`` is ΔHcal (ΔH at Tm). ``delta_cp`` is ΔCp. Either one
    being ``None`` returns ``has_curve`` false and an empty ``points``
    list. No zero series is invented. If ``tm_c`` is a finite
    temperature, ``delta_g_at_tm`` is still 0. That is the two-state
    identity, not a curve. If ``tm_c`` is ``None``, ``delta_g_at_tm``
    stays null. Any other non-finite input raises ``ThermoInputError``.

    The grid defaults are a display window (0 °C to 100 °C, 101 points),
    not a measured DSC range. When Tm lies inside that window, one sample
    is exactly Tm so ΔG(Tm) = 0 is on the curve.

    This is the same arithmetic as ``gibbs_helmholtz_report``. It is not
    a fit and not a wet-lab result. ``calibrated`` is false.
    """
    missing: list[str] = []
    if delta_h is None:
        missing.append("ΔHcal")
    if delta_cp is None:
        missing.append("ΔCp")
    if missing:
        return _no_curve(missing, tm_c)

    tm_c_value = _as_finite("tm_c", tm_c)
    if t_min_c is None:
        t_min_c = _DEFAULT_CURVE_T_MIN_C
    if t_max_c is None:
        t_max_c = _DEFAULT_CURVE_T_MAX_C
    t_min_value = _as_finite("t_min_c", t_min_c)
    t_max_value = _as_finite("t_max_c", t_max_c)
    if isinstance(n_points, bool) or not isinstance(n_points, int):
        raise ThermoInputError("n_points must be an integer >= 2")
    if n_points < 2 or n_points > _MAX_CURVE_POINTS:
        raise ThermoInputError(
            f"n_points must be an integer from 2 to {_MAX_CURVE_POINTS}"
        )
    if t_max_value <= t_min_value:
        raise ThermoInputError("t_max_c must be greater than t_min_c")

    at_tm = gibbs_helmholtz_report(
        tm_c_value,
        tm_c_value,
        delta_h,
        delta_cp,
        units=units,
    )
    grid = _curve_grid(t_min_value, t_max_value, n_points, tm_c_value)
    points: list[dict[str, float]] = []
    for t_c_value in grid:
        point = gibbs_helmholtz_report(
            t_c_value,
            tm_c_value,
            delta_h,
            delta_cp,
            units=units,
        )
        points.append(
            {
                "t_c": point["t_c"],
                "t_k": point["t_k"],
                "delta_h": point["delta_h"],
                "delta_s": point["delta_s"],
                "delta_g": point["delta_g"],
            }
        )

    return {
        "calibrated": False,
        "model": "two_state_gibbs_helmholtz",
        "equation": EQUATION_TEXT,
        "has_curve": True,
        "message": _CURVE_LABEL,
        "result_label": _CURVE_LABEL,
        "missing_inputs": [],
        "points": points,
        "delta_g_at_tm": at_tm["delta_g"],
        "delta_h_at_tm": at_tm["delta_h"],
        "delta_s_at_tm": at_tm["delta_s"],
        "delta_g_units": at_tm["delta_g_units"],
        "delta_h_units": at_tm["delta_h_units"],
        "delta_s_units": at_tm["delta_s_units"],
        "delta_cp": at_tm["delta_cp"],
        "delta_cp_units": at_tm["delta_cp_units"],
        "tm_c": at_tm["tm_c"],
        "tm_k": at_tm["tm_k"],
        "t_min_c": t_min_value,
        "t_max_c": t_max_value,
        "t_units": "C",
        "t_k_units": "K",
        "n_points": n_points,
        "tm_on_curve": any(abs(point["t_c"] - tm_c_value) < 1e-9 for point in points),
        "input_units": at_tm["input_units"],
        "unit_conversion_applied": at_tm["unit_conversion_applied"],
        "unit_conversion_factor_kJ_per_kcal": at_tm["unit_conversion_factor_kJ_per_kcal"],
        "assumptions": at_tm["assumptions"]
        + [
            "The curve is this equation evaluated on a temperature grid. "
            "It is not a fitted DSC trace.",
            "The default grid, 0 °C to 100 °C, is a display window. "
            "It is not a literature melting range.",
        ],
        "warnings": at_tm["warnings"],
    }


def _raw_rows() -> list[dict[str, Any]]:
    payload = json.loads(literature_table_path().read_text(encoding="utf-8"))
    if isinstance(payload, list):
        rows = payload
    elif isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        rows = payload["rows"]
    else:
        raise ThermoInputError("literature table has no rows array")
    return [row for row in rows if isinstance(row, dict)]


def _key_present(rows: list[dict[str, Any]], names: tuple[str, ...]) -> bool:
    return any(name in row for row in rows for name in names)


def _optional_number(row: dict[str, Any], names: tuple[str, ...]) -> float | None:
    """Copy a numeric field when one of ``names`` is present. Never fill."""
    for name in names:
        if name not in row:
            continue
        value = row[name]
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        number = float(value)
        if not math.isfinite(number):
            return None
        return number
    return None


def _optional_units(row: dict[str, Any], names: tuple[str, ...]) -> str | None:
    for name in names:
        units_key = f"{name}_units"
        if units_key in row and isinstance(row[units_key], str) and row[units_key].strip():
            return row[units_key]
    return None


def _source_from_observation(obs: ThermalObservation | None) -> dict[str, Any] | None:
    if obs is None:
        return None
    return {
        "record_id": obs.record_id,
        "observable": obs.observable,
        "value": obs.value,
        "units": obs.units,
        "uncertainty": obs.uncertainty,
        "doi": obs.doi,
        "method": obs.method,
        "citation": obs.citation,
        "figure_or_table": obs.figure_or_table,
        "buffer": obs.buffer,
        "pH": obs.pH,
        "construct": obs.construct,
        "n_repeats": obs.n_repeats,
    }


def _shared_source_field(sources: list[dict[str, Any]], field: str) -> Any:
    values = [source[field] for source in sources]
    if not values:
        return None
    first = values[0]
    if all(item == first for item in values):
        return first
    return None


def thermo_prefill(series_id: str, n_repeats: int) -> dict[str, Any]:
    """Cited Tm, ΔG, ΔH, and ΔCp for one named series and repeat count.

    Tm and ΔG are copied from the literature table when that series has
    a single row at ``n_repeats``. A copied ΔG is marked ``looked_up``
    and carries the temperature that Phillips Table I states for that
    column (10 °C). It is not calculated from Tm. ΔH and ΔCp are copied
    only when the JSON row has those fields. Otherwise they are null.
    This function does not interpolate a missing n and does not average
    rows.
    """
    if not isinstance(series_id, str) or series_id.strip() == "":
        raise ThermoInputError("series_id is required")
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise ThermoInputError("n must be an integer >= 1")
    if n_repeats < 1:
        raise ThermoInputError("n must be an integer >= 1")

    try:
        series_rows = load_named_series(series_id)
    except ValueError as exc:
        raise ThermoInputError(str(exc)) from exc
    tm_matches = [row for row in series_rows if row.n_repeats == n_repeats]

    omissions: list[str] = []
    tm_obs: ThermalObservation | None
    if len(tm_matches) == 1:
        tm_obs = tm_matches[0]
    elif len(tm_matches) == 0:
        tm_obs = None
        omissions.append(
            "no Tm row at this n; interpolation is not applied"
        )
    else:
        tm_obs = None
        omissions.append(
            f"{len(tm_matches)} Tm rows share this series and n; they were not averaged"
        )

    dg_obs = delta_g_at_n(series_id, n_repeats)
    if dg_obs is None:
        omissions.append("no single ΔG row at this n in the companion column")

    cited_n = sorted({row.n_repeats for row in series_rows})
    if tm_obs is not None:
        tm_status = "cited"
    elif not cited_n or n_repeats < cited_n[0] or n_repeats > cited_n[-1]:
        tm_status = "extrapolated"
    else:
        tm_status = "omitted"

    raw_rows = _raw_rows()
    has_dh_column = _key_present(raw_rows, _DELTA_H_KEYS)
    has_dcp_column = _key_present(raw_rows, _DELTA_CP_KEYS)
    record_ids = {
        obs.record_id
        for obs in (tm_obs, dg_obs)
        if obs is not None
    }
    matched_raw = [row for row in raw_rows if row.get("record_id") in record_ids]

    delta_h: float | None = None
    delta_h_units: str | None = None
    delta_cp: float | None = None
    delta_cp_units: str | None = None
    if not has_dh_column:
        omissions.append(
            "delta_h is not a column in ctpr_thermal_literature.json"
        )
    else:
        found = [(_optional_number(row, _DELTA_H_KEYS), row) for row in matched_raw]
        numbers = [(value, row) for value, row in found if value is not None]
        if len(numbers) == 1:
            delta_h = numbers[0][0]
            delta_h_units = _optional_units(numbers[0][1], _DELTA_H_KEYS)
        elif len(numbers) == 0:
            omissions.append("no ΔH value on the row for this series and n")
        else:
            omissions.append("more than one ΔH value; they were not averaged")
    if not has_dcp_column:
        omissions.append(
            "delta_cp is not a column in ctpr_thermal_literature.json"
        )
    else:
        found_cp = [(_optional_number(row, _DELTA_CP_KEYS), row) for row in matched_raw]
        numbers_cp = [(value, row) for value, row in found_cp if value is not None]
        if len(numbers_cp) == 1:
            delta_cp = numbers_cp[0][0]
            delta_cp_units = _optional_units(numbers_cp[0][1], _DELTA_CP_KEYS)
        elif len(numbers_cp) == 0:
            omissions.append("no ΔCp value on the row for this series and n")
        else:
            omissions.append("more than one ΔCp value; they were not averaged")

    sources = [
        source
        for source in (
            _source_from_observation(tm_obs),
            _source_from_observation(dg_obs),
        )
        if source is not None
    ]
    if len(sources) > 1 and _shared_source_field(sources, "doi") is None:
        omissions.append("source rows disagree on doi; doi was left null")
    if len(sources) > 1 and _shared_source_field(sources, "method") is None:
        omissions.append("source rows disagree on method; method was left null")

    return {
        "series_id": series_id,
        "n_repeats": n_repeats,
        "calibrated": False,
        "interpolated": False,
        "averaged": False,
        "tm_status": tm_status,
        "tm_c": None if tm_obs is None else tm_obs.value,
        "tm_units": None if tm_obs is None else tm_obs.units,
        "tm_uncertainty": None if tm_obs is None else tm_obs.uncertainty,
        "delta_g": None if dg_obs is None else dg_obs.value,
        "delta_g_units": None if dg_obs is None else dg_obs.units,
        "delta_g_uncertainty": None if dg_obs is None else dg_obs.uncertainty,
        "delta_g_origin": None if dg_obs is None else "looked_up",
        "delta_g_t_c": None if dg_obs is None else _PHILLIPS_TABLE_I_DELTA_G_T_C,
        "delta_g_t_units": None if dg_obs is None else "C",
        "delta_h": delta_h,
        "delta_h_units": delta_h_units,
        "delta_cp": delta_cp,
        "delta_cp_units": delta_cp_units,
        "doi": _shared_source_field(sources, "doi"),
        "method": _shared_source_field(sources, "method"),
        "citation": _shared_source_field(sources, "citation"),
        "figure_or_table": _shared_source_field(sources, "figure_or_table"),
        "buffer": _shared_source_field(sources, "buffer"),
        "pH": _shared_source_field(sources, "pH"),
        "construct": _shared_source_field(sources, "construct"),
        "sources": sources,
        "omissions": omissions,
    }
