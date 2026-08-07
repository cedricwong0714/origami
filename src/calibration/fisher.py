"""
Fisher Information Matrix experimental design (CLASP Docs-6 §4).

Use Fisher information to design calcium dose-response conditions that
most reduce parameter uncertainty. Distinct from Bayesian optimization,
which selects the best design performance.
"""

from __future__ import annotations

from typing import Callable, Optional

import numpy as np


class FisherInformationDesigner:
    """
    F_ij = Σ_k (1/σ²) · (∂y_k/∂θ_i) · (∂y_k/∂θ_j)

    Sensitivities via central finite differences.
    """

    def __init__(
        self,
        model_func: Callable[[np.ndarray, np.ndarray], np.ndarray],
        parameters: list[str],
        noise_variance: float = 1.0,
        eps: float = 1e-6,
    ):
        """
        model_func(theta, conditions) -> y predictions of shape (n_conditions,)
        """
        self.model_func = model_func
        self.parameters = list(parameters)
        self.noise_variance = float(noise_variance)
        self.eps = float(eps)

    def compute_fim(
        self,
        theta: np.ndarray,
        experimental_conditions: np.ndarray,
        noise_variance: Optional[float] = None,
    ) -> np.ndarray:
        theta = np.asarray(theta, dtype=float)
        conditions = np.asarray(experimental_conditions, dtype=float)
        if conditions.ndim == 1:
            conditions = conditions.reshape(-1, 1)
        n_params = len(theta)
        sigma2 = float(noise_variance if noise_variance is not None else self.noise_variance)
        FIM = np.zeros((n_params, n_params))

        # Sensitivities at each condition
        for k in range(len(conditions)):
            cond = conditions[k : k + 1]
            sensitivities = np.zeros(n_params)
            for j in range(n_params):
                theta_plus = theta.copy()
                theta_minus = theta.copy()
                step = self.eps * max(1.0, abs(theta[j]))
                theta_plus[j] += step
                theta_minus[j] -= step
                y_plus = float(self.model_func(theta_plus, cond)[0])
                y_minus = float(self.model_func(theta_minus, cond)[0])
                sensitivities[j] = (y_plus - y_minus) / (2.0 * step)
            FIM += np.outer(sensitivities, sensitivities) / sigma2
        return FIM

    def d_optimality(self, fim: np.ndarray) -> float:
        """D-optimality: det(FIM). Higher is better (more information)."""
        sign, logdet = np.linalg.slogdet(fim)
        if sign <= 0:
            return 0.0
        return float(np.exp(logdet))

    def parameter_std_lower_bounds(self, fim: np.ndarray) -> np.ndarray:
        """
        Cramér–Rao lower bounds on parameter std-devs: sqrt(diag(FIM^{-1})).
        Non-identifiable parameters return +inf.
        """
        try:
            cov = np.linalg.inv(fim)
            diag = np.diag(cov)
            out = np.sqrt(np.maximum(diag, 0.0))
            out[~np.isfinite(out)] = np.inf
            return out
        except np.linalg.LinAlgError:
            return np.full(fim.shape[0], np.inf)

    def identifiability_report(
        self,
        theta: np.ndarray,
        experimental_conditions: np.ndarray,
        threshold_rel: float = 1.0,
    ) -> dict:
        """
        Flag parameters whose CRLB exceeds threshold_rel · |θ| as non-identifiable.
        """
        fim = self.compute_fim(theta, experimental_conditions)
        crlb = self.parameter_std_lower_bounds(fim)
        non_identifiable = []
        for name, th, std in zip(self.parameters, theta, crlb):
            if not np.isfinite(std) or std > threshold_rel * max(abs(th), 1e-12):
                non_identifiable.append(name)
        return {
            "fim": fim,
            "crlb_std": crlb,
            "d_optimality": self.d_optimality(fim),
            "non_identifiable_parameters": non_identifiable,
            "parameter_names": list(self.parameters),
        }

    def rank_conditions_by_information(
        self,
        theta: np.ndarray,
        candidate_conditions: np.ndarray,
        top_k: int = 5,
    ) -> list[dict]:
        """
        Rank single-condition additions by their contribution to D-optimality.
        """
        candidates = np.asarray(candidate_conditions, dtype=float)
        if candidates.ndim == 1:
            candidates = candidates.reshape(-1, 1)
        scores = []
        for i, cond in enumerate(candidates):
            fim = self.compute_fim(theta, cond.reshape(1, -1))
            scores.append(
                {
                    "index": i,
                    "condition": cond.tolist(),
                    "d_optimality": self.d_optimality(fim),
                }
            )
        scores.sort(key=lambda s: s["d_optimality"], reverse=True)
        return scores[:top_k]
