"""
CLASP recruitment / assembly ODE (CLASP Docs §1.2 / Docs-6 Layer 1).

Governing equations (SI units: M, s):

    f_CaM(C) = C^n / (K_C^n + C^n)

    dB/dt = k_on · f_CaM · (E_T − B − L) · (M_T − B − L)
            − k_off · B − k_lock · B

    dL/dt = k_lock · B

    R(t) = R_0 + α · (B + η · L)

Hill n and EC50 follow ORIGAMI invariants (AGENTS.md §15.1): n≈4, EC50≈2 µM.
Docs-6 cites Linse et al. (1991) n_h=2.5 as an alternative literature value;
that alternative is available via CLASPParameters but is not the default.
"""

from __future__ import annotations

from typing import NamedTuple, Optional

import numpy as np
from scipy.integrate import solve_ivp

from src.core.calcium_kinetics import CAM_CA_EC50_M, CAM_CA_HILL_N


class CLASPParameters(NamedTuple):
    """
    Parameter: CaM–Ca²⁺ half-activation (K_C)
    Value: 2e-6
    Units: M
    Source: Ikura et al. (1992) Science; AGENTS.md §15.1 (ORIGAMI invariant)
    System: CaM Ca²⁺ binding
    Method: Literature consensus / CLASP Docs
    Notes: Docs-6 also cites Linse et al. (1991) J Biol Chem at 2.0 µM

    Parameter: CaM–Ca²⁺ Hill coefficient (n)
    Value: 4.0
    Units: dimensionless
    Source: AGENTS.md §15.1 ORIGAMI invariant (four Ca²⁺ sites)
    System: CaM
    Method: Structural / kinetic consensus
    Notes: Docs-6 cites Linse n_h=2.5; do not silently switch without human review

    Parameter: CaM–M13 association rate (k_on)
    Value: 1e6
    Units: M^-1 s^-1
    Source: Ikura et al. (1992) Science (Docs-6)
    System: CaM + M13 peptide
    Method: Literature kinetic prior
    Notes: Tier-2 literature-parameterized

    Parameter: CaM–M13 dissociation rate (k_off)
    Value: 0.01
    Units: s^-1
    Source: Ikura et al. (1992) Science (Docs-6); Kd≈k_off/k_on≈1e-8 M order
    System: CaM + M13
    Method: Literature kinetic prior
    Notes: Effective Kd under saturating Ca²⁺ is also constrained by CAM_M13_KD

    Parameter: SpyTag–SpyCatcher locking rate (k_lock)
    Value: 0.003
    Units: s^-1
    Source: Zakeri et al. (2012) PNAS (Docs-6)
    System: SpyTag/SpyCatcher isopeptide formation
    Method: Literature kinetic prior
    Notes: Tier-2; calibrate from SDS-PAGE time courses when available
    """

    k_c_M: float = CAM_CA_EC50_M  # 2e-6 M
    n_h: float = CAM_CA_HILL_N  # 4.0 (ORIGAMI invariant)
    k_on: float = 1e6  # M^-1 s^-1
    k_off: float = 0.01  # s^-1
    k_lock: float = 0.003  # s^-1
    r0: float = 100.0  # RLU background
    alpha: float = 1e9  # RLU per M assembled complex (relative scale)
    eta: float = 0.8  # locked reporter efficiency


def cam_activation_fraction(calcium_M: float, params: CLASPParameters) -> float:
    if calcium_M <= 0:
        return 0.0
    return float(
        calcium_M**params.n_h
        / (params.k_c_M**params.n_h + calcium_M**params.n_h)
    )


def clasp_ode(
    t: float,
    y: list[float],
    params: CLASPParameters,
    calcium_M: float,
    E_T: float,
    M_T: float,
) -> list[float]:
    """
    y = [B, L] — reversibly bound and covalently locked payload.
    Conserved inventories: B + L ≤ min(E_T, M_T).
    """
    B, L = y
    f_cam = cam_activation_fraction(calcium_M, params)
    available_E = max(0.0, E_T - B - L)
    available_M = max(0.0, M_T - B - L)
    dB_dt = (
        params.k_on * f_cam * available_E * available_M
        - params.k_off * B
        - params.k_lock * B
    )
    dL_dt = params.k_lock * B
    return [dB_dt, dL_dt]


