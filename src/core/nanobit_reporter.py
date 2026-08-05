"""
ORIGAMI Core: NanoBiT Reporter Engine
Models split-NanoLuc (LgBiT-SmBiT) complementation.
Enforces distance rules and predicts luminescence output.

Key Invariants (CLASP Docs):
- Reconstitution distance: ≤ 3.0 nm (30 Å)
- Intrinsic Kd ≈ 190 µM (weak alone, strong when tethered)
- Luminescence ∝ assembled complex concentration
- Background from unbound fragments must be subtracted
"""

from __future__ import annotations
import numpy as np
from pydantic import BaseModel, Field
from .linker_ensemble import ReachResult

NANOBIT_MAX_DISTANCE_NM = 3.0
NANOBIT_INTRINSIC_KD_M = 190e-6   # 190 µM
NANOBIT_BACKGROUND_FRACTION = 0.005  # ~0.5% spontaneous complementation


class NanoBiTSignal(BaseModel):
    predicted_rlU: float = Field(..., ge=0)
    assembly_efficiency: float = Field(..., ge=0, le=1)
    signal_to_background: float = Field(..., ge=0)
    is_complemented: bool
    distance_nm: float
    warning: str = ""


def predict_nanobit_signal(
    reach_result: ReachResult,
    occupancy_fraction: float,
    max_rlU: float = 1e6,
    background_rlU: float = 100.0
) -> NanoBiTSignal:
    """
    Predict NanoBiT luminescence from physical parameters.
    
    Args:
        reach_result: Output from linker_ensemble.compute_effective_concentration
        occupancy_fraction: Fraction of scaffolds with recruited payload (from calcium_kinetics)
        max_rlU: Maximum luminescence at 100% assembly
        background_rlU: Baseline luminescence without assembly
    """
    distance_warning = ""

    # Check hard distance constraint
    if reach_result.rms_end_to_end_nm > NANOBIT_MAX_DISTANCE_NM * 2:
        distance_warning = (
            f"RMS end-to-end distance ({reach_result.rms_end_to_end_nm:.1f} nm) "
            f"exceeds 2× complementation limit ({NANOBIT_MAX_DISTANCE_NM} nm). "
            f"Signal likely negligible."
        )

    # Effective complementation probability combines reach AND occupancy
    # When tethered, C_eff >> Kd, so complementation ≈ reach_probability
    # When untethered, complementation ≈ background
    tethered_signal = reach_result.reach_probability * reach_result.c_eff_mM / (
        reach_result.c_eff_mM + NANOBIT_INTRINSIC_KD_M * 1000  # convert to mM
    )

    # Weight by recruitment occupancy
    assembly_eff = float(occupancy_fraction * tethered_signal +
                         (1 - occupancy_fraction) * NANOBIT_BACKGROUND_FRACTION)

    predicted = background_rlU + (max_rlU - background_rlU) * assembly_eff
    stb = predicted / background_rlU if background_rlU > 0 else float('inf')

    return NanoBiTSignal(
        predicted_rlU=float(predicted),
        assembly_efficiency=float(min(1.0, assembly_eff)),
        signal_to_background=float(stb),
        is_complemented=stb > 10.0 and reach_result.is_reachable,
        distance_nm=reach_result.rms_end_to_end_nm,
        warning=distance_warning
    )


def check_nanobit_compatibility(distance_nm: float) -> bool:
    """Quick boolean check for NanoBiT geometric feasibility."""
    return distance_nm <= NANOBIT_MAX_DISTANCE_NM