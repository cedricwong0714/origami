"""Calcium dose–response on the caller's luminescence series.

The curve is

    L = L_min + (L_max − L_min) / (1 + (EC50 / [Ca])^h)

EC50 is the calcium midpoint of this assay. It is not a CaM–M13
dissociation constant. The peptide Kd in ``origami.priors`` is not
read or replaced here.

If the Hill slope is not identifiable, the same points are fit again
with h fixed at 1. That fixed slope is an assumption, written on the
result. It is not a measured cooperativity.

Three temperatures (25 °C, 30 °C, 37 °C) are stored as luminosities and
ratios. They are not an activation energy and not a melting temperature.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.optimize import curve_fit

from origami.assay.uncertainty import Z95, quotient
from origami.assay.window import _result, _series

MODEL_NAME = "calcium_logistic"
MODEL_VERSION = "1"


def _calcium_result(**kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("model_name", MODEL_NAME)
    kwargs.setdefault("model_version", MODEL_VERSION)
    return _result(**kwargs)


# Positive floor for EC50 (M) and Hill slope inside curve_fit. Not a
# measured calcium concentration or a measured Hill coefficient.
_POSITIVE_FLOOR = 1e-15


def _logistic(
    ca_M: np.ndarray,
    l_min: float,
    l_max: float,
    ec50_M: float,
    hill: float,
) -> np.ndarray:
    ratio = np.clip(ec50_M / ca_M, 1e-30, 1e30)
    return l_min + (l_max - l_min) / (1.0 + ratio**hill)


def _logistic_hill_one(
    ca_M: np.ndarray,
    l_min: float,
    l_max: float,
    ec50_M: float,
) -> np.ndarray:
    return _logistic(ca_M, l_min, l_max, ec50_M, 1.0)


def fit_calcium_response(ca_M: object, rlu: object) -> dict[str, Any]:
    """Fit the logistic calcium curve. Refuse a non-identifiable EC50."""
    try:
        calcium = _series("ca_M", ca_M)
        luminescence = _series("rlu", rlu)
    except ValueError as exc:
        return _calcium_result(computable=False, missing=[str(exc)], warnings=[])
    if calcium.size != luminescence.size:
        return _calcium_result(
            computable=False,
            missing=["ca_M and rlu must have the same length"],
            warnings=[],
        )
    if np.any(calcium <= 0):
        return _calcium_result(
            computable=False,
            missing=["every calcium concentration must be > 0"],
            warnings=[],
        )
    if calcium.size < 4 or float(np.ptp(calcium)) == 0.0:
        return _calcium_result(
            computable=False,
            missing=["at least four different calcium concentrations are required"],
            warnings=[],
            model_name=MODEL_NAME,
        )

    warnings: list[str] = [
        "EC50 is the midpoint of this luminescence curve. It does not replace the CaM–M13 peptide Kd."
    ]
    free = _fit_free_hill(calcium, luminescence)
    if free is not None:
        free["warnings"] = warnings + free["warnings"]
        return free
    warnings.append(
        "The Hill slope was not identifiable, so it was fixed at 1. That is an assumption, not a measured cooperativity."
    )
    return _fit_fixed_hill(calcium, luminescence, warnings)


def _fit_free_hill(
    calcium: np.ndarray, luminescence: np.ndarray
) -> dict[str, Any] | None:
    l_min0 = float(np.min(luminescence))
    l_max0 = float(np.max(luminescence))
    if l_max0 <= l_min0:
        l_max0 = l_min0 + 1.0
    ec50_0 = float(np.exp(np.mean(np.log(calcium))))
    try:
        coef, pcov = curve_fit(
            _logistic,
            calcium,
            luminescence,
            p0=(l_min0, l_max0, ec50_0, 1.0),
            bounds=(
                [-np.inf, -np.inf, _POSITIVE_FLOOR, _POSITIVE_FLOOR],
                [np.inf, np.inf, np.inf, 20.0],
            ),
            maxfev=20000,
        )
    except (RuntimeError, ValueError):
        return None
    se = _ses(pcov, 4)
    ec50 = float(coef[2])
    hill = float(coef[3])
    if se is None or se[2] is None or se[3] is None:
        return None
    if se[2] > abs(ec50) or hill <= _POSITIVE_FLOOR * 1.01 or hill >= 19.9:
        return None
    return _calcium_payload(
        l_min=float(coef[0]),
        l_max=float(coef[1]),
        ec50_M=ec50,
        hill=hill,
        se=se,
        hill_fixed=False,
        n_points=int(calcium.size),
        warnings=[],
    )


def _fit_fixed_hill(
    calcium: np.ndarray,
    luminescence: np.ndarray,
    warnings: list[str],
) -> dict[str, Any]:
    l_min0 = float(np.min(luminescence))
    l_max0 = float(np.max(luminescence))
    if l_max0 <= l_min0:
        l_max0 = l_min0 + 1.0
    ec50_0 = float(np.exp(np.mean(np.log(calcium))))
    try:
        coef, pcov = curve_fit(
            _logistic_hill_one,
            calcium,
            luminescence,
            p0=(l_min0, l_max0, ec50_0),
            bounds=(
                [-np.inf, -np.inf, _POSITIVE_FLOOR],
                [np.inf, np.inf, np.inf],
            ),
            maxfev=20000,
        )
    except (RuntimeError, ValueError) as exc:
        return _calcium_result(
            computable=False, missing=[f"calcium fit failed: {exc}"], warnings=warnings
        )
    se3 = _ses(pcov, 3)
    ec50 = float(coef[2])
    if se3 is None or se3[2] is None or se3[2] > abs(ec50):
        return _calcium_result(
            computable=False,
            missing=["EC50 is not identifiable from these points"],
            warnings=warnings,
        )
    se = (se3[0], se3[1], se3[2], None)
    return _calcium_payload(
        l_min=float(coef[0]),
        l_max=float(coef[1]),
        ec50_M=ec50,
        hill=1.0,
        se=se,
        hill_fixed=True,
        n_points=int(calcium.size),
        warnings=warnings,
    )


def _calcium_payload(
    *,
    l_min: float,
    l_max: float,
    ec50_M: float,
    hill: float,
    se: tuple[float | None, float | None, float | None, float | None],
    hill_fixed: bool,
    n_points: int,
    warnings: list[str],
) -> dict[str, Any]:
    ec50_sigma = se[2]
    low = None if ec50_sigma is None else ec50_M - Z95 * ec50_sigma
    high = None if ec50_sigma is None else ec50_M + Z95 * ec50_sigma
    return _calcium_result(
        computable=True,
        missing=[],
        warnings=warnings,
        model_name=MODEL_NAME,
        model_version=MODEL_VERSION,
        equation="L = L_min + (L_max - L_min) / (1 + (EC50 / [Ca])^h)",
        l_min=l_min,
        l_max=l_max,
        ec50_M=ec50_M,
        ec50_sigma_M=ec50_sigma,
        ec50_95_lower_M=low,
        ec50_95_upper_M=high,
        hill=hill,
        hill_sigma=None if hill_fixed else se[3],
        hill_fixed_at_one=hill_fixed,
        n_points=n_points,
        replaces_cam_m13_kd=False,
    )


def scrambled_ratio(
    wt_rlu: object,
    scrambled_rlu: object,
    wt_sigma: object = None,
    scrambled_sigma: object = None,
) -> dict[str, Any]:
    """Ratio of scrambled-M13 luminescence to the wild-type response."""
    from origami.assay.uncertainty import finite_number, optional_sigma

    try:
        wt = finite_number("wt_rlu", wt_rlu)
        scrambled = finite_number("scrambled_rlu", scrambled_rlu)
        sig_wt = optional_sigma("wt_sigma", wt_sigma)
        sig_sc = optional_sigma("scrambled_sigma", scrambled_sigma)
    except ValueError as exc:
        return _calcium_result(computable=False, missing=[str(exc)], warnings=[])
    if wt == 0.0:
        return _calcium_result(
            computable=False,
            missing=["wild-type RLU must be non-zero"],
            warnings=[],
        )
    value, sigma = quotient(scrambled, wt, sig_sc, sig_wt)
    low = None if sigma is None else value - Z95 * sigma
    high = None if sigma is None else value + Z95 * sigma
    return _calcium_result(
        computable=True,
        missing=[],
        warnings=[
            "This ratio is specificity of the luminescence assay. It is not a dissociation constant."
        ],
        equation="scrambled RLU / wild-type RLU",
        ratio=value,
        ratio_sigma=sigma,
        ratio_95_lower=low,
        ratio_95_upper=high,
    )


def temperature_luminosities(
    rlu_25_C: object = None,
    rlu_30_C: object = None,
    rlu_37_C: object = None,
    sigma_25_C: object = None,
    sigma_30_C: object = None,
    sigma_37_C: object = None,
) -> dict[str, Any]:
    """Store 25 °C, 30 °C, and 37 °C reads and the two ratios that exist.

    Three points are not fit to an Arrhenius line.
    """
    from origami.assay.uncertainty import finite_number, optional_sigma

    points: dict[str, float] = {}
    sigmas: dict[str, float | None] = {}
    provided = {
        "25": (rlu_25_C, sigma_25_C),
        "30": (rlu_30_C, sigma_30_C),
        "37": (rlu_37_C, sigma_37_C),
    }
    try:
        for label, (raw, raw_sigma) in provided.items():
            if raw is None:
                continue
            points[label] = finite_number(f"rlu_{label}_C", raw)
            sigmas[label] = optional_sigma(f"sigma_{label}_C", raw_sigma)
    except ValueError as exc:
        return _calcium_result(computable=False, missing=[str(exc)], warnings=[])
    if not points:
        return _calcium_result(
            computable=False,
            missing=["no temperature luminescence was provided"],
            warnings=[],
        )
    ratios: dict[str, Any] = {}
    if "25" in points and "37" in points and points["25"] != 0.0:
        value, sigma = quotient(points["37"], points["25"], sigmas["37"], sigmas["25"])
        ratios["L37_over_L25"] = _ratio_dict(value, sigma)
    if "25" in points and "30" in points and points["25"] != 0.0:
        value, sigma = quotient(points["30"], points["25"], sigmas["30"], sigmas["25"])
        ratios["L30_over_L25"] = _ratio_dict(value, sigma)
    return _calcium_result(
        computable=True,
        missing=[],
        warnings=[
            "These are luminosities at three temperatures. They are not a scaffold melting temperature and not an activation energy."
        ],
        rlu_by_temperature_C=points,
        sigma_by_temperature_C=sigmas,
        ratios=ratios,
        arrhenius_fit=False,
    )


def _ratio_dict(value: float, sigma: float | None) -> dict[str, float | None]:
    low = None if sigma is None else value - Z95 * sigma
    high = None if sigma is None else value + Z95 * sigma
    return {
        "value": value,
        "sigma": sigma,
        "interval_95_lower": low,
        "interval_95_upper": high,
    }


def _ses(pcov: np.ndarray, n: int) -> tuple[float | None, ...] | None:
    if pcov is None or pcov.shape != (n, n):
        return None
    ses: list[float | None] = []
    for index in range(n):
        variance = float(pcov[index, index])
        if not math.isfinite(variance) or variance < 0:
            return None
        ses.append(math.sqrt(variance))
    return tuple(ses)
