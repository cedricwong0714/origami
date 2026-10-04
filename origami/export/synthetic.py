"""Labelled synthetic learner rows. Not wet-lab data."""

from __future__ import annotations

from typing import Any

import numpy as np

from origami.ssdk.chassis import evaluate_chassis


def synthetic_learn_rows(
    n_values: list[int],
    *,
    seed: int = 0,
    noise_sd: float = 0.05,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    observations: list[dict[str, Any]] = []
    physics: list[dict[str, Any]] = []
    for n in n_values:
        chassis = evaluate_chassis({"n_repeats": int(n)})
        score = float(chassis["docking"]["chord_A"]) / 100.0
        y = float(score) + float(rng.normal(0.0, noise_sd))
        observations.append(
            {
                "n_repeats": int(n),
                "y": y,
                "sigma": noise_sd,
                "fidelity": 0,
                "output": "luminescence",
                "source": "synthetic_fixture",
            }
        )
        physics.append({"n_repeats": int(n), "chord_A_over_100": score})
    return {
        "calibrated": False,
        "data_class": "synthetic_fixture",
        "seed": seed,
        "noise_sd": noise_sd,
        "physics": physics,
        "observations": observations,
        "note": (
            "y is chord_A/100 plus Gaussian noise. "
            "It is not a plate readout. Do not treat a PASS against unmeasured "
            "thresholds as validation."
        ),
    }
