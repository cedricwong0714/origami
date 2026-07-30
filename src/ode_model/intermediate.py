# src/ode_model/mechanisms/intermediate.py
import numpy as np
from src.ode_model.base_solver import solve_mechanism_ode

def intermediate_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    """
    Substrate channeling derivatives (e.g. OtsA/OtsB).
    y = [Substrate, Enzyme1, Enzyme2, Intermediate_Bulk, Intermediate_Channeled, Product]
    """
    S, E1, E2, I_bulk, I_chan, P = y
    k_cat1 = params.get("k_cat1", 1.0)
    k_cat2 = params.get("k_cat2", 0.8)
    k_channel = params.get("k_channel", 5.0)  # Proximity-enhanced rate
    k_escape = params.get("k_escape", 0.1)     # Escape rate into bulk

    dS_dt = -k_cat1 * S * E1
    dI_chan_dt = k_cat1 * S * E1 - k_channel * I_chan - k_escape * I_chan
    dI_bulk_dt = k_escape * I_chan - k_cat2 * I_bulk * E2
    dP_dt = k_channel * I_chan + k_cat2 * I_bulk * E2

    return [dS_dt, 0.0, 0.0, dI_bulk_dt, dI_chan_dt, dP_dt]

def simulate_intermediate_transfer(
    initial_concs: dict,
    params: dict = None,
    time_span: tuple[float, float] = (0.0, 100.0),
    num_points: int = 100
):
    params = params or {}
    y0 = [
        initial_concs.get("S", 1.0),
        initial_concs.get("E", 0.1),
        initial_concs.get("E2", 0.1),
        0.0, 0.0, 0.0
    ]
    t, y = solve_mechanism_ode(intermediate_derivatives, y0, params, time_span, num_points)
    
    # y[0] = S, y[3] = I_bulk, y[4] = I_chan, y[5] = P
    # Sum both intermediate pools so S + ES + P == initial_total (1.0)
    total_intermediate = y[3] + y[4]

    return t, {
        "S": y[0],
        "E": y[1],
        "ES": total_intermediate,
        "P": y[5]
    }