"""Intermediate-transfer (substrate channeling) ODE — canonical implementation.

Parameters are resolved with provenance discipline (AGENTS.md §4): explicit
overrides first, then tracked kinetic defaults JSON. No silent inline literals.
"""

from __future__ import annotations

from src.core.asset_paths import resolve_param
from src.ode_model.base_solver import solve_mechanism_ode

_MECHANISM = "intermediate_transfer"


def intermediate_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    """
    Substrate channeling derivatives (e.g. OtsA/OtsB).
    y = [Substrate, Enzyme1, Enzyme2, Intermediate_Bulk, Intermediate_Channeled, Product]

    E1 and E2 are catalysts held constant (derivative 0); only the substrate,
    intermediate, and product pools carry flux. This is intentional catalyst
    bookkeeping, not a mass leak: the conserved inventory is S + I_bulk + I_chan + P.
    """
    S, E1, E2, I_bulk, I_chan, P = y
    k_cat1 = resolve_param(_MECHANISM, "k_cat1", params)
    k_cat2 = resolve_param(_MECHANISM, "k_cat2", params)
    k_channel = resolve_param(_MECHANISM, "k_channel", params)
    k_escape = resolve_param(_MECHANISM, "k_escape", params)

    dS_dt = -k_cat1 * S * E1
    dI_chan_dt = k_cat1 * S * E1 - k_channel * I_chan - k_escape * I_chan
    dI_bulk_dt = k_escape * I_chan - k_cat2 * I_bulk * E2
    dP_dt = k_channel * I_chan + k_cat2 * I_bulk * E2

    return [dS_dt, 0.0, 0.0, dI_bulk_dt, dI_chan_dt, dP_dt]


def simulate_intermediate_transfer(
    initial_concs: dict,
    params: dict = None,
    time_span: tuple[float, float] = (0.0, 100.0),
    num_points: int = 100,
):
    params = params or {}
    y0 = [
        initial_concs.get("S", 1.0),
        initial_concs.get("E", 0.1),
        initial_concs.get("E2", 0.1),
        0.0,
        0.0,
        0.0,
    ]
    t, y = solve_mechanism_ode(intermediate_derivatives, y0, params, time_span, num_points)

    total_intermediate = y[3] + y[4]
    return t, {
        "S": y[0],
        "E": y[1],
        "ES": total_intermediate,
        "P": y[5],
    }
