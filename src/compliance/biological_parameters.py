"""
Biological parameter discipline (AGENTS.md §4).

Every sourced constant used in predictions should be representable as
``BiologicalParameter``. Unsourced values must warn via ``get_parameter_or_warn``.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass
from typing import Optional

from src.core.calcium_kinetics import (
    CAM_CA_EC50_M,
    CAM_CA_HILL_N,
    CAM_M13_KD_CA_SAT_M,
    RESTING_CA_M,
)
from src.core.ctpr_geometry import (
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
    PERSISTENCE_LENGTH_NM,
)
from src.core.linker_ensemble import KUHNN_LENGTH_NM, RESIDUE_CONTOUR_NM
from src.core.nanobit_reporter import NANOBIT_INTRINSIC_KD_M, NANOBIT_MAX_DISTANCE_NM
from src.core.steric_checker import SCAFFOLD_CYLINDER_RADIUS_NM


@dataclass
class BiologicalParameter:
    name: str
    value: float
    units: str
    lower_bound: Optional[float]
    upper_bound: Optional[float]
    source: str
    system: str
    confidence: str  # high | medium | low
    notes: str = ""

    def is_within_range(self, test_value: float) -> bool:
        if self.lower_bound is None or self.upper_bound is None:
            return True
        return self.lower_bound <= test_value <= self.upper_bound

    def warn_if_extrapolating(self, test_value: float) -> None:
        if not self.is_within_range(test_value):
            warnings.warn(
                f"Value {test_value} {self.units} is outside the validated range "
                f"[{self.lower_bound}, {self.upper_bound}] {self.units} for "
                f"parameter '{self.name}'. Predictions using this value are extrapolations.",
                UserWarning,
                stacklevel=2,
            )


def get_parameter_or_warn(
    name: str,
    value: Optional[float],
    source: Optional[str],
) -> Optional[float]:
    """
    Return a biological parameter value if sourced, or warn and return None.
    Never silently use an unsourced biological constant in production paths.
    """
    if value is None or source is None:
        warnings.warn(
            f"Biological parameter '{name}' has no verified source. "
            f"This parameter must not be used in a production prediction or a "
            f"wet-lab decision. Find a peer-reviewed source before proceeding.",
            UserWarning,
            stacklevel=2,
        )
        return None
    return value


# Canonical ORIGAMI / CLASP priors (see CLASP Docs.md + module source comments)
ORIGAMI_PARAMETER_LIBRARY: dict[str, BiologicalParameter] = {
    "CTPR_RISE_NM": BiologicalParameter(
        name="CTPR rise per repeat",
        value=CTPR_RISE_NM,
        units="nm",
        lower_bound=1.0,
        upper_bound=1.2,
        source="Dueber 2009; SCABs 2024 (CLASP Docs §2)",
        system="CTPR scaffold repeat",
        confidence="high",
        notes="ORIGAMI invariant — do not tune for demos",
    ),
    "CTPR_TWIST_DEG": BiologicalParameter(
        name="CTPR twist per repeat",
        value=CTPR_TWIST_DEG,
        units="deg",
        lower_bound=18.0,
        upper_bound=22.0,
        source="Dueber 2009; SCABs 2024 (CLASP Docs §2)",
        system="CTPR scaffold repeat",
        confidence="high",
    ),
    "PERSISTENCE_LENGTH_NM": BiologicalParameter(
        name="CTPR persistence length (short scaffolds)",
        value=PERSISTENCE_LENGTH_NM,
        units="nm",
        lower_bound=10.0,
        upper_bound=20.0,
        source="CLASP Docs §2; rigid-rod approx. for N<14",
        system="CTPR scaffold",
        confidence="medium",
    ),
    "SCAFFOLD_CYLINDER_RADIUS_NM": BiologicalParameter(
        name="Scaffold cylinder radius",
        value=SCAFFOLD_CYLINDER_RADIUS_NM,
        units="nm",
        lower_bound=1.5,
        upper_bound=2.0,
        source="CLASP Docs §2.4; steric_checker",
        system="CTPR backbone cylinder",
        confidence="medium",
    ),
    "DOCKING_LOOP_OFFSET_NM": BiologicalParameter(
        name="Docking loop radial offset",
        value=DOCKING_LOOP_OFFSET_NM,
        units="nm",
        lower_bound=0.2,
        upper_bound=0.5,
        source="CLASP Docs geometry model",
        system="CTPR docking loop",
        confidence="medium",
    ),
    "CAM_M13_KD_CA_SAT_M": BiologicalParameter(
        name="CaM–M13 Kd (Ca²⁺ saturated)",
        value=CAM_M13_KD_CA_SAT_M,
        units="M",
        lower_bound=5e-8,
        upper_bound=5e-7,
        source="Ikura 1992; CLASP Docs §2.1",
        system="CaM + M13 peptide",
        confidence="high",
    ),
    "CAM_CA_EC50_M": BiologicalParameter(
        name="CaM–Ca²⁺ EC50",
        value=CAM_CA_EC50_M,
        units="M",
        lower_bound=1e-6,
        upper_bound=5e-6,
        source="Ikura 1992; CLASP Docs §2.1",
        system="CaM Ca²⁺ binding",
        confidence="high",
    ),
    "CAM_CA_HILL_N": BiologicalParameter(
        name="CaM–Ca²⁺ Hill n",
        value=CAM_CA_HILL_N,
        units="dimensionless",
        lower_bound=3.0,
        upper_bound=5.0,
        source="Ikura 1992; CLASP Docs §2.1",
        system="CaM Ca²⁺ binding",
        confidence="medium",
    ),
    "RESTING_CA_M": BiologicalParameter(
        name="Resting cytoplasmic Ca²⁺",
        value=RESTING_CA_M,
        units="M",
        lower_bound=5e-8,
        upper_bound=2e-7,
        source="CLASP Docs §2.1",
        system="E. coli cytosol (approx.)",
        confidence="medium",
    ),
    "NANOBIT_MAX_DISTANCE_NM": BiologicalParameter(
        name="NanoBiT reconstitution distance",
        value=NANOBIT_MAX_DISTANCE_NM,
        units="nm",
        lower_bound=2.0,
        upper_bound=3.5,
        source="NanoBiT literature; CLASP Docs §2.3",
        system="split luciferase complementation",
        confidence="high",
    ),
    "NANOBIT_KD_M": BiologicalParameter(
        name="NanoBiT intrinsic Kd",
        value=NANOBIT_INTRINSIC_KD_M,
        units="M",
        lower_bound=1e-4,
        upper_bound=5e-4,
        source="NanoBiT literature; CLASP Docs §2.3",
        system="split luciferase fragments",
        confidence="medium",
    ),
    "GGGGS_CONTOUR_NM": BiologicalParameter(
        name="(GGGGS)n contour per residue",
        value=RESIDUE_CONTOUR_NM,
        units="nm/residue",
        lower_bound=0.3,
        upper_bound=0.4,
        source="CLASP Docs linker ensemble",
        system="(GGGGS)n linker",
        confidence="medium",
    ),
    "GGGGS_KUHN_NM": BiologicalParameter(
        name="(GGGGS)n Kuhn length",
        value=KUHNN_LENGTH_NM,
        units="nm",
        lower_bound=0.5,
        upper_bound=0.9,
        source="CLASP Docs linker ensemble",
        system="(GGGGS)n linker",
        confidence="medium",
    ),
}
