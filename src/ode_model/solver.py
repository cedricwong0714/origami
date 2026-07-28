# src/ode_model/solver.py
import numpy as np
from scipy.integrate import solve_ivp

def system_derivatives(t: float, y: list[float], k_f: float, k_r: float, k_cat: float) -> list[float]:
    """
    Computes mass balance rate of change for S, E, ES, and P.
    y = [S, E, ES, P]
    """
    S, E, ES, P = y
    dS_dt = -k_f * E * S + k_r * ES
    dE_dt = -k_f * E * S + (k_r + k_cat) * ES
    dES_dt = k_f * E * S - (k_r + k_cat) * ES
    dP_dt = k_cat * ES
    return [dS_dt, dE_dt, dES_dt, dP_dt]

def run_system_simulation(
    initial_concentrations: dict[str, float], 
    time_span: tuple[float, float],
    k_f: float = 1.0,
    k_r: float = 0.1,
    k_cat: float = 0.5
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """
    Integrates the differential equation system using SciPy solve_ivp.
    """
    y0 = [
        initial_concentrations["S"],
        initial_concentrations["E"],
        initial_concentrations["ES"],
        initial_concentrations["P"]
    ]
    
    t_eval = np.linspace(time_span[0], time_span[1], 100)
    
    solution = solve_ivp(
        fun=system_derivatives,
        t_span=time_span,
        y0=y0,
        args=(k_f, k_r, k_cat),
        t_eval=t_eval,
        method="Radau"  # Stiff ODE solver
    )
    
    concentrations = {
        "S": solution.y[0],
        "E": solution.y[1],
        "ES": solution.y[2],
        "P": solution.y[3]
    }
    
    return solution.t, concentrations