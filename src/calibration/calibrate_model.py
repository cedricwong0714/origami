"""Leave-one-out residual metrics on provided y vs yhat. Not scientific validation."""

from __future__ import annotations

import math


def _loo_metrics(ys: list[float], yhats: list[float]) -> dict:
    """Pairwise residuals. With precomputed yhat this is equivalent to reporting
    hold-one-point residuals; it does not re-fit a model.
    """
    n = len(ys)
    sq_err = 0.0
    abs_err = 0.0
    loo_residuals: list[float] = []
    for y, yhat in zip(ys, yhats):
        residual = y - yhat
        loo_residuals.append(residual)
        sq_err += residual * residual
        abs_err += abs(residual)
    mse = sq_err / float(n)
    return {
        "n": n,
        "rmse": math.sqrt(mse),
        "mae": abs_err / float(n),
        "loo_residuals": loo_residuals,
    }


def calibrate_model(data: list[dict]) -> dict:
    """Compute residual metrics from rows that include ``y`` and ``yhat``.

    If fewer than 3 usable points, returns ``identifiable=False``,
    ``metrics=None``, and a warning. Results are diagnostic only and must not
    be presented as scientific validation of a biological model.
    """
    warning_not_validation = (
        "These metrics compare provided y and yhat only. They are not "
        "scientific validation of a biological or predictive model."
    )

    pairs: list[tuple[float, float]] = []
    for row in data or []:
        if "y" not in row or "yhat" not in row:
            continue
        try:
            pairs.append((float(row["y"]), float(row["yhat"])))
        except (TypeError, ValueError):
            continue

    n = len(pairs)
    if n < 3:
        return {
            "identifiable": False,
            "metrics": None,
            "warning": (
                "n<3 usable (y, yhat) pairs; identifiability cannot be assessed. "
                + warning_not_validation
            ),
        }

    ys = [p[0] for p in pairs]
    yhats = [p[1] for p in pairs]
    return {
        "identifiable": True,
        "metrics": _loo_metrics(ys, yhats),
        "warning": warning_not_validation,
    }
