"""Two-fidelity luminescence GP on top of an SSDK engine result.

Dry fidelity (0) uses the docking physics score at each length. Wet fidelity
(1) uses caller ``y`` (RLU or surrogate readout). Thresholds and costs come
from ``data/config/active_learning_config.json`` (placeholders until measured).

Only luminescence is modelled; other pass/fail outputs stay absent and
``overall_status`` reflects luminescence-only gating when noted.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from origami.ssdk.canonical_learner import (
    construct_flags,
    feature_matrix_sha256,
    geometry_feature_matrix,
)
from origami.ssdk.features import FEATURE_NAMES
from src.experiment_design.frozen_table import (
    cost_weighted_ei,
    load_config,
    passes,
    unmeasured_items,
)
from src.gp_model.multifidelity import MultiFidelityGP

MODEL_VERSION = "mf-lum-v0.2"


def multifidelity_luminescence_block(
    result: Any,
    observation_rows: list[dict[str, Any]],
    n_max: int,
    flags: dict[str, float] | None = None,
    sequence_vector: np.ndarray | None = None,
    sequence_method: str = "none",
    X_all: np.ndarray | None = None,
) -> dict[str, Any]:
    """Build the ``multifidelity_luminescence`` section for ``learn_ssdk``.

    The feature matrix is ``geometry_feature_matrix``. A row whose
    ``output`` is not luminescence is ignored here. It belongs to the
    per-assay GP, not to this luminescence fit.
    """
    cfg = load_config()
    by_n = {int(n): i for i, n in enumerate(result.candidates)}
    candidates = [int(n) for n in result.candidates]
    if flags is None:
        flags = construct_flags(None)
    if X_all is None:
        X_all = geometry_feature_matrix(result, n_max, flags, sequence_vector)

    X_train: list[np.ndarray] = []
    f_train: list[int] = []
    y_train: list[float] = []
    wet_noise: list[float | None] = []

    wet_by_n: dict[int, float] = {}
    for row in observation_rows:
        if row.get("output", "luminescence") != "luminescence":
            continue
        n = int(row["n_repeats"])
        fid = int(row.get("fidelity", 1))
        if fid not in (0, 1):
            raise ValueError(f"fidelity must be 0 or 1 for n={n}")
        if n not in by_n:
            continue
        idx = by_n[n]
        X_train.append(X_all[idx])
        f_train.append(fid)
        y_train.append(float(row["y"]))
        sigma = row.get("sigma")
        wet_noise.append(float(sigma) if fid == 1 and sigma is not None else None)
        if fid == 1:
            wet_by_n[n] = float(row["y"])

    for n in candidates:
        if n in wet_by_n:
            continue
        idx = by_n[n]
        X_train.append(X_all[idx])
        f_train.append(0)
        y_train.append(float(result.physics_scores[idx]))
        wet_noise.append(None)

    fitted = len(X_train) >= 2 and any(f == 1 for f in f_train)
    mf: dict[str, Any] = {
        "model_version": MODEL_VERSION,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "feature_names": list(FEATURE_NAMES),
        "feature_matrix_sha256": feature_matrix_sha256(X_all),
        "sequence_encoding": sequence_method,
        "linker_rms_A": float(flags["linker_rms_A"]),
        "config_placeholders_unmeasured": unmeasured_items(cfg),
        "threshold_luminescence": cfg["thresholds"]["luminescence"],
        "note": (
            "Luminescence threshold units (× background RLU) may not match "
            "surrogate y until assays are on the same scale. "
            "Threshold status is unmeasured until the team posts measured values."
        ),
        "fitted": fitted,
        "gp_hyperparameters": None,
        "candidates": [],
        "recommended_evaluation": None,
    }

    if not fitted:
        mf["warnings"] = [
            "Multi-fidelity luminescence GP needs at least one wet (fidelity=1) observation.",
        ]
        mf["candidates"] = _dry_only_candidates(result, cfg, n_max)
        return mf

    X = np.vstack(X_train)
    f = np.asarray(f_train, dtype=int)
    y = np.asarray(y_train, dtype=float)
    cv = float(cfg["assay_cvs"]["luminescence"]["value"])
    wet_sd_full = np.array(
        [
            0.0
            if fi == 0
            else (wi if wi is not None else cv * max(abs(yi), 1e-9))
            for fi, yi, wi in zip(f, y, wet_noise, strict=True)
        ],
        dtype=float,
    )
    gp = MultiFidelityGP(n_restarts=3, seed=0)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        gp.fit(X, f, y, wet_noise_sd=wet_sd_full)
    mf["gp_hyperparameters"] = gp.hyperparameters
    if caught:
        mf["warnings"] = [str(w.message) for w in caught]

    pred = gp.predict(X_all, fidelity=1, include_noise=False)
    thresh = float(cfg["thresholds"]["luminescence"]["value"])
    best_wet = max(wet_by_n.values()) if wet_by_n else float(np.max(pred.mean))

    eval_types = ["wet_NanoBiT"] * len(candidates)
    alpha = cost_weighted_ei(pred.mean, pred.std, best_wet, eval_types, cfg)
    rows = []
    for i, n in enumerate(candidates):
        mu, sigma = float(pred.mean[i]), float(pred.std[i])
        rows.append(
            {
                "n_repeats": n,
                "mu_luminescence": mu,
                "sigma_luminescence": sigma,
                "lower_95_luminescence": mu - 1.96 * sigma,
                "pass_luminescence": passes(mu, sigma, thresh),
                "acquisition_wet_NanoBiT": float(alpha[i]),
                "physics_score": float(result.physics_scores[by_n[n]]),
            }
        )
    mf["candidates"] = rows
    best_idx = int(np.argmax(alpha))
    mf["recommended_evaluation"] = {
        "n_repeats": candidates[best_idx],
        "evaluation_type": "wet_NanoBiT",
        "acquisition_score": float(alpha[best_idx]),
        "selected_fidelity_next": "wet",
        "pass_luminescence_at_recommendation": rows[best_idx]["pass_luminescence"],
    }
    dry_alpha = cost_weighted_ei(
        pred.mean, pred.std, best_wet, "dry_docking", cfg
    )
    mf["dry_docking_acquisition_at_next_n"] = float(dry_alpha[best_idx])
    return mf


def _dry_only_candidates(result: Any, cfg: dict[str, Any], n_max: int) -> list[dict[str, Any]]:
    thresh = float(cfg["thresholds"]["luminescence"]["value"])
    rows = []
    for i, n in enumerate(result.candidates):
        n = int(n)
        mu = float(result.physics_scores[i])
        sigma = 0.05 * abs(mu) + 0.01
        rows.append(
            {
                "n_repeats": n,
                "mu_luminescence": mu,
                "sigma_luminescence": sigma,
                "lower_95_luminescence": mu - 1.96 * sigma,
                "pass_luminescence": passes(mu, sigma, thresh),
                "acquisition_wet_NanoBiT": None,
                "physics_score": mu,
                "note": "Dry physics score only; wet GP not fitted.",
            }
        )
    return rows
