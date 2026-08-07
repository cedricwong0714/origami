"""Bayesian experiment selection: EI and Expected Information Gain (Docs-6 §3)."""

from __future__ import annotations

from typing import Literal, Optional

import numpy as np
from pydantic import BaseModel, Field
from scipy.stats import norm

from src.experiment_design.acquisition import expected_improvement, upper_confidence_bound
from src.gp_model.residual_gp import ResidualGP


class ExperimentRecommendation(BaseModel):
    features: list[float]
    acquisition_score: float
    predicted_mean: float
    uncertainty_std: float
    objective: str
    rank: int


class BayesianExperimentSelector:
    """
    EI: maximize predicted performance.
    EIG: maximize learning (uncertainty reduction) — preferred for calibration.
    """

    def __init__(self, gp: ResidualGP):
        self.gp = gp

    def expected_information_gain(
        self,
        X_candidate: np.ndarray,
        y_mechanistic: np.ndarray,
        n_fantasies: int = 32,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        """
        Approximate EIG by fantasizing observations at each candidate and
        measuring expected reduction in predictive std at that point.

        For an unfitted GP, ranks by prior uncertainty (all equal → uniform).
        """
        rng = rng or np.random.default_rng(42)
        X = np.asarray(X_candidate, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        y_mech = np.asarray(y_mechanistic, dtype=float)
        if len(y_mech) != len(X):
            raise ValueError("y_mechanistic must match X_candidate length")

        y_pred, unc95 = self.gp.predict(X, y_mech)
        sigma = unc95 / 1.96
        eig = np.zeros(len(X))

        if not self.gp.is_fitted:
            # No data yet — all candidates equally informative under prior
            return np.ones(len(X))

        # Current predictive uncertainty
        current_u = sigma.copy()

        for i in range(len(X)):
            # Fantasize observations ~ N(y_pred[i], sigma[i]^2)
            fantasies = rng.normal(y_pred[i], max(sigma[i], 1e-9), size=n_fantasies)
            post_unc = []
            for fant in fantasies:
                # Refit a shallow copy-like GP on augmented data is expensive;
                # use analytic 1-point posterior variance reduction for RBF-like GPs:
                # σ²_post ≈ σ² · (1 - σ²/(σ²+noise)) under homoscedastic approx.
                noise = 0.1
                reduction = (sigma[i] ** 2) / (sigma[i] ** 2 + noise)
                post_unc.append(sigma[i] * np.sqrt(max(0.0, 1.0 - reduction)))
            eig[i] = float(current_u[i] - np.mean(post_unc))
        return eig

    def recommend(
        self,
        X_candidate: np.ndarray,
        y_mechanistic: np.ndarray,
        objective: Literal["information_gain", "EI", "UCB"] = "information_gain",
        n_recommendations: int = 3,
        current_best: float = 0.0,
    ) -> list[ExperimentRecommendation]:
        X = np.asarray(X_candidate, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        y_mech = np.asarray(y_mechanistic, dtype=float)
        y_pred, unc95 = self.gp.predict(X, y_mech)
        sigma = unc95 / 1.96

        if objective == "information_gain":
            scores = self.expected_information_gain(X, y_mech)
        elif objective == "EI":
            scores = expected_improvement(y_pred, sigma, current_best=current_best)
        elif objective == "UCB":
            scores = upper_confidence_bound(y_pred, sigma)
        else:
            raise ValueError(f"Unsupported objective '{objective}'")

        ranked = np.argsort(scores)[::-1][:n_recommendations]
        out: list[ExperimentRecommendation] = []
        for rank, idx in enumerate(ranked, start=1):
            out.append(
                ExperimentRecommendation(
                    features=X[idx].tolist(),
                    acquisition_score=float(scores[idx]),
                    predicted_mean=float(y_pred[idx]),
                    uncertainty_std=float(sigma[idx]),
                    objective=objective,
                    rank=rank,
                )
            )
        return out
