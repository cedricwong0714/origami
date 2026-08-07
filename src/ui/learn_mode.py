"""
Learn Mode — upload results, update model, recommend next experiment.

Compares mechanistic ODE baseline with observations via the GP correction
layer and returns acquisition-ranked follow-ups.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

import numpy as np

from src.core.schema import DesignSpec
from src.experiment_design.generator import ExperimentGenerator
from src.gp_model.predictor import predict_augmented_kinetics
from src.gp_model.trainer import GPCorrectionModel
from src.ode_model.solver import run_system_simulation
from src.profiles import get_profile


class LearnMode:
    def run(
        self,
        spec: DesignSpec,
        experimental_product: np.ndarray,
        time_span: tuple[float, float] = (0.0, 100.0),
        initial_concentrations: Optional[dict[str, float]] = None,
        strategy: Literal["UCB", "EI"] = "UCB",
        top_k: int = 3,
    ) -> dict[str, Any]:
        if experimental_product is None or len(experimental_product) < 2:
            return {
                "status": "REJECTED",
                "errors": ["Learn Mode requires an experimental product time series (≥2 points)."],
            }

        profile = get_profile(spec.mechanism_type)
        initial = initial_concentrations or {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0}
        n = len(experimental_product)

        t, concs = run_system_simulation(
            initial,
            time_span=time_span,
            mechanism_type=spec.mechanism_type,
            num_points=n,
        )
        ode_product = concs["P"]

        gp = GPCorrectionModel()
        gp.fit(t, ode_product, experimental_product)
        augmented = predict_augmented_kinetics(t, ode_product, gp)

        residual = experimental_product - ode_product
        rmse = float(np.sqrt(np.mean(residual ** 2)))
        max_abs_err = float(np.max(np.abs(residual)))

        generator = ExperimentGenerator(gp)
        recommendations = generator.suggest_next_experiments(
            candidate_time_points=t,
            candidate_ode_baseline=ode_product,
            top_k=top_k,
            strategy=strategy,
            current_best=float(np.max(experimental_product)),
        )

        return {
            "status": "SUCCESS",
            "profile_id": profile.profile_id,
            "evidence_maturity": profile.assign_evidence_level(
                spec, has_experimental_data=True
            ).value,
            "time_points": t,
            "ode_baseline_product": ode_product,
            "experimental_product": experimental_product,
            "augmented_kinetics": augmented,
            "comparison": {
                "rmse": rmse,
                "max_abs_error": max_abs_err,
                "n_points": n,
                "note": (
                    "Positive residual means observation exceeded mechanistic baseline; "
                    "GP correction captures the discrepancy with uncertainty."
                ),
            },
            "next_experiment_recommendations": recommendations,
            "required_controls": profile.required_controls(spec).model_dump(),
        }


def learn(
    spec: DesignSpec,
    experimental_product: np.ndarray,
    **kwargs: Any,
) -> dict[str, Any]:
    return LearnMode().run(spec, experimental_product, **kwargs)
