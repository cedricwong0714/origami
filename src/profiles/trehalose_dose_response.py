"""
Ca²⁺ → trehalose functional dose–response (SCALE Stage L dual readout).

Couples existing CaM–M13 recruitment occupancy to the intermediate-transfer
ODE without inventing new kinetic constants:

  k_channel_eff = k_channel · f_occupancy(Ca²⁺)   (scaffolded)
  k_channel_eff = 0                               (free / unscaffolded control)

Fold-change = P_scaffold(Ca) / P_free(Ca) at matched endpoint time.

This is a Tier-3 / hypothesis_only computational baseline until Megazyme
dose–response calibrates the occupancy→channeling link.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from src.calibration.dose_response_metrics import fit_hill_dose_response
from src.core.calcium_kinetics import recruitment_occupancy
from src.core.schema import MechanismType
from src.ode_model.solver import run_system_simulation
from src.profiles.trehalose_synthesis import TrehaloseSynthesisProfile


def _endpoint_product(
    *,
    k_channel_eff: float,
    base_params: dict[str, float],
    initial: dict[str, float],
    time_span: tuple[float, float],
    num_points: int,
) -> float:
    params = {**base_params, "k_channel": float(k_channel_eff)}
    _t, concs = run_system_simulation(
        initial,
        time_span=time_span,
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        params=params,
        num_points=num_points,
    )
    return float(concs["P"][-1])


def predict_trehalose_ca_dose_response(
    calcium_M: Optional[np.ndarray] = None,
    *,
    params: Optional[dict[str, float]] = None,
    initial: Optional[dict[str, float]] = None,
    time_span: tuple[float, float] = (0.0, 100.0),
    num_points: int = 80,
    cam_total_M: float = 1e-6,
    m13_total_M: float = 1e-6,
) -> dict[str, Any]:
    """
    Sweep free Ca²⁺ and predict scaffolded vs free trehalose endpoint yield.

    Returns series plus Hill summary of the scaffolded curve and fold-change.
    """
    if calcium_M is None:
        # Match assembly dose-response window: 0.1–100 µM free Ca²⁺
        calcium_M = np.logspace(-7, -4, 41)
    ca = np.asarray(calcium_M, dtype=float).ravel()

    profile = TrehaloseSynthesisProfile()
    base = {**profile._params(), **(params or {})}
    k_channel_max = float(base.get("k_channel", 5.0))
    init = initial or {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0}

    occupancy: list[float] = []
    p_scaffold: list[float] = []
    p_free: list[float] = []
    fold: list[float] = []

    for c in ca:
        state = recruitment_occupancy(
            float(c),
            cam_total_M=cam_total_M,
            m13_total_M=m13_total_M,
        )
        f = float(state.occupancy_fraction)
        occupancy.append(f)
        ps = _endpoint_product(
            k_channel_eff=k_channel_max * f,
            base_params=base,
            initial=init,
            time_span=time_span,
            num_points=num_points,
        )
        pf = _endpoint_product(
            k_channel_eff=0.0,
            base_params=base,
            initial=init,
            time_span=time_span,
            num_points=num_points,
        )
        p_scaffold.append(ps)
        p_free.append(pf)
        fold.append(ps / pf if pf > 1e-15 else float("inf"))

    hill = fit_hill_dose_response(
        ca,
        np.asarray(p_scaffold, dtype=float),
        confidence_tier="hypothesis_only",
    )

    return {
        "calcium_M": [float(x) for x in ca],
        "calcium_uM_min": float(ca[0] * 1e6),
        "calcium_uM_max": float(ca[-1] * 1e6),
        "occupancy_fraction": occupancy,
        "trehalose_scaffold": p_scaffold,
        "trehalose_free": p_free,
        "fold_change": fold,
        "k_channel_max": k_channel_max,
        "params": base,
        "hill_fit_scaffold": hill.model_dump(),
        "unit": "dimensionless_yield_fraction",
        "confidence_tier": "hypothesis_only",
        "evidence_maturity": "Tier 3: Computational Baseline",
        "assumption": (
            "Effective k_channel scales linearly with CaM–M13 occupancy; "
            "free control sets k_channel=0 (bulk path only). "
            "Not calibrated to Megazyme data."
        ),
        "note": (
            "Predicted Ca²⁺→trehalose dose–response (scaffolded vs free). "
            "Literature-parameterized channeling priors + sourced CaM recruitment. "
            "Hypothesis-only until wet-lab fold-change calibrates the link."
        ),
    }
