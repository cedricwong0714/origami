"""Proximity-dependent protease–substrate cleavage ODE.

Models scaffolded recruitment of a protease to a cleavage target
(CLASP Docs §8):

    P + T  --recruitment-->  P:T  -->  P + T_cleaved

All rate constants are Tier-3 computational placeholders until
literature-calibrated values are deposited in models/kinetic_models/.
"""

from __future__ import annotations

from src.core.asset_paths import resolve_param
from src.ode_model.base_solver import solve_mechanism_ode

_MECHANISM = "protease_cleavage"


def protease_cleavage_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    """
    y = [Target, Protease, ProximityComplex, CleavedProduct]

    Mapping matches the ORIGAMI solver convention:
        S  -> uncleaved cleavage target
        E  -> protease effector
        ES -> scaffolded proximity complex
        P  -> cleaved product
    """
    S, E, ES, P = y

    k_cat_basal = resolve_param(_MECHANISM, "k_cat_basal", params)
    k_cat_prox = resolve_param(_MECHANISM, "k_cat_prox", params)
    k_on_prox = float(params.get("k_on_prox", params.get("c_eff_mM", 1.0)))
    k_nonspecific = resolve_param(_MECHANISM, "k_nonspecific", params)

    d_basal = k_cat_basal * E * S
    d_assembly = k_on_prox * E * S
    d_cleave = k_cat_prox * ES
    d_nonspecific = k_nonspecific * S

    dS_dt = -d_basal - d_assembly - d_nonspecific
    dE_dt = -d_assembly + d_cleave
    dES_dt = d_assembly - d_cleave
    dP_dt = d_basal + d_cleave + d_nonspecific

    return [dS_dt, dE_dt, dES_dt, dP_dt]


def simulate_protease_cleavage(
    initial_concs: dict,
    params: dict | None = None,
    time_span: tuple[float, float] = (0.0, 100.0),
    num_points: int = 100,
):
    params = params or {}
    y0 = [
        initial_concs.get("S", 1.0),
        initial_concs.get("E", 0.1),
        0.0,
        0.0,
    ]
    t, y = solve_mechanism_ode(protease_cleavage_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[2], "P": y[3]}
