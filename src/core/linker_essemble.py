"""
ORIGAMI Core: Linker Ensemble & Effective Concentration Engine
Models flexible linker reach using Gaussian chain approximation (MVP).
Calculates effective local concentration (C_eff) for proximity-dependent binding.

Key Invariants (CLASP Docs):
- (GGGGS)n contour length: ~0.36 nm/residue
- Kuhn length for GGGGS: ~0.7 nm
- C_eff drives NanoBiT complementation and SpyTag/Catcher reaction rates
"""

from __future__ import annotations
import numpy as np
from pydantic import BaseModel, Field
from typing import Optional

KUHNN_LENGTH_NM = 0.7       # Kuhn length for (GGGGS)n linkers
RESIDUE_CONTOUR_NM = 0.36   # Contour length per residue
AVOGADRO = 6.022e23


class LinkerSpec(BaseModel):
    sequence: str = "(GGGGS)3"
    n_residues: int = Field(..., ge=1)
    contour_length_nm: float = Field(..., gt=0)
    kuhn_length_nm: float = KUHNN_LENGTH_NM


class ReachResult(BaseModel):
    c_eff_mM: float = Field(..., description="Effective local concentration in mM")
    reach_probability: float = Field(..., ge=0, le=1)
    rms_end_to_end_nm: float = Field(..., gt=0)
    is_reachable: bool


def parse_linker(sequence: str) -> LinkerSpec:
    """Parse (GGGGS)n notation into physical parameters."""
    seq = sequence.strip()
    if seq.startswith("(GGGGS)") and seq.endswith(")"):
        try:
            n = int(seq[7:-1])
        except ValueError:
            n = 3
    else:
        n = max(1, len(seq) // 5)

    n_residues = n * 5
    contour = n_residues * RESIDUE_CONTOUR_NM
    return LinkerSpec(sequence=seq, n_residues=n_residues, contour_length_nm=contour)


def compute_effective_concentration(
    linker: LinkerSpec,
    anchor_distance_nm: float,
    capture_radius_nm: float = 1.0
) -> ReachResult:
    """
    Compute C_eff using Gaussian chain model.
    
    C_eff = (3/(2π⟨r²⟩))^(3/2) × exp(-3d²/(2⟨r²⟩)) × V_capture
    Converted to mM for direct comparison with Kd values.
    """
    n_kuhn = linker.contour_length_nm / linker.kuhn_length_nm
    if n_kuhn < 1:
        n_kuhn = 1.0

    mean_sq_end_to_end = n_kuhn * linker.kuhn_length_nm ** 2
    rms = np.sqrt(mean_sq_end_to_end)

    # Gaussian probability density at distance d
    prefactor = (3.0 / (2.0 * np.pi * mean_sq_end_to_end)) ** 1.5
    exponent = np.exp(-3.0 * anchor_distance_nm ** 2 / (2.0 * mean_sq_end_to_end))
    prob_density_nm3 = prefactor * exponent

    # Capture volume (sphere of radius capture_radius)
    v_capture_nm3 = (4.0 / 3.0) * np.pi * capture_radius_nm ** 3

    # Convert to molar concentration
    c_eff_M = prob_density_nm3 * v_capture_nm3 / AVOGADRO * 1e27  # nm³ → L
    c_eff_mM = c_eff_M * 1000.0

    # Reach probability: fraction of ensemble within capture radius
    # Approximated as CDF of Maxwell-Boltzmann distribution
    x = capture_radius_nm / rms
    reach_prob = float(1.0 - np.exp(-1.5 * x ** 2) * (1.0 + 1.5 * x ** 2))

    return ReachResult(
        c_eff_mM=float(c_eff_mM),
        reach_probability=min(1.0, max(0.0, reach_prob)),
        rms_end_to_end_nm=float(rms),
        is_reachable=reach_prob > 0.01
    )