def simulate_assembly(
    calcium_M: float,
    params: Optional[CLASPParameters] = None,
    E_T: float = 1e-6,
    M_T: float = 1e-6,
    t_end: float = 3600.0,
    num_points: int = 100,
    method: str = "LSODA",
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """
    Integrate CLASP assembly ODE at fixed free calcium.

    Returns time grid and concentrations B(t), L(t), R(t).
    Prefers LSODA (stiff-capable); falls back to RK45 if LSODA fails.
    """
    params = params or CLASPParameters()
    t_eval = np.linspace(0.0, t_end, num_points)

    def _rhs(t, y):
        return clasp_ode(t, y, params, calcium_M, E_T, M_T)

    sol = solve_ivp(
        _rhs,
        (0.0, t_end),
        [0.0, 0.0],
        t_eval=t_eval,
        method=method,
        rtol=1e-8,
        atol=1e-12,
    )
    if not sol.success and method != "RK45":
        sol = solve_ivp(
            _rhs,
            (0.0, t_end),
            [0.0, 0.0],
            t_eval=t_eval,
            method="RK45",
            rtol=1e-8,
            atol=1e-12,
        )
    if not sol.success:
        raise RuntimeError(f"CLASP ODE integration failed: {sol.message}")

    B = sol.y[0]
    L = sol.y[1]
    R = params.r0 + params.alpha * (B + params.eta * L)
    return sol.t, {"B": B, "L": L, "R": R, "assembled": B + L}


def predict_luminescence(
    calcium_series_M: np.ndarray,
    params: Optional[CLASPParameters] = None,
    E_T: float = 1e-6,
    M_T: float = 1e-6,
    t_end: float = 3600.0,
) -> np.ndarray:
    """
    Steady-ish endpoint luminescence across a calcium dose-response series.
    Uses the final time-point of each fixed-calcium integration.
    """
    params = params or CLASPParameters()
    predictions = []
    for calcium in np.asarray(calcium_series_M, dtype=float):
        _, concs = simulate_assembly(
            float(calcium), params=params, E_T=E_T, M_T=M_T, t_end=t_end, num_points=50
        )
        predictions.append(float(concs["R"][-1]))
    return np.asarray(predictions, dtype=float)


def estimate_ec50_from_curve(
    calcium_M: np.ndarray,
    response: np.ndarray,
) -> dict[str, float | None | str]:
    """
    Apparent EC50 = free Ca²⁺ where response crosses half-maximal.

    Half-max is defined as R_min + 0.5 * (R_max − R_min). Interpolation is
    linear in log10([Ca²⁺]) between the bracketing grid points.

    Bounds are the bracketing calcium concentrations (grid resolution), not a
    statistical 95% CI from wet-lab replicates. Label accordingly in UI.
    """
    ca = np.asarray(calcium_M, dtype=float).ravel()
    y = np.asarray(response, dtype=float).ravel()
    if ca.size < 2 or y.size != ca.size:
        return {
            "ec50_M": None,
            "uncertainty_lower_M": None,
            "uncertainty_upper_M": None,
            "half_maximal_response": None,
            "note": "Need ≥2 matched calcium/response points to estimate EC50.",
        }

    order = np.argsort(ca)
    ca = ca[order]
    y = y[order]
    y_min = float(np.min(y))
    y_max = float(np.max(y))
    span = y_max - y_min
    if span <= 0.0 or not np.isfinite(span):
        return {
            "ec50_M": None,
            "uncertainty_lower_M": None,
            "uncertainty_upper_M": None,
            "half_maximal_response": y_min,
            "note": "Response is flat; EC50 is undefined for this curve.",
        }

    half = y_min + 0.5 * span
    # First crossing of half-max when scanning low → high Ca²⁺.
    above = y >= half
    if not np.any(above) or bool(above[0]):
        # Never crosses, or already at/above half at the lowest dose.
        if bool(above[0]) and y[0] >= half:
            return {
                "ec50_M": float(ca[0]),
                "uncertainty_lower_M": None,
                "uncertainty_upper_M": float(ca[1]) if ca.size > 1 else None,
                "half_maximal_response": half,
                "note": (
                    "Half-max already reached at the lowest sampled Ca²⁺; "
                    "EC50 ≤ lowest grid point (extrapolation)."
                ),
            }
        return {
            "ec50_M": None,
            "uncertainty_lower_M": None,
            "uncertainty_upper_M": None,
            "half_maximal_response": half,
            "note": "Half-max not reached within the sampled Ca²⁺ range.",
        }

    i = int(np.argmax(above))  # first True
    ca_lo, ca_hi = float(ca[i - 1]), float(ca[i])
    y_lo, y_hi = float(y[i - 1]), float(y[i])
    if y_hi <= y_lo:
        ec50 = ca_hi
    else:
        frac = (half - y_lo) / (y_hi - y_lo)
        # Interpolate in log10([Ca]) — dose-response is typically log-spaced.
        log_ec50 = np.log10(ca_lo) + frac * (np.log10(ca_hi) - np.log10(ca_lo))
        ec50 = float(10.0**log_ec50)

    return {
        "ec50_M": ec50,
        "uncertainty_lower_M": ca_lo,
        "uncertainty_upper_M": ca_hi,
        "half_maximal_response": half,
        "note": (
            "Apparent EC50 from mechanistic dose-response (log-linear interpolation). "
            "Bounds are bracketing grid points, not wet-lab 95% CI."
        ),
    }


def assembly_mass_inventory(B: np.ndarray, L: np.ndarray) -> np.ndarray:
    """Total assembled inventory B+L (non-decreasing under pure locking)."""
    return np.asarray(B) + np.asarray(L)
