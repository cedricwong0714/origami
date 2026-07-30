# src/ode_model/base_solver.py
import numpy as np
from scipy.integrate import solve_ivp
from typing import Callable, Tuple

def solve_mechanism_ode(
    derivative_func: Callable,
    initial_state: list[float],
    params: dict,
    time_span: Tuple[float, float] = (0.0, 100.0),
    num_points: int = 100
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Universal numerical RK45 integrator for all ORIGAMI proximity models.
    """
    t_eval = np.linspace(time_span[0], time_span[1], num_points)

    sol = solve_ivp(
        fun=lambda t, y: derivative_func(t, y, params),
        t_span=time_span,
        y0=initial_state,
        t_eval=t_eval,
        method="RK45",
        rtol=1e-8,   # High precision relative tolerance
        atol=1e-10   # High precision absolute tolerance
    )

    return sol.t, sol.y