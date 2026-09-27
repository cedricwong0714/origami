"""
ORIGAMI Core: Calcium Kinetics Engine
Models Ca2+-dependent CaM-M13 binding kinetics.
Universal recruitment switch for all CLASP mechanism profiles.

Key Invariants (CLASP Docs):
- CaM-M13 Kd = 0.19e-9 M when Ca2+-saturated
  (Biochemistry 2006, 45(41):12547-12559, DOI 10.1021/bi060857u;
  same citation as origami.priors.CAM_M13_KD_M)
- Resting cytoplasmic [Ca2+] ≈ 100 nM
- Hill coefficient n ≈ 4 (four Ca2+ binding sites on CaM)
- EC50 for activation ≈ 1-5 µM free Ca2+
"""

from __future__ import annotations
import numpy as np
from pydantic import BaseModel, Field
from typing import Optional

# Parameter: CaM–M13 Kd at saturating Ca2+
# Value: 0.19e-9
# Units: M
# Source: Biochemistry 2006, 45(41):12547-12559, DOI 10.1021/bi060857u.
#   WT CaM + WT M13, fluorescence competition, Kd = 0.19 ± 0.09 nM.
#   Same citation already recorded on origami.priors.CAM_M13_KD_M.
# Notes: Peptide Kd. Not a CLASP fusion. Occupancy uses this value.
CAM_M13_KD_CA_SAT_M = 0.19e-9
# Hill n, EC50, and resting calcium (Ikura 1992; CLASP Docs §2.1). Unchanged.
CAM_CA_HILL_N = 4.0             # Cooperativity of Ca2+ binding to CaM
CAM_CA_EC50_M = 2e-6            # Free [Ca2+] for half-maximal CaM activation
RESTING_CA_M = 1e-7             # Basal cytoplasmic [Ca2+]


class RecruitmentState(BaseModel):
    free_ca2_M: float
    cam_activation_fraction: float = Field(..., ge=0, le=1)
    occupancy_fraction: float = Field(..., ge=0, le=1)
    is_assembled: bool
    assembly_regime: str  # "unbound", "partial", "saturated"


def cam_activation(ca2_free_M: float) -> float:
    """Fraction of CaM in open/Ca2+-bound conformation (Hill equation)."""
    if ca2_free_M <= 0:
        return 0.0
    return (ca2_free_M ** CAM_CA_HILL_N) / (
        ca2_free_M ** CAM_CA_HILL_N + CAM_CA_EC50_M ** CAM_CA_HILL_N
    )


def recruitment_occupancy(
    ca2_free_M: float,
    cam_total_M: float = 1e-6,
    m13_total_M: float = 1e-6,
    kd_modulation: float = 1.0
) -> RecruitmentState:
    """
    Compute fractional occupancy of M13 sites by CaM.
    
    Accounts for Ca2+-dependent activation AND bimolecular binding equilibrium.
    kd_modulation allows profile-specific tuning (e.g., mutant CaM variants).
    """
    f_active = cam_activation(ca2_free_M)
    effective_kd = CAM_M13_KD_CA_SAT_M * kd_modulation

    # Only activated CaM can bind M13
    cam_active_M = cam_total_M * f_active

    # Quadratic solution for bimolecular binding: [CM] = ...
    if cam_active_M < 1e-15 or m13_total_M < 1e-15:
        bound_M = 0.0
    else:
        a = 1.0
        b = -(cam_active_M + m13_total_M + effective_kd)
        c = cam_active_M * m13_total_M
        discriminant = b ** 2 - 4 * a * c
        bound_M = (-b - np.sqrt(max(0, discriminant))) / (2 * a)

    occupancy = bound_M / m13_total_M if m13_total_M > 0 else 0.0

    if occupancy < 0.05:
        regime = "unbound"
    elif occupancy < 0.8:
        regime = "partial"
    else:
        regime = "saturated"

    return RecruitmentState(
        free_ca2_M=ca2_free_M,
        cam_activation_fraction=float(f_active),
        occupancy_fraction=float(min(1.0, max(0.0, occupancy))),
        is_assembled=occupancy > 0.1,
        assembly_regime=regime
    )


def dose_response_curve(
    ca2_range_M: Optional[np.ndarray] = None,
    n_points: int = 50
) -> list[RecruitmentState]:
    """Generate full Ca2+ dose-response for visualization and fitting."""
    if ca2_range_M is None:
        ca2_range_M = np.logspace(-9, -4, n_points)
    return [recruitment_occupancy(float(ca)) for ca in ca2_range_M]