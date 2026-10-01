"""Train the residual GP on literature series this lab will not measure.

The training rows are the Phillips 2012 CTPRa DSC table already in
``data/stability/ctpr_thermal_literature.json``. This lab plan has no
DSC and no thermal shift, so these melts and unfolding ΔG values will
not be replaced by a local assay.

The physics score for each row is the length model already fit to
these same printed cells, in the same units as the table. The GP
learns the residual of the printed cell around that model. It does
not learn bridging luminescence, and it does not invent a surrogate
yield.

``calibrated`` stays false. ``gp_fitted`` is true only when at least
three cited lengths were used.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from origami.design_engine.active_learning import recommend
from origami.design_engine.gp import GPHyperparameters, ResidualGP
from origami.stability.length_fit import LengthFit, fit_named_delta_g, fit_named_tm
from origami.stability.series import (
    PHILLIPS_2012_CTPRA_DSC,
    companion_delta_g_rows,
    load_named_series,
)
from origami.stability.table import ThermalObservation

_Z95 = 1.96
# Optimizer bounds inside ResidualGP.fit. These are numerical limits on
# the Matérn hyperparameters, not biological constants.
_LENGTHSCALE_FLOOR = 0.3
_VARIANCE_FLOOR = 1e-3


def train_literature() -> dict[str, Any]:
    """Fit one residual GP on cited Tm and one on cited unfolding ΔG."""
    tm_rows = load_named_series(PHILLIPS_2012_CTPRA_DSC)
    dg_rows = companion_delta_g_rows(PHILLIPS_2012_CTPRA_DSC)
    tm_fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    dg_fit = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "lab_will_measure_this": False,
        "reason": (
            "The lab plan has no DSC and no thermal shift. "
            "These rows are Phillips et al. 2012, DOI 10.1002/pro.2018, CTPRa, DSC. "
            "They are not bridging luminescence and not a fusion assay."
        ),
        "tm": _fit_track(tm_rows, tm_fit, "Tm_C", "C"),
        "delta_g": _fit_track(dg_rows, dg_fit, "delta_G", "kcal mol^-1"),
    }


def _fit_track(
    rows: list[ThermalObservation],
    fit: LengthFit,
    observable: str,
    units: str,
) -> dict[str, Any]:
    training: list[dict[str, Any]] = []
    xs: list[list[float]] = []
    ys: list[float] = []
    physics: list[float] = []
    sigmas: list[float | None] = []
    for row in rows:
        if row.observable != observable:
            continue
        predicted = fit.predict(row.n_repeats)
        if predicted.value is None:
            continue
        xs.append([float(row.n_repeats)])
        ys.append(float(row.value))
        physics.append(float(predicted.value))
        sigmas.append(None if row.uncertainty is None else float(row.uncertainty))
        training.append(
            {
                "n_repeats": row.n_repeats,
                "y": float(row.value),
                "sigma": None if row.uncertainty is None else float(row.uncertainty),
                "physics": float(predicted.value),
                "residual": float(row.value) - float(predicted.value),
                "record_id": row.record_id,
                "doi": row.doi,
                "source": "literature",
            }
        )
    gp = ResidualGP()
    noise_note = (
        "At least one printed uncertainty is missing, so the GP noise "
        "hyperparameter stays at its default. A missing sigma is not "
        "stored as zero."
    )
    positive = [sigma for sigma in sigmas if sigma is not None and sigma > 0]
    if training and len(positive) == len(sigmas):
        gp.hypers = GPHyperparameters(noise=float(np.mean(positive)))
        noise_note = "GP noise was initialized from the mean printed uncertainty."
    fitted = len(training) >= 3
    if training:
        gp.fit(
            np.array(xs, dtype=float),
            np.array(ys, dtype=float),
            np.array(physics, dtype=float),
            optimize=fitted,
        )
    candidates = list(range(3, 25))
    s_star = []
    usable = []
    for n_repeats in candidates:
        predicted = fit.predict(n_repeats)
        if predicted.value is None:
            continue
        usable.append(n_repeats)
        s_star.append(float(predicted.value))
    posterior = gp.predict(
        np.array(usable, dtype=float).reshape(-1, 1), np.array(s_star)
    )
    observed = {int(row["n_repeats"]) for row in training}
    nxt = recommend(
        np.array(usable, dtype=float).reshape(-1, 1),
        posterior,
        np.array(s_star, dtype=float),
        np.zeros(len(usable)),
        observed=observed,
        acquisition="ucb",
    )
    longest = max(observed) if observed else None
    by_n = {n: index for index, n in enumerate(usable)}
    unused_std = [
        float(posterior.std[index])
        for n_repeats, index in by_n.items()
        if n_repeats not in observed
    ]
    flat_unused = bool(unused_std) and max(unused_std) - min(unused_std) < 1e-4
    on_floor = (
        gp.hypers.lengthscale <= _LENGTHSCALE_FLOOR * 1.001
        or gp.hypers.variance <= _VARIANCE_FLOOR * 1.001
    )
    identifiability = (
        "The Matérn lengthscale or residual variance sat on the optimizer floor. "
        "The length model already carries the trend in the printed cells. "
        "The posterior width is the noise term."
        if on_floor
        else "Kernel hyperparameters finished inside the optimizer bounds."
    )
    flat_note = (
        " Posterior standard deviation is flat across unmeasured lengths, "
        "so UCB follows the small remaining rise in the length model and "
        "lands on the last candidate. That is not evidence that a longer "
        "scaffold is more informative."
        if flat_unused
        else ""
    )
    past_note = (
        " The pick is past the longest cited length. It is an extrapolation."
        if longest is not None and nxt.n_repeats > longest
        else ""
    )
    preview = []
    shown: list[int] = []
    for n_repeats in (8, 14, 17, nxt.n_repeats):
        if n_repeats in shown:
            continue
        shown.append(n_repeats)
        index = by_n.get(n_repeats)
        if index is None:
            continue
        center = float(posterior.mean[index])
        sigma = float(posterior.std[index])
        preview.append(
            {
                "n_repeats": n_repeats,
                "posterior_mean": center,
                "posterior_std": sigma,
                "posterior_95_lower": center - _Z95 * sigma,
                "posterior_95_upper": center + _Z95 * sigma,
                "in_training_set": n_repeats in observed,
            }
        )
    return {
        "calibrated": False,
        "gp_fitted": fitted,
        "units": units,
        "n_training": len(training),
        "training_lengths": sorted(observed),
        "alpha": posterior.alpha,
        "beta": posterior.beta,
        "noise_note": noise_note,
        "identifiability_note": identifiability,
        "hyperparameters": {
            "lengthscale": float(gp.hypers.lengthscale),
            "variance": float(gp.hypers.variance),
            "noise": float(gp.hypers.noise),
        },
        "physics_note": (
            "The physics score is the length model fit to these same printed cells. "
            "The residual is the printed cell minus that model."
        ),
        "training_rows": training,
        "longest_cited_n": longest,
        "next_n_if_this_observable_were_measured": nxt.n_repeats,
        "next_past_longest_cited_length": (
            longest is not None and nxt.n_repeats > longest
        ),
        "next_reason": (
            "If this observable were measured, UCB would pick repeat count "
            f"{nxt.n_repeats} among lengths 3–24 that are absent from the "
            "Phillips table. The lab plan does not include DSC or a thermal "
            "shift, so this is not a wet-lab instruction."
            f"{flat_note}{past_note}"
        ),
        "preview": preview,
    }
