import numpy as np
from src.ode_model.base_solver import solve_mechanism_ode

def covalent_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    T, W, Comp, Adduct = y
    k_on = params.get("k_on", 5.0)
    k_off = params.get("k_off", 1.0)
    k_inact = params.get("k_inact", 0.5)

    d_bind = k_on * T * W - k_off * Comp
    dComp_dt = d_bind - k_inact * Comp
    dAdduct_dt = k_inact * Comp

    return [-d_bind, -d_bind, dComp_dt, dAdduct_dt]

def simulate_covalent_capture(initial_concs: dict, params: dict = None, time_span=(0.0, 100.0), num_points=100):
    params = params or {}
    y0 = [initial_concs.get("S", 1.0), initial_concs.get("E", 1.0), 0.0, 0.0]
    t, y = solve_mechanism_ode(covalent_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[2], "P": y[3]}
