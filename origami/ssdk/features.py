"""Structured feature rows for SSDK multi-fidelity Gaussian processes.

NEK here is Euclidean distance in engineered descriptors (no ESM-2 in the
default path). Sequence encoding stays in ``src.gp_model.sequence_encoding``
for construct-level models later.
"""

from __future__ import annotations

import numpy as np

from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report

FEATURE_NAMES = (
    "n_repeats_scaled",
    "physics_score",
    "p_instability",
    "contour_nm_scaled",
    "axial_span_A_scaled",
    "scaffold_radius_A_scaled",
    "dist_m13_spy_A_scaled",
    "dist_m13_lgbit_A_scaled",
    "dist_spy_lgbit_A_scaled",
    "linker_rms_A_scaled",
    "cam_on_scaffold",
    "m13_on_scaffold",
)


def module_indices(n_repeats: int) -> tuple[int, int, int]:
    """Default placement: M13 at the first repeat, SpyCatcher mid, LgBiT at the last."""
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    return 0, n_repeats // 2, n_repeats - 1


def module_distances_A(n_repeats: int) -> tuple[float, float, float]:
    """Cα-site distances (Å) between the three default module indices."""
    geom = build_ctpr(n_repeats)
    i_m, i_s, i_l = module_indices(n_repeats)

    def _d(i: int, j: int) -> float:
        return float(np.linalg.norm(geom.sites[i].xyz_A - geom.sites[j].xyz_A))

    return _d(i_m, i_s), _d(i_m, i_l), _d(i_s, i_l)


def ssdk_feature_vector(
    n_repeats: int,
    physics_score: float,
    p_instability: float,
    n_max: int,
    *,
    linker_rms_A: float = 0.0,
    cam_on_scaffold: float = 1.0,
    m13_on_scaffold: float = 0.0,
) -> np.ndarray:
    """One row per scaffold length. Distances are Å/100. Flags are 0 or 1."""
    report = structural_report(build_ctpr(n_repeats))
    d_ms, d_ml, d_sl = module_distances_A(n_repeats)
    scale = float(max(n_max, 1))
    return np.array(
        [
            n_repeats / scale,
            float(physics_score),
            float(p_instability),
            report.contour_nm / 10.0,
            report.axial_span_A / 100.0,
            report.scaffold_radius_A / 100.0,
            d_ms / 100.0,
            d_ml / 100.0,
            d_sl / 100.0,
            float(linker_rms_A) / 100.0,
            float(cam_on_scaffold),
            float(m13_on_scaffold),
        ],
        dtype=float,
    )
