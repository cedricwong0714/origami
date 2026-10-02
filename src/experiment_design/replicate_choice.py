"""Replicate-versus-new-design choice by variance reduction per cost.

For a point whose current predictive variance is v and whose measurement
noise variance is s2, one extra observation gives the standard Gaussian
update  v_post = 1 / (1/v + 1/s2).  The variance reduction is v - v_post.
This is exact for a single Gaussian-noise measurement at that point and
ignores the GP's correlation between neighbouring points, so it understates
the value of a new point that also informs its neighbours.

The measurement noise sigma is supplied by the caller (for example the
plate-reader replicate SEM or a stated assay CV); no default is invented.
Costs are caller-supplied positive numbers in a caller-named unit.
"""

from __future__ import annotations

import math
from typing import Any


def variance_reduction(sigma_pred: float, sigma_noise: float) -> float:
    """Reduction in predictive variance from one more observation."""
    if not (math.isfinite(sigma_pred) and sigma_pred > 0):
        raise ValueError("sigma_pred must be finite and positive")
    if not (math.isfinite(sigma_noise) and sigma_noise > 0):
        raise ValueError("sigma_noise must be finite and positive")
    v, s2 = sigma_pred**2, sigma_noise**2
    return v - 1.0 / (1.0 / v + 1.0 / s2)


def choose_replicate_or_new(
    observed: list[dict[str, Any]],
    new: list[dict[str, Any]],
    sigma_noise: float,
    cost_unit: str,
) -> dict[str, Any]:
    """Pick the best action. Each item needs ``label``, ``sigma_pred``, ``cost``."""
    if not cost_unit.strip():
        raise ValueError("cost_unit must be a non-empty string")
    options: list[dict[str, Any]] = []
    for kind, items in (("replicate", observed), ("new", new)):
        for item in items:
            cost = float(item["cost"])
            if not (math.isfinite(cost) and cost > 0):
                raise ValueError(f"cost for {item['label']!r} must be finite and positive")
            gain = variance_reduction(float(item["sigma_pred"]), sigma_noise)
            options.append(
                {
                    "action": kind,
                    "label": item["label"],
                    "variance_reduction": gain,
                    "cost": cost,
                    "gain_per_cost": gain / cost,
                }
            )
    if not options:
        raise ValueError("no candidate actions supplied")
    options.sort(key=lambda o: o["gain_per_cost"], reverse=True)
    best = options[0]
    best["reason"] = (
        f"{best['action']} of {best['label']!r} removes variance "
        f"{best['variance_reduction']:.4g} for {best['cost']:g} {cost_unit} "
        f"({best['gain_per_cost']:.4g} per {cost_unit}); noise sigma {sigma_noise:g}."
    )
    return {"best": best, "ranked": options, "calibrated": False}
