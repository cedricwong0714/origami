"""Discrete Bayesian optimization / active learning.

Candidates are a finite parts list (CTPR repeat counts). Acquisition is
computed from the GP posterior — not a grid of linear scores.

Default acquisition: constrained UCB, which both exploits the posterior
mean and explores high-variance (information-rich) designs. Sterically
refused candidates are masked.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from origami.design_engine.gp import GPPosterior


@dataclass
class NextExperiment:
    n_repeats: int
    acquisition: float
    posterior_mean: float
    posterior_std: float
    physics_score: float
    p_instability: float
    interpolated: bool
    reason: str
    acquisition_name: str


def expected_improvement(mean: np.ndarray, std: np.ndarray, best: float) -> np.ndarray:
    """EI for maximization. Uses the Gaussian tail (calculus on the posterior)."""
    from scipy.stats import norm

    std = np.maximum(std, 1e-12)
    z = (mean - best) / std
    return (mean - best) * norm.cdf(z) + std * norm.pdf(z)


def entropy(std: np.ndarray) -> np.ndarray:
    """Differential entropy of a univariate Gaussian posterior, ½ log(2πe σ²)."""
    return 0.5 * np.log(2.0 * np.pi * np.e * np.maximum(std, 1e-12) ** 2)


def recommend(
    candidates: np.ndarray,
    posterior: GPPosterior,
    physics_scores: np.ndarray,
    p_instability: np.ndarray,
    observed: set[int] | None = None,
    kappa: float = 1.8,
    clash_limit: float = 0.85,
    acquisition: str = "ucb",
) -> NextExperiment:
    observed = observed or set()
    n = candidates.astype(int).ravel()
    mean = posterior.mean
    std = posterior.std
    if acquisition == "ucb":
        acq = mean + kappa * std
        name = f"UCB(κ={kappa})"
    elif acquisition == "entropy":
        acq = entropy(std)
        name = "posterior entropy (information gain proxy)"
    elif acquisition == "ei":
        mask_obs = np.array([int(v) in observed for v in n])
        best = float(np.max(mean[mask_obs])) if np.any(mask_obs) else float(np.max(mean))
        acq = expected_improvement(mean, std, best)
        name = "expected improvement"
    else:
        raise ValueError(f"unknown acquisition {acquisition}")

    unused = np.array([int(v) not in observed for v in n])
    legal = (p_instability < clash_limit) & unused
    if not np.any(legal):
        if np.any(unused):
            legal = unused
            acq = -p_instability + 0.05 * std
            name = name + " (all unused designs exceed steric threshold; ranking least-unstable unused)"
        else:
            legal = np.ones(len(n), dtype=bool)
            name = name + " (library exhausted; allowing remeasure)"
    masked = np.where(legal, acq, -np.inf)
    idx = int(np.argmax(masked))
    return NextExperiment(
        n_repeats=int(n[idx]),
        acquisition=float(acq[idx]),
        posterior_mean=float(mean[idx]),
        posterior_std=float(std[idx]),
        physics_score=float(physics_scores[idx]),
        p_instability=float(p_instability[idx]),
        interpolated=bool(posterior.interpolated[idx]),
        reason=(
            f"{name} over discrete CTPR lengths. "
            "This is the next assay to run, not a claim that the design is validated."
        ),
        acquisition_name=name,
    )
