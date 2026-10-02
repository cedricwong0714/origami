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
)


def ssdk_feature_vector(
    n_repeats: int,
    physics_score: float,
    p_instability: float,
    n_max: int,
) -> np.ndarray:
    """One row per scaffold length (length 5). Values are not z-scored globally."""
    report = structural_report(build_ctpr(n_repeats))
    scale = float(max(n_max, 1))
    return np.array(
        [
            n_repeats / scale,
            float(physics_score),
            float(p_instability),
            report.contour_nm / 10.0,
            report.axial_span_A / 100.0,
        ],
        dtype=float,
    )
