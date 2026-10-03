"""Turn blank-corrected RLU into amount with a caller-supplied standard curve.

The line is the existing assay fit, ``RLU = a + b × amount``. Inversion
is ``amount = (RLU − a) / b``. Uncertainty uses the delta method on a,
b, and the observation sigma when that sigma is present. Missing pieces
are omitted from the variance and named. They are not replaced with a
default.

Only luminescence rows are converted. Other assay outputs stay on the
scale the caller sent. ``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

from origami.assay.window import fit_standard_curve


class QuantificationError(ValueError):
    """The standard curve cannot convert luminescence into amount."""


def quantify_luminescence_rows(
    rows: list[dict[str, Any]],
    standard_curve: dict[str, Any],
    amount_units: str,
) -> dict[str, Any]:
    """Return converted row copies and the fit that produced them.

    ``rows`` are not mutated. Non-luminescence rows are copied through.
    """
    if not isinstance(amount_units, str) or not amount_units.strip():
        raise QuantificationError("amount_units is required when quantifying luminescence")
    if not isinstance(standard_curve, dict):
        raise QuantificationError("standard_curve must be an object with amount and rlu")
    fit = fit_standard_curve(standard_curve.get("amount"), standard_curve.get("rlu"))
    if not fit.get("computable"):
        missing = ", ".join(str(item) for item in fit.get("missing", []))
        raise QuantificationError(
            f"standard curve is not usable: {missing or 'fit failed'}"
        )
    intercept = float(fit["intercept"])
    slope = float(fit["slope"])
    if slope == 0.0:
        raise QuantificationError("standard-curve slope is zero, so amount is undefined")
    intercept_sigma = fit.get("intercept_sigma")
    slope_sigma = fit.get("slope_sigma")
    converted: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise QuantificationError(f"observations[{index}] must be an object")
        output = row.get("output", "luminescence")
        if output != "luminescence":
            converted.append(dict(row))
            continue
        y_rlu = float(row["y"])
        amount = (y_rlu - intercept) / slope
        sigma, sigma_note = _amount_sigma(
            y_rlu,
            intercept,
            slope,
            row.get("sigma"),
            intercept_sigma,
            slope_sigma,
        )
        updated = dict(row)
        updated["y_rlu"] = y_rlu
        updated["y"] = amount
        updated["sigma"] = sigma
        updated["units"] = amount_units.strip()
        updated["quantification_note"] = sigma_note
        converted.append(updated)
    return {
        "applied": True,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "learner_target": "amount",
        "amount_units": amount_units.strip(),
        "equation": "amount = (RLU - a) / b",
        "fit": fit,
        "rows": converted,
        "note": (
            "Luminescence observations were converted with the caller-supplied "
            "standard curve. Other outputs were left unchanged. "
            "This conversion is not a wet-lab calibration."
        ),
    }


def _amount_sigma(
    y_rlu: float,
    intercept: float,
    slope: float,
    y_sigma: object,
    intercept_sigma: object,
    slope_sigma: object,
) -> tuple[float | None, str]:
    """Delta-method sigma. A missing input is named and left out of the sum."""
    variance = 0.0
    used: list[str] = []
    omitted: list[str] = []
    d_dy = 1.0 / slope
    d_da = -1.0 / slope
    d_db = -(y_rlu - intercept) / slope**2
    pieces = (
        ("observation", y_sigma, d_dy),
        ("intercept", intercept_sigma, d_da),
        ("slope", slope_sigma, d_db),
    )
    for name, sigma, derivative in pieces:
        if sigma is None:
            omitted.append(name)
            continue
        sigma_f = float(sigma)
        if not math.isfinite(sigma_f) or sigma_f < 0:
            raise QuantificationError(f"{name} sigma must be finite and >= 0")
        variance += (derivative * sigma_f) ** 2
        used.append(name)
    if not used or variance == 0.0:
        return None, (
            "No positive sigma was available on the observation or the curve. "
            "A zero uncertainty was not stored."
        )
    note = f"Delta-method sigma uses {', '.join(used)}."
    if omitted:
        note += f" Omitted, because no sigma was supplied: {', '.join(omitted)}."
    return math.sqrt(variance), note


def curve_request_from_body(body: dict[str, Any]) -> dict[str, Any] | None:
    """Read raw amount and RLU points from the learn body. Do not accept a fitted curve."""
    direct = body.get("standard_curve")
    window = body.get("assay_window")
    nested = window.get("standard_curve") if isinstance(window, dict) else None
    chosen = direct if isinstance(direct, dict) else nested
    if chosen is None:
        return None
    if "amount" not in chosen or "rlu" not in chosen:
        raise QuantificationError(
            "standard_curve needs amount and rlu lists from the plate, not a fitted slope"
        )
    return {"amount": chosen.get("amount"), "rlu": chosen.get("rlu")}
