"""One multi-fidelity GP per wet output. Missing outputs stay absent.

Outputs: luminescence, locking_fraction, expression, solubility, purity.
An observation selects its output with ``output`` (default luminescence).
Overall PASS requires every *fitted* thresholded output to pass. An output
with no wet row is omitted, not scored as a failure and not filled in.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from origami.ssdk.canonical_learner import (
    WET_OUTPUTS,
    construct_flags,
    feature_matrix_sha256,
    geometry_feature_matrix,
)
from src.experiment_design.frozen_table import Z95, load_config, passes, unmeasured_items
from src.gp_model.multifidelity import MultiFidelityGP

THRESHOLDED = ("luminescence", "locking_fraction", "solubility", "purity")


def _rows_for(observation_rows: list[dict[str, Any]], output: str) -> list[dict[str, Any]]:
    kept = []
    for row in observation_rows:
        name = row.get("output", "luminescence")
        if name == output:
            kept.append(row)
    return kept


def fit_output(
    result: Any,
    rows: list[dict[str, Any]],
    output: str,
    X_all: np.ndarray,
) -> dict[str, Any]:
    """Fit one output. Returns fitted=False when that output has no wet row."""
    wet = [r for r in rows if int(r.get("fidelity", 1)) == 1]
    if not wet:
        return {"output": output, "fitted": False, "calibrated": False}
    by_n = {int(n): i for i, n in enumerate(result.candidates)}
    X_list = []
    f_list = []
    y_list = []
    wet_ns = set()
    for row in wet:
        n = int(row["n_repeats"])
        if n not in by_n:
            continue
        idx = by_n[n]
        X_list.append(X_all[idx])
        f_list.append(1)
        y_list.append(float(row["y"]))
        wet_ns.add(n)
    for i, n in enumerate(result.candidates):
        if int(n) in wet_ns:
            continue
        X_list.append(X_all[i])
        f_list.append(0)
        y_list.append(float(result.physics_scores[i]))
    if sum(f_list) < 1:
        return {"output": output, "fitted": False, "calibrated": False}
    gp = MultiFidelityGP(n_restarts=2, seed=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        gp.fit(np.vstack(X_list), np.asarray(f_list), np.asarray(y_list, dtype=float))
    pred = gp.predict(X_all, fidelity=1, include_noise=False)
    cfg = load_config()
    thresh = cfg["thresholds"].get(output, {}).get("value")
    series = []
    for i, n in enumerate(result.candidates):
        mu, sigma = float(pred.mean[i]), float(pred.std[i])
        item: dict[str, Any] = {
            "n_repeats": int(n),
            "mu": mu,
            "sigma": sigma,
            "lower_95": mu - Z95 * sigma,
        }
        if thresh is not None:
            item["passes"] = passes(mu, sigma, float(thresh))
        series.append(item)
    return {
        "output": output,
        "fitted": True,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "threshold": thresh,
        "threshold_status": cfg["thresholds"].get(output, {}).get("status"),
        "rows": series,
    }


def multioutput_block(
    result: Any,
    observation_rows: list[dict[str, Any]],
    n_max: int,
    construct: dict[str, Any] | None,
    sequence_vector: np.ndarray | None = None,
    sequence_method: str = "none",
    X_all: np.ndarray | None = None,
) -> dict[str, Any]:
    flags = construct_flags(construct)
    if X_all is None:
        X_all = geometry_feature_matrix(result, n_max, flags, sequence_vector)
    cfg = load_config()
    outputs: dict[str, Any] = {}
    for name in WET_OUTPUTS:
        outputs[name] = fit_output(
            result, _rows_for(observation_rows, name), name, X_all
        )
    gated = [name for name in THRESHOLDED if outputs[name]["fitted"]]
    if not gated:
        status = "NOT_GATED"
    else:
        status = "PASS" if all(_output_passes(outputs[name]) for name in gated) else "FAIL"
    return {
        "calibrated": False,
        "model": "separate_multifidelity_gp_per_output",
        "feature_matrix_sha256": feature_matrix_sha256(X_all),
        "sequence_encoding": sequence_method,
        "overall_status": status,
        "gated_outputs": gated,
        "omitted_outputs": [name for name in WET_OUTPUTS if not outputs[name]["fitted"]],
        "placeholders_unmeasured": unmeasured_items(cfg),
        "outputs": outputs,
        "note": (
            "Each wet assay is its own two-fidelity GP. An assay with no row is omitted. "
            "Thresholds are placeholders until measured."
        ),
    }


def _output_passes(block: dict[str, Any]) -> bool:
    rows = block.get("rows") or []
    if not rows or "passes" not in rows[0]:
        return False
    return all(bool(row["passes"]) for row in rows)
