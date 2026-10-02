"""Local parameter sensitivity of predicted luminescence.

This reports elasticities, not uncertainty. Most CLASP kinetic parameters
(k_on, k_off, k_lock, alpha, eta, r0) carry no published error bar in this
codebase, so a parameter-propagated confidence interval cannot honestly be
built from them. What can be stated is how strongly the prediction responds
to each parameter, which identifies the parameters whose missing error bars
matter most.

Elasticity e_p = d ln(R) / d ln(p), estimated by a central difference with a
relative step of STEP. STEP is a numerical choice, not a biological constant.
Parameters that are exactly zero are skipped (log scale undefined).
"""

from __future__ import annotations

import math
from typing import Any

from src.core.clasp_assembly import CLASPParameters, predict_luminescence

STEP = 0.05
SWEPT = ("k_c_M", "n_h", "k_on", "k_off", "k_lock", "r0", "alpha", "eta")


def parameter_elasticities(
    calcium_M: float,
    params: CLASPParameters | None = None,
    E_T: float = 1e-6,
    M_T: float = 1e-6,
    t_end: float = 3600.0,
) -> dict[str, Any]:
    """Central-difference elasticity of endpoint luminescence per parameter."""
    base = params or CLASPParameters()

    def run(p: CLASPParameters) -> float:
        return float(predict_luminescence([calcium_M], p, E_T=E_T, M_T=M_T, t_end=t_end)[0])

    r0_value = run(base)
    if r0_value <= 0 or not math.isfinite(r0_value):
        raise ValueError(f"Baseline luminescence {r0_value} is not positive and finite.")

    elasticities: dict[str, float] = {}
    for name in SWEPT:
        value = getattr(base, name)
        if value == 0:
            continue
        hi = run(base._replace(**{name: value * (1 + STEP)}))
        lo = run(base._replace(**{name: value * (1 - STEP)}))
        if hi <= 0 or lo <= 0:
            continue
        elasticities[name] = (math.log(hi) - math.log(lo)) / (
            math.log(1 + STEP) - math.log(1 - STEP)
        )

    most = max(elasticities, key=lambda k: abs(elasticities[k])) if elasticities else None
    return {
        "calcium_M": calcium_M,
        "baseline_luminescence_RLU": r0_value,
        "elasticities": elasticities,
        "most_sensitive_parameter": most,
        "relative_step": STEP,
        "is_uncertainty": False,
        "note": (
            "Elasticities show response to each parameter. They are not a "
            "confidence interval; no parameter error bars are propagated."
        ),
    }
