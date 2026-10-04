"""Canonical residual learner: sklearn Matérn-2.5, with the older engine as fallback.

The design-engine Cholesky GP remains available when the request sets
``learner`` to ``design_engine``. The default request is ``sklearn``.
If there is no wet luminescence row, sklearn cannot fit and the response
names ``design_engine_fallback`` instead of pretending the families match.
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np

from origami.linker_prior import kratky_porod_mean_square_A
from origami.ssdk.features import FEATURE_NAMES, ssdk_feature_vector
from src.experiment_design.frozen_table import cost_weighted_ei, load_config
from origami.ssdk.hetero_noise import residual_scatter
from src.gp_model.residual_gp import ResidualGP

WET_OUTPUTS = (
    "luminescence",
    "locking_fraction",
    "expression",
    "solubility",
    "purity",
)


def construct_flags(body: dict[str, Any] | None) -> dict[str, float]:
    """Placement flags. Defaults match the wet architecture: CaM off scaffold, M13 grafted."""
    raw = body or {}
    linker = raw.get("linker_residues", 15)
    if isinstance(linker, bool) or not isinstance(linker, int) or linker < 1:
        linker = 15
    rms = float(np.sqrt(kratky_porod_mean_square_A(linker)))
    return {
        "linker_rms_A": rms,
        "cam_on_scaffold": 1.0 if raw.get("cam_on_scaffold", False) else 0.0,
        "m13_on_scaffold": 1.0 if raw.get("m13_on_scaffold", True) else 0.0,
    }


def feature_matrix(result: Any, n_max: int, flags: dict[str, float]) -> np.ndarray:
    rows = []
    for i, n in enumerate(result.candidates):
        rows.append(
            ssdk_feature_vector(
                int(n),
                float(result.physics_scores[i]),
                float(result.p_instability[i]),
                n_max,
                linker_rms_A=flags["linker_rms_A"],
                cam_on_scaffold=flags["cam_on_scaffold"],
                m13_on_scaffold=flags["m13_on_scaffold"],
            )
        )
    return np.vstack(rows)


def _with_sequence(X: np.ndarray, sequence_vector: np.ndarray | None) -> np.ndarray:
    if sequence_vector is None:
        return X
    extra = np.repeat(np.asarray(sequence_vector, dtype=float).reshape(1, -1), len(X), axis=0)
    return np.hstack([X, extra])


def geometry_feature_matrix(
    result: Any,
    n_max: int,
    flags: dict[str, float],
    sequence_vector: np.ndarray | None = None,
) -> np.ndarray:
    """One feature matrix for every SSDK Gaussian process on this request.

    Columns are the screw descriptors in ``FEATURE_NAMES``, then the
    optional sequence block. The same array is what sklearn, the
    per-assay multi-fidelity GPs, and the luminescence multi-fidelity
    GP must see. Rebuilding it inside one of those fits is how the
    linker flags used to drop out.
    """
    return _with_sequence(feature_matrix(result, n_max, flags), sequence_vector)


def feature_matrix_sha256(matrix: np.ndarray) -> str:
    """Checksum of the shared float64 feature matrix. Not a sequence checksum."""
    payload = np.ascontiguousarray(matrix, dtype=np.float64).tobytes()
    return hashlib.sha256(payload).hexdigest()


def fit_sklearn_luminescence(
    result: Any,
    observation_rows: list[dict[str, Any]],
    n_max: int,
    flags: dict[str, float],
    sequence_vector: np.ndarray | None = None,
    sequence_method: str = "none",
    use_heteroscedastic_std: bool = False,
    X_all: np.ndarray | None = None,
) -> dict[str, Any]:
    """Residual GP of wet luminescence minus the docking physics score."""
    by_n = {int(n): i for i, n in enumerate(result.candidates)}
    if X_all is None:
        X_all = geometry_feature_matrix(result, n_max, flags, sequence_vector)
    X_rows: list[np.ndarray] = []
    y_obs: list[float] = []
    y_mech: list[float] = []
    measured: set[int] = set()
    for row in observation_rows:
        if row.get("output", "luminescence") != "luminescence":
            continue
        if int(row.get("fidelity", 1)) != 1:
            continue
        n = int(row["n_repeats"])
        if n not in by_n:
            continue
        idx = by_n[n]
        X_rows.append(X_all[idx])
        y_obs.append(float(row["y"]))
        y_mech.append(float(result.physics_scores[idx]))
        measured.add(n)
    base = {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "feature_names": list(FEATURE_NAMES),
        "feature_matrix_sha256": feature_matrix_sha256(X_all),
        "sequence_encoding": sequence_method,
        "heteroscedastic": {
            "fitted": False,
            "replaces_assay_cv": False,
            "origin": "residual_scatter_model",
        },
        "fitted": False,
        "family": "sklearn_matern_residual",
    }
    if len(X_rows) < 1:
        base["reason"] = "No wet luminescence row, so the sklearn residual GP was not fit."
        return base
    X_train = np.vstack(X_rows)
    residuals = np.asarray(y_obs) - np.asarray(y_mech)
    gp = ResidualGP(n_restarts=2)
    gp.fit(X_train, np.asarray(y_obs), np.asarray(y_mech))
    mean, half = gp.predict(X_all, np.asarray(result.physics_scores, dtype=float))
    std = np.asarray(half, dtype=float) / 1.96
    scatter = residual_scatter(X_train, residuals, X_all)
    if use_heteroscedastic_std and scatter.get("fitted"):
        std = np.asarray(scatter["sigma"], dtype=float)
    cfg = load_config()
    best = max(y_obs)
    alpha = cost_weighted_ei(mean, std, best, "wet_NanoBiT", cfg)
    candidates = [int(n) for n in result.candidates]
    eligible = [i for i, n in enumerate(candidates) if n not in measured]
    if not eligible:
        eligible = list(range(len(candidates)))
    pick = eligible[int(np.argmax(alpha[eligible]))]
    base.update(
        fitted=True,
        next_n=candidates[pick],
        acquisition_score=float(alpha[pick]),
        heteroscedastic=scatter,
        used_heteroscedastic_std=bool(use_heteroscedastic_std and scatter.get("fitted")),
        reason=(
            f"sklearn Matérn-2.5 residual GP on {len(X_rows)} wet luminescence "
            f"row(s). Next n={candidates[pick]} maximises EI/cost among unmeasured lengths."
        ),
        rows=[
            {
                "n_repeats": candidates[i],
                "mu": float(mean[i]),
                "sigma": float(std[i]),
                "acquisition_wet_NanoBiT": float(alpha[i]),
                "measured": candidates[i] in measured,
            }
            for i in range(len(candidates))
        ],
    )
    return base
