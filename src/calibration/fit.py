"""Bounded least-squares calibration of CLASP assembly parameters (Docs §1.5)."""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np
from pydantic import BaseModel, Field
from scipy.optimize import least_squares

from src.calibration.fisher import FisherInformationDesigner


class FitResult(BaseModel):
    fitted_values: dict[str, float]
    uncertainties: dict[str, float]
    non_identifiable_parameters: list[str] = Field(default_factory=list)
    data_points_used: int
    degrees_of_freedom: int
    rmse: float
    success: bool
    message: str = ""


def fit_model_with_identifiability_check(
    model_func: Callable[[np.ndarray, np.ndarray], np.ndarray],
    parameters: list[str],
    theta0: np.ndarray,
    conditions: np.ndarray,
    observations: np.ndarray,
    bounds: Optional[tuple[np.ndarray, np.ndarray]] = None,
    noise_variance: float = 1.0,
    identifiability_rel_threshold: float = 1.0,
) -> FitResult:
    """
    Fit model_func(theta, conditions) -> y to observations with bounded LS,
    then report Cramér–Rao / FIM-based identifiability (AGENTS.md §6.4).
    """
    theta0 = np.asarray(theta0, dtype=float)
    conditions = np.asarray(conditions, dtype=float)
    observations = np.asarray(observations, dtype=float)
    if conditions.ndim == 1:
        conditions = conditions.reshape(-1, 1)

    def residual(theta: np.ndarray) -> np.ndarray:
        return model_func(theta, conditions) - observations

    ls_bounds = bounds if bounds is not None else (
        np.full_like(theta0, -np.inf),
        np.full_like(theta0, np.inf),
    )
    result = least_squares(residual, theta0, bounds=ls_bounds, method="trf")
    theta_hat = result.x
    y_hat = model_func(theta_hat, conditions)
    rmse = float(np.sqrt(np.mean((y_hat - observations) ** 2)))

    designer = FisherInformationDesigner(model_func, parameters, noise_variance=noise_variance)
    report = designer.identifiability_report(
        theta_hat, conditions, threshold_rel=identifiability_rel_threshold
    )
    crlb = report["crlb_std"]

    fitted = {name: float(v) for name, v in zip(parameters, theta_hat)}
    uncertainties = {
        name: float(std) if np.isfinite(std) else float("inf")
        for name, std in zip(parameters, crlb)
    }
    # Never present non-identifiable params as confident fitted values
    for name in report["non_identifiable_parameters"]:
        uncertainties[name] = float("inf")

    return FitResult(
        fitted_values=fitted,
        uncertainties=uncertainties,
        non_identifiable_parameters=list(report["non_identifiable_parameters"]),
        data_points_used=len(observations),
        degrees_of_freedom=max(0, len(observations) - len(parameters)),
        rmse=rmse,
        success=bool(result.success),
        message=str(result.message),
    )
