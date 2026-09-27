"""Thermal gate: compare a cited melting temperature to the assay temperature.

This function does not define a Tm(n) equation. It does not interpolate
between repeat counts and it does not extend a measured Tm past the cited
repeat range. A missing measurement stays missing.

Rows are used as supplied. ``data_class`` is kept on each row for provenance
and is not a filter. Only rows whose ``observable`` is ``Tm_C`` can set
``tm_C``. A ``delta_G`` row is never converted into a melting temperature.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

_TM_OBSERVABLE = "Tm_C"
_NO_TM_REASON = "no Tm_C rows"
_NO_INTERPOLATION_REASON = "no measurement at this n; interpolation is not implemented"


@dataclass(frozen=True)
class ThermalRow:
    """One thermal observation passed in by the caller.

    ``value`` is whatever number the caller attached to ``observable``.
    This type does not claim the number is a literature measurement.
    """

    n_repeats: int
    observable: str
    value: float
    units: str
    uncertainty: float | None
    data_class: str


@dataclass(frozen=True)
class ThermalGateResult:
    """Outcome of comparing a matched Tm to the assay temperature.

    ``interval_low`` and ``interval_high`` are the envelope of the matched
    rows, not a pooled standard deviation. They are ``None`` when no Tm is
    reported.
    """

    state: Literal["pass", "fail", "extrapolated", "omitted"]
    tm_C: float | None
    interval_low: float | None
    interval_high: float | None
    n_repeats: int
    reason: str


def _half_width(uncertainty: float | None) -> float:
    """Row half-width. A missing uncertainty contributes zero width."""
    if uncertainty is None:
        return 0.0
    return uncertainty


def thermal_gate(
    n_repeats: int,
    t_assay_C: float,
    rows: Sequence[ThermalRow],
) -> ThermalGateResult:
    """Gate ``n_repeats`` using cited ``Tm_C`` rows only.

    Parameters
    ----------
    n_repeats:
        Repeat count requested for the design.
    t_assay_C:
        Assay temperature in degrees Celsius. Compared with the numeric
        ``Tm_C`` value. This function does not convert units.
    rows:
        Thermal observations. Every row is eligible. Rows whose observable
        is not ``Tm_C`` do not supply a melting temperature.

    Returns
    -------
    ThermalGateResult
        ``pass`` when the matched Tm is strictly greater than ``t_assay_C``.
        ``fail`` when that Tm is less than or equal to ``t_assay_C``.
        ``extrapolated`` when ``n_repeats`` is outside the inclusive min/max
        of cited ``Tm_C`` repeat counts. No Tm is filled in by extending
        the series.
        ``omitted`` when there is no ``Tm_C`` row, or when ``n_repeats``
        lies between measured repeat counts. Interpolation is not
        implemented, so a gap stays a gap.
    """
    tm_rows = [row for row in rows if row.observable == _TM_OBSERVABLE]
    if not tm_rows:
        return ThermalGateResult(
            state="omitted",
            tm_C=None,
            interval_low=None,
            interval_high=None,
            n_repeats=n_repeats,
            reason=_NO_TM_REASON,
        )

    cited_repeats = [row.n_repeats for row in tm_rows]
    cited_low = min(cited_repeats)
    cited_high = max(cited_repeats)
    if n_repeats < cited_low or n_repeats > cited_high:
        return ThermalGateResult(
            state="extrapolated",
            tm_C=None,
            interval_low=None,
            interval_high=None,
            n_repeats=n_repeats,
            reason=(
                f"n={n_repeats} is outside the cited repeat range "
                f"[{cited_low}, {cited_high}]"
            ),
        )

    matched = [row for row in tm_rows if row.n_repeats == n_repeats]
    if not matched:
        return ThermalGateResult(
            state="omitted",
            tm_C=None,
            interval_low=None,
            interval_high=None,
            n_repeats=n_repeats,
            reason=_NO_INTERPOLATION_REASON,
        )

    tm_C = sum(row.value for row in matched) / len(matched)
    interval_low = min(row.value - _half_width(row.uncertainty) for row in matched)
    interval_high = max(row.value + _half_width(row.uncertainty) for row in matched)
    if tm_C > t_assay_C:
        state: Literal["pass", "fail"] = "pass"
        relation = "strictly greater than"
    else:
        state = "fail"
        relation = "less than or equal to"
    return ThermalGateResult(
        state=state,
        tm_C=tm_C,
        interval_low=interval_low,
        interval_high=interval_high,
        n_repeats=n_repeats,
        reason=(
            f"matched Tm_C {tm_C} C is {relation} assay temperature {t_assay_C} C"
        ),
    )
