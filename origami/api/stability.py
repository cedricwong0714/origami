"""HTTP lookup of the existing literature thermal panel.

This module does not fit ``Tm(n)``, does not interpolate, and does not
average series. Each row is whatever ``stability_panel`` already
returns. ``delta_G`` is carried on the row and is not a pass/fail rule.
``calibrated`` stays false.

The default comparison temperature is
``DEFAULT_OPERATING_TEMPERATURE_C`` (37 C). That value is an *E. coli*
operating assumption. It is not a temperature reported by Phillips et
al. 2012.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from origami.drylab import STABILITY_SERIES, stability_panel
from origami.stability.series import (
    DEFAULT_OPERATING_TEMPERATURE_C,
    PHILLIPS_2012_CTPRA_DSC,
)

router = APIRouter()

# Confirmation lengths requested by the dry-lab screen. These are not
# a fitted Tm(n) grid. n=14 is outside the cited repeat range, so the
# thermal gate leaves its Tm empty.
_CONFIRM_N: frozenset[int] = frozenset({3, 8, 14})

_ASSAY_DESCRIPTION = (
    "Assay comparison temperature in degrees Celsius. "
    "The default, 37, is an E. coli operating assumption "
    "(DEFAULT_OPERATING_TEMPERATURE_C), not a DSC setpoint "
    "from Phillips et al. 2012."
)

_CONFIRM_NOTE = (
    "n=14 Tm is extrapolated and no Tm(n) was fit. "
    "No interpolation. Series stay separate and are never averaged. "
    "delta_G does not set pass/fail. calibrated stays false. "
    "The default comparison temperature 37 C is an E. coli operating "
    "assumption, not a temperature from Phillips et al. 2012. "
    f"Default series id: {PHILLIPS_2012_CTPRA_DSC}."
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
    """Keep one row per series at n = 3, 8, and 14.

    Four named series and three lengths are twelve rows. Rows are not
    merged across series. A count other than that means the panel was
    collapsed or duplicated, which this lookup must not do.
    """
    panel = literature_panel(t_assay_C)
    rows = [row for row in panel["rows"] if int(row["n_repeats"]) in _CONFIRM_N]
    expected = len(STABILITY_SERIES) * len(_CONFIRM_N)
    series_ids = [row["series_id"] for row in rows]
    keys = [(row["series_id"], int(row["n_repeats"])) for row in rows]
    if len(rows) != expected or len(keys) != len(set(keys)):
        raise HTTPException(
            status_code=500,
            detail=(
                "stability confirmation must keep one row per series "
                f"at n in {sorted(_CONFIRM_N)} "
                f"({len(STABILITY_SERIES)} series, {expected} rows). "
                f"Got {len(rows)} rows."
            ),
        )
    if set(series_ids) != set(STABILITY_SERIES):
        raise HTTPException(
            status_code=500,
            detail="stability confirmation dropped or merged a series",
        )
    return {
        "calibrated": False,
        "t_assay_C": panel["t_assay_C"],
        "default_series_id": PHILLIPS_2012_CTPRA_DSC,
        "rows": rows,
        "note": _CONFIRM_NOTE,
    }


@router.get("/api/stability/panel")
def get_stability_panel(
    t_assay_C: float = Query(
        default=DEFAULT_OPERATING_TEMPERATURE_C,
        description=_ASSAY_DESCRIPTION,
    ),
) -> dict[str, Any]:
    """Literature thermal panel for every named series and library n."""
    return literature_panel(t_assay_C)


@router.get("/api/stability/confirm")
def get_stability_confirm(
    t_assay_C: float = Query(
        default=DEFAULT_OPERATING_TEMPERATURE_C,
        description=_ASSAY_DESCRIPTION,
    ),
) -> dict[str, Any]:
    """n = 3, 8, and 14 from the literature panel, one row per series."""
    return literature_confirm(t_assay_C)
