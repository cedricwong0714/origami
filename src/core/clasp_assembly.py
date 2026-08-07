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


def assembly_mass_inventory(B: np.ndarray, L: np.ndarray) -> np.ndarray:
    """Total assembled inventory B+L (non-decreasing under pure locking)."""
    return np.asarray(B) + np.asarray(L)
