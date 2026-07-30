import numpy as np
from src.ode_model.base_solver import solve_mechanism_ode

def complementation_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    T, FA, FB, Comp, Active = y
    k_on = params.get("k_on", 10.0)
    k_off = params.get("k_off", 1.0)
    k_rec = params.get("k_rec", 2.0)

    d_bind = k_on * T * FA * FB - k_off * Comp
    dComp_dt = d_bind - k_rec * Comp
    dActive_dt = k_rec * Comp

    return [-d_bind, -d_bind, -d_bind, dComp_dt, dActive_dt]

def simulate_complementation(initial_concs: dict, params: dict = None, time_span=(0.0, 100.0), num_points=100):
    params = params or {}
    y0 = [initial_concs.get("S", 0.5), initial_concs.get("E", 1.0), initial_concs.get("E2", 1.0), 0.0, 0.0]
    t, y = solve_mechanism_ode(complementation_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[3], "P": y[4]}
