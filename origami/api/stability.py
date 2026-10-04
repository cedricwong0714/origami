"""HTTP surfaces for the literature thermal panel and the length fit.

``GET /api/stability/panel`` is the raw lookup. It does not fit
``Tm(n)`` and it does not average series. ``GET /api/stability/confirm``
is the page payload. Each melting temperature and unfolding ΔG on that
payload is the per-series length model evaluated at that repeat count.
The comparison at the assay temperature uses the calculated melting
temperature. ``calibrated`` stays false.

The default comparison temperature is
``DEFAULT_OPERATING_TEMPERATURE_C`` (37 C). That value is an *E. coli*
operating assumption. It is not a temperature reported by Phillips et
al. 2012.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request

from origami.drylab import stability_panel
from origami.stability.length_fit import (
    MODEL_NAME,
    MODEL_VERSION,
    SATURATING_EQUATION,
    LINE_EQUATION,
    LengthFit,
    fit_named_delta_g,
    fit_named_tm,
    fit_public_dict,
)
from origami.stability.series import (
    DEFAULT_OPERATING_TEMPERATURE_C,
    PHILLIPS_2012_CTPRA_DSC,
)
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.thermo import (
    ThermoInputError,
    _PHILLIPS_TABLE_I_DELTA_G_T_C,
    effective_enthalpy_delta_cp_zero,
    gibbs_helmholtz_curves,
    gibbs_helmholtz_report,
    thermo_prefill,
)

router = APIRouter()

# Lengths shown on the confirmation page. The number at each length is
# the length model evaluated there, including a length past the longest
# cited repeat count.
_CONFIRM_N: tuple[int, ...] = (3, 8, 14)

# User-facing stability confirmation uses one literature series only.
_CANONICAL_SERIES = PHILLIPS_2012_CTPRA_DSC
_CANONICAL_DOI = "10.1002/pro.2018"
_CANONICAL_METHOD = "DSC"
_CANONICAL_CONSTRUCT_FAMILY = "CTPRa"

_ASSAY_DESCRIPTION = (
    "Assay comparison temperature in degrees Celsius. "
    "The default, 37, is an E. coli operating assumption "
    "(DEFAULT_OPERATING_TEMPERATURE_C), not a DSC setpoint "
    "from Phillips et al. 2012."
)

_CONFIRM_NOTE = (
    "Melting temperature and unfolding ΔG are calculated from a fit to one series. "
    f"With at least four points the model tried first is {SATURATING_EQUATION}, "
    "with y_inf, y_1, and lambda positive, and it is reported only when it is identifiable. "
    "After curve_fit, the saturating form is non-identifiable when any parameter "
    "standard error is not finite, or when the prediction sigma at n = 3, 8, or 14 "
    "is larger than the absolute value of the prediction. "
    f"That observable then uses {LINE_EQUATION} fit to the same rows, "
    "and the number shown is that line with its linearized 95% band. "
    "If the line is also non-identifiable, no point value is reported. "
    "For unfolding ΔG that warning is: the rows do not determine ΔG(n). "
    f"With two or three points the model is {LINE_EQUATION}. "
    "The comparison at the assay temperature uses the calculated melting temperature. "
    "A 95% band is value ± 1.96 sigma from the linearized fit covariance. "
    "It is a linear approximation, not a wet-lab confidence interval. "
    "Only the Phillips 2012 CTPRa DSC series is exposed on the confirmation screen. "
    "ΔHcal and ΔCp are not in the literature file and are not estimated here. "
    "calibrated stays false. A passing test is not scientific validation. "
    "The default comparison temperature 37 C is an E. coli operating "
    "assumption, not a temperature from Phillips et al. 2012. "
    f"Literature series id: {_CANONICAL_SERIES}."
)


def _panel_rows(t_assay_C: float) -> list[dict[str, Any]]:
    """Call ``stability_panel`` and surface its input errors as HTTP 400.

    Non-finite ``t_assay_C`` raises ``ValueError`` inside
    ``stability_panel`` (``t_assay_C must be finite``). A non-number
    raises ``TypeError`` (``t_assay_C must be a number``). Those
    messages are passed through. This function does not replace them
    with a different check.
    """
    try:
        return stability_panel(t_assay_C)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def literature_panel(t_assay_C: float) -> dict[str, Any]:
    """Wrap ``stability_panel`` without changing row fields.

    ``t_assay_C`` on the wrapper is the value stored on the rows, which
    is the float ``stability_panel`` compared against the cited Tm.
    """
    rows = _panel_rows(t_assay_C)
    assay = rows[0]["t_assay_C"] if rows else float(t_assay_C)
    return {
        "calibrated": False,
        "t_assay_C": assay,
        "rows": rows,
    }


def literature_confirm(t_assay_C: float) -> dict[str, Any]:
    """Calculated rows for the canonical series at n = 3, 8, and 14.

    The team-facing confirmation screen uses Phillips 2012 CTPRa DSC only.
    The displayed melting temperature is the length model at that n, and
    the pass/fail comparison uses that calculated value. The literature
    lookup for the same cell is ``paper_tm_C`` when a row exists.
    ``GET /api/stability/panel`` remains the raw multi-series lookup.
    """
    panel = literature_panel(t_assay_C)
    series_id = _CANONICAL_SERIES
    lookup = {
        (str(row["series_id"]), int(row["n_repeats"])): row for row in panel["rows"]
    }
    tm_fit = fit_named_tm(series_id)
    dg_fit = fit_named_delta_g(series_id)
    assay = float(panel["t_assay_C"])
    rows = [
        _confirm_row(
            series_id,
            n_repeats,
            assay,
            lookup.get((series_id, n_repeats)),
            tm_fit,
            dg_fit,
        )
        for n_repeats in _CONFIRM_N
    ]
    keys = [(row["series_id"], int(row["n_repeats"])) for row in rows]
    if len(rows) != len(_CONFIRM_N) or len(keys) != len(set(keys)):
        raise HTTPException(
            status_code=500,
            detail=(
                "stability confirmation must keep one row per team length "
                f"at n in {list(_CONFIRM_N)} for {_CANONICAL_SERIES}. "
                f"Got {len(rows)} rows."
            ),
        )
    if any(row["series_id"] != series_id for row in rows):
        raise HTTPException(
            status_code=500,
            detail="stability confirmation merged or dropped the canonical series",
        )
    return {
        "calibrated": False,
        "t_assay_C": assay,
        "literature_series_id": series_id,
        "doi": _CANONICAL_DOI,
        "method": _CANONICAL_METHOD,
        "construct_family": _CANONICAL_CONSTRUCT_FAMILY,
        "comparison": "fit",
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "equation_saturating": SATURATING_EQUATION,
        "equation_line": LINE_EQUATION,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "rows": rows,
        "series_fits": [
            {
                "series_id": series_id,
                "tm": fit_public_dict(tm_fit),
                "delta_g": fit_public_dict(dg_fit),
            }
        ],
        "note": _CONFIRM_NOTE,
    }


def _confirm_row(
    series_id: str,
    n_repeats: int,
    t_assay_C: float,
    paper: dict[str, Any] | None,
    tm_fit: LengthFit,
    dg_fit: LengthFit,
) -> dict[str, Any]:
    """Calculated Tm and ΔG, with the paper cell kept as a reference."""
    tm_pred = tm_fit.predict(n_repeats)
    dg_pred = dg_fit.predict(n_repeats)
    paper_tm = _paper_tm(paper)
    paper_dg = None if paper is None else paper.get("delta_g")
    if tm_pred.value is None:
        state = "not_fit"
        reason = (
            tm_fit.warnings[0]
            if tm_fit.warnings
            else "No melting-temperature curve was fit for this series."
        )
    elif tm_pred.value > t_assay_C:
        state = "pass"
        reason = (
            "The comparison uses the fit. "
            f"Calculated Tm {tm_pred.value} C is strictly greater than "
            f"assay temperature {t_assay_C} C."
        )
    else:
        state = "fail"
        reason = (
            "The comparison uses the fit. "
            f"Calculated Tm {tm_pred.value} C is less than or equal to "
            f"assay temperature {t_assay_C} C."
        )
    return {
        "source": "length_fit",
        "calibrated": False,
        "comparison_uses_fit": True,
        "series_id": series_id,
        "n_repeats": n_repeats,
        "t_assay_C": t_assay_C,
        "thermal_state": state,
        "tm_C": _plain(tm_pred.value),
        "tm_uncertainty_C": _plain(tm_pred.sigma),
        "tm_interval_low": _plain(tm_pred.band_95_low),
        "tm_interval_high": _plain(tm_pred.band_95_high),
        "tm_band_label": tm_pred.band_label,
        "tm_fit_form": tm_fit.form,
        "thermal_reason": reason,
        "paper_tm_C": _plain(paper_tm),
        "paper_tm_uncertainty_C": _plain(
            None if paper is None else paper.get("tm_uncertainty_C")
        ),
        "delta_g": _plain(dg_pred.value),
        "delta_g_units": dg_fit.units if dg_pred.value is not None else None,
        "delta_g_uncertainty": _plain(dg_pred.sigma),
        "delta_g_band_95_low": _plain(dg_pred.band_95_low),
        "delta_g_band_95_high": _plain(dg_pred.band_95_high),
        "delta_g_band_label": dg_pred.band_label,
        "delta_g_fit_form": dg_fit.form,
        "paper_delta_g": _plain(None if paper_dg is None else float(paper_dg)),
        "paper_delta_g_uncertainty": _plain(
            None if paper is None else paper.get("delta_g_uncertainty")
        ),
        "paper_delta_g_units": None if paper is None else paper.get("delta_g_units"),
        "longest_cited_n": tm_pred.longest_cited_n,
        "past_longest_cited_length": tm_pred.past_longest_cited_length,
        "length_note": tm_pred.length_note,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
    }


def stability_at_n(n_repeats: int, t_assay_C: float) -> dict[str, Any]:
    """Length-model melting temperature and ΔG at one repeat count.

    The number is the Phillips 2012 CTPRa DSC length fit evaluated at
    ``n_repeats``. A missing table row is not left blank. The ΔG anchor
    temperature is the Table I temperature, 10 °C, because that is the
    column the fit was trained on.
    """
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise ValueError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise ValueError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    panel = literature_panel(t_assay_C)
    series_id = _CANONICAL_SERIES
    lookup = {
        (str(row["series_id"]), int(row["n_repeats"])): row for row in panel["rows"]
    }
    assay = float(panel["t_assay_C"])
    tm_fit = fit_named_tm(series_id)
    dg_fit = fit_named_delta_g(series_id)
    row = _confirm_row(
        series_id,
        n_repeats,
        assay,
        lookup.get((series_id, n_repeats)),
        tm_fit,
        dg_fit,
    )
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "n_repeats": n_repeats,
        "t_assay_C": assay,
        "literature_series_id": series_id,
        "anchor_temperature_C": _PHILLIPS_TABLE_I_DELTA_G_T_C,
        "anchor_note": (
            "Length-model ΔG is the fit to the Phillips 2012 Table I "
            "unfolding ΔG column, which that table states at 10 °C. "
            "It is not a temperature correction."
        ),
        "model_name": MODEL_NAME,
        "model_version": MODEL_VERSION,
        "row": row,
    }


def _paper_tm(paper: dict[str, Any] | None) -> float | None:
    """Cited Tm from the lookup when that cell is a real table row."""
    if paper is None:
        return None
    if paper.get("thermal_state") not in ("pass", "fail"):
        return None
    value = paper.get("tm_C")
    if value is None:
        return None
    return float(value)


def _plain(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


@router.get("/api/stability/panel")
def get_stability_panel(
    t_assay_C: float = Query(
        default=DEFAULT_OPERATING_TEMPERATURE_C,
        description=_ASSAY_DESCRIPTION,
    ),
) -> dict[str, Any]:
    """Literature thermal panel for every named series and library n."""
    return literature_panel(t_assay_C)


@router.get("/api/stability/predict")
def get_stability_predict(
    n: int = Query(..., description="Repeat count from 3 to 24."),
    t_assay_C: float = Query(
        default=DEFAULT_OPERATING_TEMPERATURE_C,
        description=_ASSAY_DESCRIPTION,
    ),
) -> dict[str, Any]:
    """Length-model Tm and ΔG at any repeat count, including n = 14."""
    try:
        return stability_at_n(n, t_assay_C)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/stability/confirm")
def get_stability_confirm(
    t_assay_C: float = Query(
        default=DEFAULT_OPERATING_TEMPERATURE_C,
        description=_ASSAY_DESCRIPTION,
    ),
) -> dict[str, Any]:
    """Calculated n = 3, 8, and 14 for Phillips 2012 CTPRa DSC. The panel route stays the lookup."""
    return literature_confirm(t_assay_C)


@router.post("/api/stability/thermo")
async def post_stability_thermo(request: Request) -> dict[str, Any]:
    """ΔG, ΔH, and ΔS from caller-supplied Gibbs–Helmholtz inputs.

    Body: t_c, tm_c, delta_h, delta_cp, optional units ("kcal" or "kJ"),
    and optional delta_h_sigma, delta_cp_sigma, tm_sigma_c.
    Temperatures are °C. Outputs are kcal. calibrated stays false.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    try:
        return gibbs_helmholtz_report(
            body.get("t_c"),
            body.get("tm_c"),
            body.get("delta_h"),
            body.get("delta_cp"),
            units="kcal" if "units" not in body else body.get("units"),
            delta_h_sigma=body.get("delta_h_sigma"),
            delta_cp_sigma=body.get("delta_cp_sigma"),
            tm_sigma_c=body.get("tm_sigma_c"),
        )
    except ThermoInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stability/thermo/curves")
