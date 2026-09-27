"""Gaussian-chain effective concentration.

σ² below is the mean-square end-to-end length <R²> = N b², not Nb²/3.

C_eff(r) = (3 / (2 π σ²))^(3/2) exp(-3 r² / (2 σ²))

This is polymer physics, not a Gaussian process.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from origami.priors import LINKER_SIGMA_A

_AVOGADRO = 6.02214076e23
_M_FROM_PER_A3 = 1e27 / _AVOGADRO


@dataclass(frozen=True)
class EffectiveConcentration:
    r_A: float
    sigma_A: float
    C_eff_per_A3: float
    C_eff_M: float
    provenance: str = "literature_placeholder"


def gaussian_chain_ceff(
    r_A: float,
    sigma_A: float | None = None,
) -> EffectiveConcentration:
    sig = LINKER_SIGMA_A.value if sigma_A is None else sigma_A
    if sig <= 0:
        raise ValueError("linker sigma must be positive")
    pre = (3.0 / (2.0 * np.pi * sig**2)) ** 1.5
    ceff_per_A3 = float(pre * np.exp(-3.0 * r_A**2 / (2.0 * sig**2)))
    return EffectiveConcentration(
        r_A=float(r_A),
        sigma_A=float(sig),
        C_eff_per_A3=ceff_per_A3,
        C_eff_M=ceff_per_A3 * _M_FROM_PER_A3,
    )


def gaussian_chain_ceff_M(r_A: float, sigma_A: float | None = None) -> float:
    return gaussian_chain_ceff(r_A, sigma_A).C_eff_M
