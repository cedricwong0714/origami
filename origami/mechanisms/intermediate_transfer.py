"""Damköhler-reduced intermediate transfer.

Space is not solved as a PDE. Escape and capture are competing first-order
rates inside one local volume:

    dI/dt = v_prod − (k_escape + k_capture) I
    dP/dt = k_capture I

    Da = k_capture / k_escape
    P(capture before escape) = Da / (1 + Da)
    J_product = v_prod * Da / (1 + Da)

Unsaturated downstream enzyme:

    k_capture = (k_cat / K_m) * C_eff

v_prod, k_escape, and k_cat/K_m are required inputs. This module does not
supply enzyme constants.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class TransferResult:
    da: float
    p_capture: float
    intermediate_ss_M: float
    product_flux_M_per_s: float
    k_capture_per_s: float
    k_escape_per_s: float
    v_prod_M_per_s: float
    c_eff_M: float | None
    time_s: np.ndarray
    intermediate_M: np.ndarray
    product_M: np.ndarray
    units_flux: str = "M/s"
    confidence_tier: str = "hypothesis_only"
    calibrated: bool = False
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def damkohler(k_capture_per_s: float, k_escape_per_s: float) -> float:
    if k_capture_per_s < 0 or k_escape_per_s <= 0:
        raise ValueError("k_capture must be >= 0 and k_escape must be > 0")
    return float(k_capture_per_s / k_escape_per_s)


def capture_probability(da: float) -> float:
    if da < 0:
        raise ValueError("Damköhler number cannot be negative")
    return float(da / (1.0 + da))


def k_capture_from_specificity(kcat_over_km_per_M_s: float, c_eff_M: float) -> float:
    """First-order capture rate in the unsaturated limit."""
    if kcat_over_km_per_M_s < 0 or c_eff_M < 0:
        raise ValueError("kcat/Km and C_eff must be >= 0")
    return float(kcat_over_km_per_M_s * c_eff_M)


def _rhs(_t: float, y: np.ndarray, v_prod: float, k_esc: float, k_cap: float) -> np.ndarray:
    intermediate = y[0]
    return np.array(
        [
            v_prod - (k_esc + k_cap) * intermediate,
            k_cap * intermediate,
        ]
    )


def simulate_transfer(
    v_prod_M_per_s: float,
    k_escape_per_s: float,
    k_capture_per_s: float,
    c_eff_M: float | None = None,
    t_end_s: float | None = None,
    n_eval: int = 80,
) -> TransferResult:
    if v_prod_M_per_s < 0:
        raise ValueError("v_prod cannot be negative")
    da = damkohler(k_capture_per_s, k_escape_per_s)
    p_cap = capture_probability(da)
    k_tot = k_escape_per_s + k_capture_per_s
    i_ss = float(v_prod_M_per_s / k_tot) if k_tot > 0 else 0.0
    flux = float(v_prod_M_per_s * p_cap)
    if t_end_s is None:
        t_end_s = 20.0 / max(k_tot, 1e-12)
    t_eval = np.linspace(0.0, float(t_end_s), n_eval)
    sol = solve_ivp(
        _rhs,
        (0.0, float(t_end_s)),
        np.array([0.0, 0.0]),
        t_eval=t_eval,
        args=(v_prod_M_per_s, k_escape_per_s, k_capture_per_s),
        rtol=1e-6,
        atol=1e-12,
    )
    if not sol.success:
        raise RuntimeError(f"transfer ODE failed: {sol.message}")
    warnings = [
        "Rates are caller-supplied. This is not a calibrated trehalose or CLASP measurement.",
        "Reduced model: no spatial PDE. Diffusion enters only as k_escape.",
    ]
    assumptions = [
        "Well-mixed local volume.",
        "First-order capture (downstream enzyme unsaturated).",
        "Constant production rate v_prod.",
        "P(capture) = Da/(1+Da) with Da = k_capture/k_escape.",
    ]
    return TransferResult(
        da=da,
        p_capture=p_cap,
        intermediate_ss_M=i_ss,
        product_flux_M_per_s=flux,
        k_capture_per_s=k_capture_per_s,
        k_escape_per_s=k_escape_per_s,
        v_prod_M_per_s=v_prod_M_per_s,
        c_eff_M=c_eff_M,
        time_s=sol.t,
        intermediate_M=sol.y[0],
        product_M=sol.y[1],
        assumptions=assumptions,
        warnings=warnings,
    )


def simulate_from_ceff(
    v_prod_M_per_s: float,
    k_escape_per_s: float,
    kcat_over_km_per_M_s: float,
    c_eff_M: float,
    t_end_s: float | None = None,
) -> TransferResult:
    k_cap = k_capture_from_specificity(kcat_over_km_per_M_s, c_eff_M)
    result = simulate_transfer(
        v_prod_M_per_s,
        k_escape_per_s,
        k_cap,
        c_eff_M=c_eff_M,
        t_end_s=t_end_s,
    )
    result.assumptions.append("k_capture = (k_cat/K_m) * C_eff, unsaturated limit.")
    return result
