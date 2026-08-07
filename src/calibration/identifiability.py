"""Identifiability reporting (AGENTS.md §6.4).

Thin public API over the Fisher Information machinery in
``src/calibration/fisher.py`` so callers can request an identifiability
report by name without wiring FIM details themselves.
"""

from __future__ import annotations

from typing import Callable

import numpy as np
from pydantic import BaseModel, Field

from src.calibration.fisher import FisherInformationDesigner


class IdentifiabilityReport(BaseModel):
    parameter_names: list[str]
    crlb_std: list[float]
    d_optimality: float
    non_identifiable_parameters: list[str] = Field(default_factory=list)
    all_identifiable: bool


def identifiability_report(
    model_func: Callable[[np.ndarray, np.ndarray], np.ndarray],
    parameters: list[str],
    theta: np.ndarray,
    experimental_conditions: np.ndarray,
    noise_variance: float = 1.0,
    threshold_rel: float = 1.0,
) -> IdentifiabilityReport:
    """
    Compute a FIM-based identifiability report at ``theta`` for the given
    experimental conditions. Non-identifiable parameters (CRLB std above
    ``threshold_rel * |theta|`` or non-finite) are named explicitly and must
    not be presented as fitted values.
    """
    designer = FisherInformationDesigner(
        model_func, parameters, noise_variance=noise_variance
    )
    raw = designer.identifiability_report(
        np.asarray(theta, dtype=float),
        experimental_conditions,
        threshold_rel=threshold_rel,
    )
    non_id = list(raw["non_identifiable_parameters"])
    return IdentifiabilityReport(
        parameter_names=list(raw["parameter_names"]),
        crlb_std=[float(x) for x in raw["crlb_std"]],
        d_optimality=float(raw["d_optimality"]),
        non_identifiable_parameters=non_id,
        all_identifiable=len(non_id) == 0,
    )
