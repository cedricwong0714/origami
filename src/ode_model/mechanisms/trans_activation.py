"""Trans-activation / phosphorylation-transfer ODE — canonical implementation.

Models proximity-induced trans-autophosphorylation:
- Basal monomeric autophosphorylation (slow, 3D diffusion)
- Scaffolded trans-phosphorylation (fast, driven by C_eff)
- Competitive dephosphorylation flux from soluble phosphatase

All rate constants are Tier-3 computational placeholders until
literature-calibrated values are deposited in models/kinetic_models/.
"""

from __future__ import annotations

import numpy as np

from src.ode_model.base_solver import solve_mechanism_ode


def trans_activation_derivatives(t: float, y: list[float], params: dict) -> list[float]:
    """
    y = [Substrate, Kinase, ProximityComplex, PhosphorylatedProduct]

    Mapping matches the ORIGAMI solver convention:
        S  -> substrate / target (acceptor)
        E  -> kinase (donor)
        ES -> scaffolded proximity complex
        P  -> phosphorylated product
    """
    S, K, KS, Sp = y

    # Tier-3 computational defaults (no claimed biological provenance)
    k_cat_basal = params.get("k_cat_basal", 0.05)      # monomeric background
    k_cat_trans = params.get("k_cat_trans", 1.0)       # proximity-induced
    # C_eff (mM) from linker ensemble drives assembly into proximity complex
    c_eff_mM = params.get("c_eff_mM", 1.0)
    k_on_prox = params.get("k_on_prox", c_eff_mM)
    k_dephos = params.get("k_dephos", 0.1)             # dephosphorylation
    phosphatase = params.get("phosphatase_uM", 0.1)   # soluble phosphatase

    # K is a catalyst: basal phosphorylation consumes S -> Sp, K unchanged.
    # Assembly sequesters K + S into the proximity complex KS.
    # Trans releases K and phosphorylates the substrate (KS -> K + Sp).
    # Dephosphorylation converts Sp back to S (phosphatase is a catalyst).
    d_basal = k_cat_basal * K * S
    d_assembly = k_on_prox * K * S
    d_trans = k_cat_trans * KS
    d_dephos = k_dephos * Sp * phosphatase

    dS_dt = -d_basal - d_assembly + d_dephos
    dK_dt = -d_assembly + d_trans
    dKS_dt = d_assembly - d_trans
    dSp_dt = d_basal + d_trans - d_dephos

    return [dS_dt, dK_dt, dKS_dt, dSp_dt]


def simulate_trans_activation(
    initial_concs: dict,
    params: dict | None = None,
    time_span: tuple[float, float] = (0.0, 100.0),
    num_points: int = 100,
):
    params = params or {}
    y0 = [
        initial_concs.get("S", 1.0),  # substrate
        initial_concs.get("E", 0.1),  # kinase
        0.0,                         # proximity complex
        0.0,                         # phosphorylated product
    ]
    t, y = solve_mechanism_ode(trans_activation_derivatives, y0, params, time_span, num_points)
    return t, {"S": y[0], "E": y[1], "ES": y[2], "P": y[3]}
