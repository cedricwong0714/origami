"""Uncertainty label for endpoint luminescence.

``predict_luminescence`` returns one RLU. The CLASP ODE parameters that
produce it (``k_c_M``, ``n_h``, ``k_on``, ``k_off``, ``k_lock``, ``r0``,
``alpha``, ``eta``) do not have sourced standard deviations in this
repository. Peptide Kd and the Spy bimolecular rate do have sigmas, and
those sigmas belong to different quantities, so they are not substituted.

Until a sourced sigma exists for an ODE parameter, the interval stays
the fixed ±30% placeholder. A delta-method interval is computed only
when the caller supplies every sigma and marks each one ``user_entered``.
No sigma is invented here. ``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

# Standard-normal 97.5 percentile. Not a biological parameter.
STANDARD_NORMAL_97_5 = 1.96

PLACEHOLDER_METHOD = "fixed_relative_placeholder_pm_30_percent"
DELTA_METHOD = "delta_method_caller_supplied_sigmas"

# Names match CLASPParameters. The notes say why an existing sigma
# elsewhere in origami.priors is not this parameter's error bar.
BLOCKED_PARAMETERS: tuple[dict[str, str], ...] = (
    {
        "name": "k_c_M",
        "units": "M",
        "reason": "CLASPParameters.k_c_M has no sourced standard deviation.",
    },
    {
        "name": "n_h",
        "units": "dimensionless",
        "reason": "The Hill coefficient stored on CLASPParameters has no sourced standard deviation.",
    },
    {
        "name": "k_on",
        "units": "M^-1 s^-1",
        "reason": (
            "CLASPParameters.k_on has no sourced standard deviation. "
            "CAM_M13_KD_M.sigma is a peptide Kd, not this rate."
        ),
    },
    {
        "name": "k_off",
        "units": "s^-1",
        "reason": "CLASPParameters.k_off has no sourced standard deviation.",
    },
    {
        "name": "k_lock",
        "units": "s^-1",
        "reason": (
            "CLASPParameters.k_lock has no sourced standard deviation. "
            "SPY_K_ON_PER_M_S.sigma is a bimolecular rate and is not applied to k_lock."
        ),
    },
    {
        "name": "r0",
        "units": "RLU",
        "reason": "The background scale r0 has no sourced standard deviation.",
    },
    {
        "name": "alpha",
        "units": "RLU per M",
        "reason": "The reporter scale alpha has no sourced standard deviation.",
    },
    {
        "name": "eta",
        "units": "dimensionless",
        "reason": "The locked-reporter factor eta has no sourced standard deviation.",
    },
)


def parameter_error_report() -> dict[str, Any]:
    """Say that ODE parameter error was not propagated."""
    return {
        "parameter_error_propagated": False,
        "uncertainty_method": PLACEHOLDER_METHOD,
        "blocked_parameters": [dict(item) for item in BLOCKED_PARAMETERS],
        "reason": (
            "None of the CLASP ODE parameters has a sourced standard deviation. "
            "A propagated interval was not invented. The band remains "
            "predicted_value multiplied by 0.7 and 1.3."
        ),
        "confidence_tier": "hypothesis_only",
        "calibrated": False,
        "human_review_required": True,
    }


def placeholder_interval(predicted_value: float) -> dict[str, Any]:
    """Fixed relative band plus the reason propagation is blocked."""
    value = float(predicted_value)
    if not math.isfinite(value):
        raise ValueError("predicted luminescence must be finite")
    interval = parameter_error_report()
    interval.update(
        {
            "predicted_value": value,
            "uncertainty_95_lower": value * 0.7,
            "uncertainty_95_upper": value * 1.3,
            "units": "RLU",
        }
    )
    return interval


def delta_method_interval(
    predicted_value: float,
    sensitivities_dR_dp: dict[str, float],
    parameter_sigmas: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Propagate caller-supplied sigmas. Every entry must be user_entered.

    ``sensitivities_dR_dp[name]`` is ∂R/∂p in RLU per parameter unit.
    Variance is the sum of (sensitivity × sigma)². Parameters that are
    absent from ``parameter_sigmas`` are not given a default sigma.
    """
    value = float(predicted_value)
    if not math.isfinite(value):
        raise ValueError("predicted luminescence must be finite")
    if not parameter_sigmas:
        raise ValueError("parameter_sigmas is empty; no interval was invented")
    if set(parameter_sigmas) != set(sensitivities_dR_dp):
        raise ValueError("sensitivities and parameter_sigmas must name the same parameters")
    variance = 0.0
    used: list[dict[str, Any]] = []
    for name, spec in parameter_sigmas.items():
        if not isinstance(spec, dict):
            raise ValueError(f"{name} sigma must be an object")
        if spec.get("provenance") != "user_entered":
            raise ValueError(
                f"{name} sigma provenance must be user_entered. "
                "A literature or placeholder sigma is not applied here."
            )
        sigma = spec.get("sigma")
        if isinstance(sigma, bool) or not isinstance(sigma, (int, float)):
            raise ValueError(f"{name} sigma must be a number")
        sigma_f = float(sigma)
        if not math.isfinite(sigma_f) or sigma_f < 0:
            raise ValueError(f"{name} sigma must be finite and >= 0")
        slope = float(sensitivities_dR_dp[name])
        if not math.isfinite(slope):
            raise ValueError(f"{name} sensitivity must be finite")
        variance += (slope * sigma_f) ** 2
        used.append(
            {
                "name": name,
                "sigma": sigma_f,
                "units": spec.get("units"),
                "sensitivity_dR_dp": slope,
                "provenance": "user_entered",
            }
        )
    half = STANDARD_NORMAL_97_5 * math.sqrt(variance)
    return {
        "predicted_value": value,
        "uncertainty_95_lower": value - half,
        "uncertainty_95_upper": value + half,
        "sigma": math.sqrt(variance),
        "uncertainty_method": DELTA_METHOD,
        "parameter_error_propagated": True,
        "parameters_used": used,
        "confidence_tier": "hypothesis_only",
        "calibrated": False,
        "human_review_required": True,
        "units": "RLU",
        "reason": (
            "The half-width is 1.96 times the delta-method standard deviation "
            "from caller-supplied sigmas. It is not a wet-lab confidence interval."
        ),
    }
