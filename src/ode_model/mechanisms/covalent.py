"""Covalent-capture ODE — canonical implementation.

Parameters resolved with provenance discipline (AGENTS.md §4). Profile aliases
k_bond / k_rev map to the recruitment complex formation / locking steps.
"""

from __future__ import annotations

from src.core.asset_paths import resolve_param
from src.ode_model.base_solver import solve_mechanism_ode

_MECHANISM = "covalent_capture"


def covalent_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    T, W, Comp, Adduct = y
    # k_bond = isopeptide locking rate (Comp -> Adduct); k_rev = complex off-rate
    k_bond = resolve_param(_MECHANISM, "k_bond", params)
    k_rev = resolve_param(_MECHANISM, "k_rev", params)
    # Recruitment association rate; falls back to a tracked prior if absent.
    k_on = float(params.get("k_on", 5.0))

    d_bind = k_on * T * W - k_rev * Comp
    dComp_dt = d_bind - k_bond * Comp
    dAdduct_dt = k_bond * Comp

    return [-d_bind, -d_bind, dComp_dt, dAdduct_dt]


def simulate_covalent_capture(
    initial_concs: dict,
    params: dict = None,
    time_span=(0.0, 100.0),
    num_points=100,
):
    params = params or {}
    y0 = [
        initial_concs.get("S", 1.0),
        initial_concs.get("E", 1.0),
        0.0,
        0.0,
    ]
    t, y = solve_mechanism_ode(covalent_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[2], "P": y[3]}
