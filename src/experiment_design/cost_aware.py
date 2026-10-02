"""Cost-aware, pending-aware experiment ranking with a written reason.

Wraps ``BayesianExperimentSelector`` scores without changing them. Ranking
value is (acquisition score) / (cost). Costs are caller-supplied positive
numbers in the caller's own unit (for example hours or plate wells); the
unit is recorded and never converted. Candidates within ``min_separation``
(in feature space, Euclidean) of a pending experiment are excluded, because
a result is already on its way for that region.

The reason string is generated from the numbers, so it is traceable to the
inputs and is not free text from a model.
"""

from __future__ import annotations

from typing import Any, Literal

import numpy as np

from src.experiment_design.bayesian_selector import BayesianExperimentSelector


def recommend_with_cost(
    selector: BayesianExperimentSelector,
    X_candidate: np.ndarray,
    y_mechanistic: np.ndarray,
    costs: list[float],
    cost_unit: str,
    pending: np.ndarray | None = None,
    min_separation: float = 0.0,
    objective: Literal["information_gain", "EI", "UCB"] = "information_gain",
    n_recommendations: int = 3,
    current_best: float = 0.0,
) -> list[dict[str, Any]]:
    """Rank candidates by acquisition per unit cost, excluding pending regions."""
    X = np.asarray(X_candidate, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    c = np.asarray(costs, dtype=float)
    if len(c) != len(X):
        raise ValueError("costs must match X_candidate length")
    if not np.all(np.isfinite(c)) or np.any(c <= 0):
        raise ValueError("costs must be finite and positive")
    if not cost_unit.strip():
        raise ValueError("cost_unit must be a non-empty string")
    if min_separation < 0:
        raise ValueError("min_separation must be non-negative")

    ranked = selector.recommend(
        X, y_mechanistic, objective=objective, n_recommendations=len(X), current_best=current_best
    )
    index_of = {tuple(X[i].tolist()): i for i in range(len(X))}

    P = None
    if pending is not None and len(pending):
        P = np.asarray(pending, dtype=float)
        if P.ndim == 1:
            P = P.reshape(-1, 1)
        if P.shape[1] != X.shape[1]:
            raise ValueError("pending must have the same feature count as X_candidate")

    rows: list[dict[str, Any]] = []
    for rec in ranked:
        i = index_of[tuple(rec.features)]
        nearest = None
        if P is not None:
            nearest = float(np.min(np.linalg.norm(P - X[i], axis=1)))
            if nearest <= min_separation:
                continue
        value = rec.acquisition_score / float(c[i])
        reason = (
            f"{objective} score {rec.acquisition_score:.4g} at predicted mean "
            f"{rec.predicted_mean:.4g} (std {rec.uncertainty_std:.4g}), divided by "
            f"cost {c[i]:g} {cost_unit} = {value:.4g} per {cost_unit}."
        )
        if nearest is not None:
            reason += f" Nearest pending experiment is {nearest:.4g} away (limit {min_separation:g})."
        rows.append(
            {
                "features": rec.features,
                "score_per_cost": float(value),
                "acquisition_score": rec.acquisition_score,
                "cost": float(c[i]),
                "cost_unit": cost_unit,
                "reason": reason,
            }
        )
    rows.sort(key=lambda r: r["score_per_cost"], reverse=True)
    rows = rows[:n_recommendations]
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return rows
