"""Covalent Spy capture.

Two paths:

- Lumped irreversible bimolecular adduct (Zakeri 2012 apparent k_on).
- Reversible capture plus irreversible lock when all three rates are supplied.

This module does not read ``models/kinetic_models/covalent_capture.defaults.json``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.integrate import solve_ivp


@dataclass
class CovalentSimResult:
    time_s: np.ndarray
    tag_M: np.ndarray
    catcher_M: np.ndarray
    complex_M: np.ndarray
    adduct_M: np.ndarray
    units: str
    calibrated: bool
    confidence_tier: str
    human_review_required: bool
    assumptions: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "calibrated": self.calibrated,
            "confidence_tier": self.confidence_tier,
            "human_review_required": self.human_review_required,
            "units": {"concentration": self.units, "time": "s"},
            "assumptions": self.assumptions,
            "warnings": self.warnings,
            "time_s": [float(x) for x in self.time_s],
            "series": {
                "tag_M": [float(x) for x in self.tag_M],
                "catcher_M": [float(x) for x in self.catcher_M],
                "complex_M": [float(x) for x in self.complex_M],
                "adduct_M": [float(x) for x in self.adduct_M],
            },
        }


def _lumped_derivatives(
    _t: float,
    y: np.ndarray,
    k_on: float,
) -> np.ndarray:
    tag, catcher, _comp, _adduct = (float(v) for v in y)
    d_adduct = k_on * tag * catcher
    return np.array([-d_adduct, -d_adduct, 0.0, d_adduct])


def _derivatives(
    _t: float,
    y: np.ndarray,
    k_on: float,
    k_rev: float,
    k_bond: float,
) -> np.ndarray:
    tag, catcher, comp, adduct = (float(v) for v in y)
    d_bind = k_on * tag * catcher - k_rev * comp
    d_comp = d_bind - k_bond * comp
    d_adduct = k_bond * comp
    return np.array([-d_bind, -d_bind, d_comp, d_adduct])


def simulate_covalent_timecourse(
    *,
    tag0_M: float,
    catcher0_M: float,
    k_on_per_M_s: float,
    k_rev_per_s: float | None = None,
    k_bond_per_s: float | None = None,
    t_end_s: float = 100.0,
    num_points: int = 100,
) -> CovalentSimResult:
    for name, val in (
        ("tag0_M", tag0_M),
        ("catcher0_M", catcher0_M),
        ("k_on_per_M_s", k_on_per_M_s),
        ("t_end_s", t_end_s),
    ):
        if not isinstance(val, (int, float)) or isinstance(val, bool):
            raise TypeError(f"{name} must be a number")
        if float(val) < 0:
            raise ValueError(f"{name} must be >= 0")
    if k_on_per_M_s <= 0:
        raise ValueError("k_on must be strictly positive")
    lumped = k_rev_per_s is None and k_bond_per_s is None
    if not lumped:
        if k_rev_per_s is None or k_bond_per_s is None:
            raise ValueError("k_rev and k_bond must both be supplied, or both omitted")
        for name, val in (
            ("k_rev_per_s", k_rev_per_s),
            ("k_bond_per_s", k_bond_per_s),
        ):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise TypeError(f"{name} must be a number")
            if float(val) <= 0:
                raise ValueError("k_rev and k_bond must be strictly positive")
    if t_end_s <= 0:
        raise ValueError("t_end_s must be > 0")
    if num_points < 2:
        raise ValueError("num_points must be >= 2")

    t_eval = np.linspace(0.0, float(t_end_s), int(num_points))
    y0 = np.array([float(tag0_M), float(catcher0_M), 0.0, 0.0])
    if lumped:
        sol = solve_ivp(
            _lumped_derivatives,
            (0.0, float(t_end_s)),
            y0,
            args=(float(k_on_per_M_s),),
            t_eval=t_eval,
            rtol=1e-6,
            atol=1e-9,
        )
        assumptions = [
            "Lumped irreversible bimolecular adduct: d[adduct]/dt = k_on [Tag][Catcher].",
            "This matches Zakeri 2012 SDS-PAGE of covalent product, not a 3-step fit.",
        ]
    else:
        sol = solve_ivp(
            _derivatives,
            (0.0, float(t_end_s)),
            y0,
            args=(float(k_on_per_M_s), float(k_rev_per_s), float(k_bond_per_s)),
            t_eval=t_eval,
            rtol=1e-6,
            atol=1e-9,
        )
        assumptions = [
            "Well-mixed mass action for Tag, Catcher, reversible complex, and locked adduct.",
            "k_rev and k_bond were supplied explicitly (lab override or request body).",
        ]
    if not sol.success:
        raise RuntimeError(f"covalent ODE failed: {sol.message}")

    return CovalentSimResult(
        time_s=sol.t,
        tag_M=sol.y[0],
        catcher_M=sol.y[1],
        complex_M=sol.y[2],
        adduct_M=sol.y[3],
        units="M",
        calibrated=False,
        confidence_tier="hypothesis_only",
        human_review_required=True,
        assumptions=assumptions,
        warnings=[
            "Not calibrated to this team's wet-lab SpyTag time course.",
            "A passing integration test is not scientific validation.",
        ],
    )
