"""
Learn Mode — upload results, update model, recommend next experiment.

Compares mechanistic ODE baseline with observations via the GP correction
layer and returns acquisition-ranked follow-ups.
"""

from __future__ import annotations

from typing import Any, Literal, Optional, Sequence

import numpy as np

from src.core.schema import DesignSpec
from src.experiment_design.generator import ExperimentGenerator
from src.gp_model.predictor import predict_augmented_kinetics
from src.gp_model.trainer import GPCorrectionModel
from src.ode_model.solver import run_system_simulation
from src.profiles import get_profile


def _ode_product_on_grid(
    *,
    initial: dict[str, float],
    mechanism_type: Any,
    experimental_time: Optional[np.ndarray],
    time_span: tuple[float, float],
    n_obs: int,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Evaluate mechanistic product on the observation time grid.

    When experimental times are supplied, integrate on a denser linspace
    and interpolate onto those times so residuals are pointwise honest.
    """
    if experimental_time is not None:
        t_obs = np.asarray(experimental_time, dtype=float)
        if t_obs.ndim != 1 or len(t_obs) != n_obs:
            raise ValueError("experimental_time must be 1-D and match experimental_product length")
        if np.any(np.diff(t_obs) <= 0):
            raise ValueError("experimental_time must be strictly increasing")
        span = (float(t_obs[0]), float(t_obs[-1]))
        dense_n = max(200, n_obs * 5)
        t_dense, concs = run_system_simulation(
            initial,
            time_span=span,
            mechanism_type=mechanism_type,
            num_points=dense_n,
        )
        ode_product = np.interp(t_obs, t_dense, concs["P"])
        return t_obs, ode_product

    t, concs = run_system_simulation(
        initial,
        time_span=time_span,
        mechanism_type=mechanism_type,
        num_points=n_obs,
    )
    return t, concs["P"]


class LearnMode:
    def run(
        self,
        spec: DesignSpec,
        experimental_product: np.ndarray,
        time_span: tuple[float, float] = (0.0, 100.0),
        experimental_time: Optional[Sequence[float]] = None,
        initial_concentrations: Optional[dict[str, float]] = None,
        strategy: Literal["UCB", "EI", "information_gain"] = "UCB",
        top_k: int = 3,
        data_class: Optional[str] = None,
        package_warnings: Optional[list[str]] = None,
    ) -> dict[str, Any]:
        if experimental_product is None or len(experimental_product) < 2:
            return {
                "status": "REJECTED",
                "errors": ["Learn Mode requires an experimental product time series (≥2 points)."],
            }

        profile = get_profile(spec.mechanism_type)
        initial = initial_concentrations or {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0}
        n = len(experimental_product)
        exp = np.asarray(experimental_product, dtype=float)
        t_obs = None if experimental_time is None else np.asarray(experimental_time, dtype=float)

        try:
            t, ode_product = _ode_product_on_grid(
                initial=initial,
                mechanism_type=spec.mechanism_type,
                experimental_time=t_obs,
                time_span=time_span,
                n_obs=n,
            )
        except ValueError as exc:
            return {"status": "REJECTED", "errors": [str(exc)]}

        gp = GPCorrectionModel()
        gp.fit(t, ode_product, exp)
        augmented = predict_augmented_kinetics(t, ode_product, gp)

        residual = exp - ode_product
        rmse = float(np.sqrt(np.mean(residual ** 2)))
        max_abs_err = float(np.max(np.abs(residual)))

        if strategy == "information_gain":
            from src.experiment_design.bayesian_selector import BayesianExperimentSelector
            from src.gp_model.residual_gp import ResidualGP

            # Fit Matérn ResidualGP on the same residual surface for EIG
            residual_gp = ResidualGP()
            X = t.reshape(-1, 1)
            residual_gp.fit(X, exp, ode_product)
            selector = BayesianExperimentSelector(residual_gp)
            eig_recs = selector.recommend(
                X,
                ode_product,
                objective="information_gain",
                n_recommendations=top_k,
            )
            recommendations = [
                {
                    "time_point": float(r.features[0]),
                    "predicted_mean": r.predicted_mean,
                    "uncertainty_std": r.uncertainty_std,
                    "acquisition_score": r.acquisition_score,
                    "objective": r.objective,
                }
                for r in eig_recs
            ]
        else:
            generator = ExperimentGenerator(gp)
            recommendations = generator.suggest_next_experiments(
                candidate_time_points=t,
                candidate_ode_baseline=ode_product,
                top_k=top_k,
                strategy=strategy,
                current_best=float(np.max(exp)),
            )

        honesty = (
            "Positive residual means observation exceeded mechanistic baseline; "
            "GP correction captures the discrepancy with uncertainty. "
            "Next-experiment suggestions are proposals, not orders."
        )
        if data_class == "synthetic_fixture":
            honesty += " Input data_class=synthetic_fixture — not Tier-1 experimental."

        # Phenomenological A,k fit + FIM identifiability (Docs §1.5 / AGENTS §6.4).
        # Not a claim that A,k are mechanistic CLASP constants.
        identifiability: dict[str, Any] | None = None
        try:
            from src.calibration.fit import fit_model_with_identifiability_check

            def _exp_model(theta: np.ndarray, conditions: np.ndarray) -> np.ndarray:
                amp, rate = float(theta[0]), float(theta[1])
                tt = conditions[:, 0]
                return amp * (1.0 - np.exp(-rate * tt))

            cond = t.reshape(-1, 1)
            amp0 = float(max(np.max(exp), 1e-6))
            rate0 = 0.05
            fit = fit_model_with_identifiability_check(
                _exp_model,
                ["amplitude", "rate"],
                np.asarray([amp0, rate0], dtype=float),
                cond,
                exp,
                bounds=(
                    np.asarray([1e-9, 1e-6], dtype=float),
                    np.asarray([amp0 * 5.0, 5.0], dtype=float),
                ),
                noise_variance=max(rmse**2, 1e-12),
            )
            identifiability = {
                "model": "phenomenological_exponential_A_1_minus_exp_kt",
                "fitted_values": fit.fitted_values,
                "uncertainties": fit.uncertainties,
                "non_identifiable_parameters": fit.non_identifiable_parameters,
                "all_identifiable": len(fit.non_identifiable_parameters) == 0,
                "rmse": fit.rmse,
                "success": fit.success,
                "note": (
                    "Phenomenological A,k fit for Fisher/CRLB reporting only — "
                    "not mechanistic CLASP kinetic constants. Non-identifiable "
                    "parameters must not be presented as fitted values."
                ),
            }
        except Exception as exc:
            identifiability = {
                "model": "phenomenological_exponential_A_1_minus_exp_kt",
                "success": False,
                "error": str(exc),
                "note": "Identifiability report unavailable for this dataset.",
            }

        return {
            "status": "SUCCESS",
            "profile_id": profile.profile_id,
            "evidence_maturity": profile.assign_evidence_level(
                spec, has_experimental_data=True
            ).value,
            "data_class": data_class,
            "package_warnings": list(package_warnings or []),
            "time_points": t,
            "ode_baseline_product": ode_product,
            "experimental_product": exp,
            "augmented_kinetics": augmented,
            "comparison": {
                "rmse": rmse,
                "max_abs_error": max_abs_err,
                "n_points": n,
                "note": honesty,
            },
            "identifiability": identifiability,
            "next_experiment_recommendations": recommendations,
            "required_controls": profile.required_controls(spec).model_dump(),
        }


def learn(
    spec: DesignSpec,
    experimental_product: np.ndarray,
    **kwargs: Any,
) -> dict[str, Any]:
    return LearnMode().run(spec, experimental_product, **kwargs)
