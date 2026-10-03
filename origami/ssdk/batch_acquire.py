"""Greedy batch of lengths, scored by EI/cost times a feasibility weight.

The batch size is the number of constructs you can run together (1 to 12).
Solubility and purity, when those outputs were fitted, down-weight a length
whose lower 95% bound misses the placeholder threshold. The weight is 0.25
per failed constraint. Unfitted constraints do not invent a penalty.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.experiment_design.frozen_table import cost_weighted_ei, load_config

_FAIL_WEIGHT = 0.25


def _penalty(multioutput: dict[str, Any], n_repeats: int) -> float:
    weight = 1.0
    outputs = multioutput.get("outputs") or {}
    for name in ("solubility", "purity"):
        block = outputs.get(name) or {}
        if not block.get("fitted"):
            continue
        for row in block.get("rows") or []:
            if int(row["n_repeats"]) == n_repeats and row.get("passes") is False:
                weight *= _FAIL_WEIGHT
    return weight


def select_batch(
    canonical: dict[str, Any],
    multioutput: dict[str, Any],
    batch_size: int,
) -> dict[str, Any]:
    """Pick up to ``batch_size`` unmeasured lengths. Requires a fitted canonical row list."""
    if batch_size < 1 or batch_size > 12:
        raise ValueError("batch_size must be from 1 to 12")
    rows = list(canonical.get("rows") or [])
    if not rows:
        return {
            "selected": [],
            "batch_size": batch_size,
            "reason": "Canonical learner has no rows, so no batch was selected.",
            "calibrated": False,
        }
    cfg = load_config()
    remaining = [i for i, row in enumerate(rows) if not row.get("measured")]
    if not remaining:
        remaining = list(range(len(rows)))
    selected: list[dict[str, Any]] = []
    while remaining and len(selected) < batch_size:
        means = np.array([rows[i]["mu"] for i in remaining])
        stds = np.array([rows[i]["sigma"] for i in remaining])
        best = max(float(row["mu"]) for row in rows)
        alpha = cost_weighted_ei(means, stds, best, "wet_full_panel", cfg)
        scores = []
        for local, i in enumerate(remaining):
            pen = _penalty(multioutput, int(rows[i]["n_repeats"]))
            scores.append(float(alpha[local]) * pen)
        choice = int(np.argmax(scores))
        idx = remaining.pop(choice)
        selected.append(
            {
                "n_repeats": int(rows[idx]["n_repeats"]),
                "score": scores[choice],
                "feasibility_weight": _penalty(multioutput, int(rows[idx]["n_repeats"])),
                "evaluation_type": "wet_full_panel",
            }
        )
    return {
        "selected": selected,
        "batch_size": batch_size,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "reason": (
            "Greedy batch on EI/cost for a full wet panel. "
            "Solubility or purity below the placeholder lower-95% gate multiplies the score by 0.25."
        ),
    }
