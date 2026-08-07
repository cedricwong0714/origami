# src/ode_model/base_solver.py
"""Universal numerical integrator for ORIGAMI proximity / assembly ODEs."""

from __future__ import annotations

from typing import Any, Callable, Optional, Tuple

import numpy as np
from scipy.integrate import solve_ivp


def solve_mechanism_ode(
    derivative_func: Callable,
    initial_state: list[float],
    params: dict,
    time_span: Tuple[float, float] = (0.0, 100.0),
    num_points: int = 100,
    method: str = "LSODA",
    return_metadata: bool = False,
) -> Tuple[np.ndarray, np.ndarray] | Tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """
    Integrate a mechanism ODE.

    Prefers LSODA (stiff-capable automatic method switching). Falls back to
    RK45 if LSODA fails. High-precision tolerances (rtol=1e-8, atol=1e-10).
    """
    t_eval = np.linspace(time_span[0], time_span[1], num_points)

    def _integrate(chosen: str):
        return solve_ivp(
            fun=lambda t, y: derivative_func(t, y, params),
            t_span=time_span,
            y0=initial_state,
            t_eval=t_eval,
            method=chosen,
            rtol=1e-8,
            atol=1e-10,
        )

    sol = _integrate(method)
    used_method = method
    if not sol.success and method != "RK45":
        sol = _integrate("RK45")
        used_method = "RK45"

    if not sol.success:
        raise RuntimeError(f"ODE integration failed ({used_method}): {sol.message}")

    if return_metadata:
        meta = {
            "method": used_method,
            "success": bool(sol.success),
            "nfev": int(getattr(sol, "nfev", 0)),
            "njev": int(getattr(sol, "njev", 0) or 0),
            "message": str(sol.message),
        }
        return sol.t, sol.y, meta
    return sol.t, sol.y
