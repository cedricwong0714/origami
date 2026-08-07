"""Redox electron-transfer ODE — canonical implementation (relative ranking).

Parameters resolved with provenance discipline (AGENTS.md §4). The geometric
decay constant ``beta_decay`` is a structural prior (not a rate) sourced here.
"""

from __future__ import annotations

import numpy as np

from src.core.asset_paths import resolve_param
from src.ode_model.base_solver import solve_mechanism_ode

_MECHANISM = "redox_transfer"

# Marcus-theory distance-decay constant for electron transfer (per nm).
# Structural prior, not a kinetic rate; Tier-3 computational baseline.
_BETA_DECAY_PER_NM = 1.1


def redox_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    D_red, A_ox, D_ox, A_red = y
    dist_nm = float(params.get("distance_nm", 2.0))
    beta = float(params.get("beta_decay", _BETA_DECAY_PER_NM))
    # Accept profile alias k_et as k_max for relative ranking priors
    k_max = resolve_param(_MECHANISM, "k_et", params)
    k_leak = resolve_param(_MECHANISM, "k_leak", params)

    k_ET = k_max * np.exp(-beta * (dist_nm - 0.5))
    d_transfer = k_ET * D_red * A_ox
    # Optional non-productive leak of reduced donor (relative ranking term)
    d_leak = k_leak * D_red

    return [-d_transfer - d_leak, -d_transfer, d_transfer, d_transfer]


def simulate_redox_transfer(
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
    t, y = solve_mechanism_ode(redox_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[2], "P": y[3]}
