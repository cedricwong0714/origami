"""Grouped leave-one-group-out ablation of the three prediction layers.

Compares, on held-out groups (for example batches or constructs):
  physics      : mechanistic prediction only (no uncertainty, so no coverage)
  physics+GP   : mechanistic prediction plus ResidualGP correction
  physics+GP+XGB: the above plus the XGBoost residual layer, with the
                  interval widened by the XGBoost LOO RMSE in quadrature

Rows from one group are never split between training and test, so the score
measures transfer to a new batch rather than interpolation within a batch.
This is the gate in docs/SSDK_ROADMAP.md (long term, item 5): the tree layer
should be trusted only if it lowers held-out error versus physics+GP.
A passing run is a software result on the supplied data, not validation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from src.gp_model.residual_gp import ResidualGP
from src.gp_model.xgb_meta import InsufficientDataError, XGBoostMetaPredictor

Z95 = 1.96


def _rank(a: np.ndarray) -> np.ndarray:
    order = np.argsort(a, kind="mergesort")
    ranks = np.empty(len(a), dtype=float)
    ranks[order] = np.arange(len(a), dtype=float)
    for v in np.unique(a):
        mask = a == v
        if mask.sum() > 1:
            ranks[mask] = ranks[mask].mean()
    return ranks


def spearman(a: np.ndarray, b: np.ndarray) -> float | None:
    """Spearman rank correlation; None when undefined (constant input, n<3)."""
    if len(a) < 3:
        return None
    ra, rb = _rank(np.asarray(a, float)), _rank(np.asarray(b, float))
    if np.std(ra) == 0 or np.std(rb) == 0:
        return None
    return float(np.corrcoef(ra, rb)[0, 1])


def _metrics(y: np.ndarray, pred: np.ndarray, half: np.ndarray | None) -> dict[str, Any]:
    err = pred - y
    out: dict[str, Any] = {
        "rmse": float(np.sqrt(np.mean(err**2))),
        "mae": float(np.mean(np.abs(err))),
        "spearman": spearman(y, pred),
    }
    if half is None:
        out["coverage_95"] = None
        out["mean_half_width"] = None
    else:
        out["coverage_95"] = float(np.mean(np.abs(err) <= half))
        out["mean_half_width"] = float(np.mean(half))
    return out


def grouped_ablation(
    X: np.ndarray,
    y_obs: np.ndarray,
    y_mech: np.ndarray,
    groups: list[str],
    feature_names: list[str] | None = None,
) -> dict[str, Any]:
    """Leave-one-group-out comparison of physics, physics+GP, physics+GP+XGB.

    ``y_mech`` is the mechanistic prediction for every row, supplied by the
    caller so the harness does not depend on one specific ODE. Requires at
    least two distinct groups.
    """
    X = np.asarray(X, dtype=float)
    if X.ndim == 1:
        X = X.reshape(-1, 1)
    y = np.asarray(y_obs, dtype=float)
    ym = np.asarray(y_mech, dtype=float)
    g = np.asarray(groups)
    if not (len(X) == len(y) == len(ym) == len(g)):
        raise ValueError("X, y_obs, y_mech and groups must have the same length.")
    labels = sorted(set(g.tolist()))
    if len(labels) < 2:
        raise ValueError("Grouped validation needs at least two distinct groups.")
    names = feature_names or [f"x{i}" for i in range(X.shape[1])]

    p_gp = np.full(len(y), np.nan)
    h_gp = np.full(len(y), np.nan)
    p_xgb = np.full(len(y), np.nan)
    h_xgb = np.full(len(y), np.nan)
    xgb_folds = 0

    for label in labels:
        test = g == label
        train = ~test
        gp = ResidualGP()
        gp.fit(X[train], y[train], ym[train])
        mean_te, half_te = gp.predict(X[test], ym[test])
        p_gp[test] = mean_te
        h_gp[test] = half_te
        p_xgb[test] = mean_te
        h_xgb[test] = half_te
        if train.sum() >= XGBoostMetaPredictor.MIN_SAMPLES_REQUIRED:
            mean_tr, _ = gp.predict(X[train], ym[train])
            xgb = XGBoostMetaPredictor()
            try:
                xgb.fit(X[train], y[train] - mean_tr, feature_names=names)
            except (InsufficientDataError, ImportError):
                continue
            p_xgb[test] = mean_te + xgb.predict(X[test])
            sigma = np.sqrt((half_te / Z95) ** 2 + (xgb.loo_rmse or 0.0) ** 2)
            h_xgb[test] = Z95 * sigma
            xgb_folds += 1

    results = {
        "physics": _metrics(y, ym, None),
        "physics+GP": _metrics(y, p_gp, h_gp),
        "physics+GP+XGB": _metrics(y, p_xgb, h_xgb),
    }
    gain = results["physics+GP"]["rmse"] - results["physics+GP+XGB"]["rmse"]
    return {
        "n_rows": int(len(y)),
        "groups": labels,
        "xgb_active_folds": xgb_folds,
        "results": results,
        "xgb_gain_rmse": float(gain) if xgb_folds else None,
        "xgb_justified": bool(xgb_folds == len(labels) and gain > 0),
        "calibrated": False,
        "note": (
            "Held-out-group error on the supplied data only. Not wet-lab "
            "validation. Coverage near 0.95 is expected only if errors are "
            "roughly Gaussian and the groups resemble future batches."
        ),
    }