async def post_stability_thermo_curves(request: Request) -> dict[str, Any]:
    """ΔG(Tm) from Tm, and curves only when ΔHcal and ΔCp are posted.

    The body is the whole input. Nothing is read from the literature
    file and nothing is written back to it. A finite Tm with missing
    ΔHcal or ΔCp returns ΔG(Tm) = 0 and an empty curve. A non-finite
    number is HTTP 400. ΔH, ΔS, and ΔCp are not filled in.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    curve_kwargs: dict[str, Any] = {}
    if "t_min_c" in body and body.get("t_min_c") is not None:
        curve_kwargs["t_min_c"] = body.get("t_min_c")
    if "t_max_c" in body and body.get("t_max_c") is not None:
        curve_kwargs["t_max_c"] = body.get("t_max_c")
    if "n_points" in body and body.get("n_points") is not None:
        curve_kwargs["n_points"] = body.get("n_points")
    if "units" in body:
        curve_kwargs["units"] = body.get("units")
    try:
        return gibbs_helmholtz_curves(
            body.get("tm_c"),
            body.get("delta_h"),
            body.get("delta_cp"),
            **curve_kwargs,
        )
    except ThermoInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/api/stability/thermo/effective")
async def post_effective_enthalpy(request: Request) -> dict[str, Any]:
    """ΔH_eff and ΔG(T) under the explicit assumption ΔCp = 0.

    Body: tm_c, delta_g_ref, t_ref_c, optional units ("kcal" or "kJ"),
    optional delta_g_sigma and tm_sigma_c, and optional t_min_c,
    t_max_c, n_points. Temperatures are °C. Outputs are kcal.
    A missing anchor returns only ΔG(Tm) = 0.
    Tm equal to the anchor temperature is HTTP 400: ΔH is not
    identifiable. delta_h and delta_cp in the body are ignored.
    They belong to the full Gibbs–Helmholtz route and are not
    replaced by ΔH_eff. A 95% band is returned only when both
    sigmas are supplied. A null sigma is not treated as zero.
    calibrated stays false.
    """
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="JSON object required") from exc
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    curve_kwargs: dict[str, Any] = {}
    if "t_min_c" in body and body.get("t_min_c") is not None:
        curve_kwargs["t_min_c"] = body.get("t_min_c")
    if "t_max_c" in body and body.get("t_max_c") is not None:
        curve_kwargs["t_max_c"] = body.get("t_max_c")
    if "n_points" in body and body.get("n_points") is not None:
        curve_kwargs["n_points"] = body.get("n_points")
    if "units" in body:
        curve_kwargs["units"] = body.get("units")
    if "delta_g_sigma" in body:
        curve_kwargs["delta_g_sigma"] = body.get("delta_g_sigma")
    if "tm_sigma_c" in body:
        curve_kwargs["tm_sigma_c"] = body.get("tm_sigma_c")
    try:
        return effective_enthalpy_delta_cp_zero(
            body.get("tm_c"),
            body.get("delta_g_ref"),
            body.get("t_ref_c"),
            **curve_kwargs,
        )
    except ThermoInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/api/stability/thermo/prefill")
def get_thermo_prefill(
    series_id: str = Query(..., description="Named literature series id."),
    n: str = Query(..., description="Repeat count. Not interpolated."),
) -> dict[str, Any]:
    """Cited Tm and ΔG for one series and n. ΔH and ΔCp stay null if absent."""
    try:
        if not isinstance(series_id, str) or series_id.strip() == "":
            raise ThermoInputError("series_id is required")
        token = n.strip()
        if token.startswith("-"):
            digits = token[1:]
            negative = True
        else:
            digits = token
            negative = False
        if digits == "" or not digits.isdigit():
            raise ThermoInputError("n must be an integer")
        n_repeats = -int(digits) if negative else int(digits)
        return thermo_prefill(series_id.strip(), n_repeats)
    except ThermoInputError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
