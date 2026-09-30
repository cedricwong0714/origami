"""Select one published thermal series before the gate sees any rows.

The literature file stores several constructs, methods, and buffers.
``thermal_gate`` averages every ``Tm_C`` row that shares a repeat count.
That average is not a measurement. Callers must pick one series first.

A series is one DOI, one observable, one method, one buffer, one pH,
and one construct family. The family is the construct name with a
trailing repeat count removed: ``CTPRa10`` and ``CTPR3`` are different
families. ``CTPR2a`` keeps the letter because it is not a bare count.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from origami.stability.table import ThermalObservation, load_thermal_table

# Phillips et al. (2012) Protein Sci. 21:327-338, DOI 10.1002/pro.2018,
# Table I, DSC, 50 mM phosphate, pH 7.0. CTPRa only. CTPR rows in that
# same table are a different construct family and are not included.
# Citation text matches data/stability/ctpr_thermal_literature.json.
PHILLIPS_2012_CTPRA_DSC = "phillips2012_ctpra_dsc"
CORTAJARENA_2011_CTPRA_DSC = "cortajarena2011_ctpra_dsc"
PHILLIPS_2012_CTPRA_CD = "phillips2012_ctpra_cd"
PHILLIPS_2012_CTPR_DSC = "phillips2012_ctpr_dsc"

# Operating temperature for the design screen when the caller does not
# supply one. Phillips et al. 2012 Table I reports melting temperatures,
# not this value. 37 C is the conventional E. coli incubation temperature
# used here as the comparison point. It is an operating assumption, not
# a DSC setpoint from that paper.
DEFAULT_OPERATING_TEMPERATURE_C = 37.0

_NAMED_SERIES: dict[str, dict[str, object]] = {
    PHILLIPS_2012_CTPRA_DSC: {
        "doi": "10.1002/pro.2018",
        "observable": "Tm_C",
        "method": "DSC",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPRa",
    },
    CORTAJARENA_2011_CTPRA_DSC: {
        "doi": "10.1002/pro.564",
        "observable": "Tm_C",
        "method": "DSC",
        "buffer": "150 mM NaCl, 50 mM phosphate",
        "pH": 6.8,
        "construct_family": "CTPRa",
    },
    PHILLIPS_2012_CTPRA_CD: {
        "doi": "10.1002/pro.2018",
        "observable": "Tm_C",
        "method": "CD",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPRa",
    },
    PHILLIPS_2012_CTPR_DSC: {
        "doi": "10.1002/pro.2018",
        "observable": "Tm_C",
        "method": "DSC",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPR",
    },
}

# Same Table I column as the DSC Tm series: Gibbs–Helmholtz unfolding
# ΔG at 10°C, positive as printed. Not a second pass/fail rule.
# ``larger_printed_value_is_more_stable`` is true only because that column
# is an unfolding free energy printed as a positive number. A larger
# printed value is a larger unfolding ΔG in this table. The flag is not
# a general rule for chemical-denaturation tables whose signs differ.
_DELTA_G_COMPANION: dict[str, dict[str, object]] = {
    PHILLIPS_2012_CTPRA_DSC: {
        "doi": "10.1002/pro.2018",
        "observable": "delta_G",
        "method": "DSC",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPRa",
        "larger_printed_value_is_more_stable": True,
    },
    PHILLIPS_2012_CTPR_DSC: {
        "doi": "10.1002/pro.2018",
        "observable": "delta_G",
        "method": "DSC",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPR",
        "larger_printed_value_is_more_stable": True,
    },
}


@dataclass(frozen=True)
class ThermalSeriesKey:
    """Identity of one experimental series. Not an average across papers."""

    doi: str
    observable: str
    method: str
    buffer: str
    pH: float | None
    construct_family: str


def construct_family(construct: str) -> str:
    """Drop a trailing repeat count. ``CTPRa10`` -> ``CTPRa``, ``CTPR2a`` stays."""
    if not isinstance(construct, str) or construct.strip() == "":
        raise ValueError("construct must be a non-empty string")
    end = len(construct)
    while end > 0 and construct[end - 1].isdigit():
        end -= 1
    family = construct[:end]
    if family == "":
        raise ValueError(f"construct {construct!r} is only a repeat count")
    return family


def series_key(row: ThermalObservation) -> ThermalSeriesKey:
    return ThermalSeriesKey(
        doi=row.doi,
        observable=row.observable,
        method=row.method,
        buffer=row.buffer,
        pH=row.pH,
        construct_family=construct_family(row.construct),
    )


def literature_table_path() -> Path:
    """Repo path of the checked-in CTPR thermal table."""
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "stability"
        / "ctpr_thermal_literature.json"
    )


def list_series(rows: list[ThermalObservation]) -> list[ThermalSeriesKey]:
    """Unique series in file order."""
    seen: list[ThermalSeriesKey] = []
    for row in rows:
        key = series_key(row)
        if key not in seen:
            seen.append(key)
    return seen


def select_thermal_series(
    rows: list[ThermalObservation],
    *,
    doi: str,
    observable: str,
    method: str,
    buffer: str,
    pH: float | None,
    construct_family_name: str,
) -> list[ThermalObservation]:
    """Return rows from one series. An empty match raises."""
    wanted = ThermalSeriesKey(
        doi=doi,
        observable=observable,
        method=method,
        buffer=buffer,
        pH=pH,
        construct_family=construct_family_name,
    )
    matched = [row for row in rows if series_key(row) == wanted]
    if not matched:
        raise ValueError(
            "no thermal rows match series "
            f"doi={doi} observable={observable} method={method} "
            f"buffer={buffer!r} pH={pH} family={construct_family_name}"
        )
    return matched


def assert_single_tm_series(rows: list[ThermalObservation]) -> list[ThermalObservation]:
    """Refuse a table whose melting temperatures come from more than one series.

    ``delta_G`` rows are ignored by the thermal gate and do not count.
    """
    tm_rows = [row for row in rows if row.observable == "Tm_C"]
    keys = list_series(tm_rows)
    if len(keys) == 0:
        return rows
    if len(keys) > 1:
        shown = ", ".join(
            f"{key.construct_family} {key.method} {key.doi} pH={key.pH}" for key in keys
        )
        raise ValueError(
            "thermal table mixes multiple Tm series. Pass thermal_series "
            f"to choose one. Found: {shown}"
        )
    return rows


def load_named_series(
    series_id: str,
    path: Path | None = None,
) -> list[ThermalObservation]:
    """Load one named Tm series from the literature table.

    Built-in ids are the Phillips 2012 CTPRa DSC default, the Cortajarena
    2011 CTPRa DSC series, the Phillips 2012 CTPRa CD series, and the
    Phillips 2012 CTPR DSC series. They are not averaged together.
    """
    spec = _NAMED_SERIES.get(series_id)
    if spec is None:
        known = ", ".join(sorted(_NAMED_SERIES))
        raise ValueError(f"unknown thermal series {series_id!r}. Known: {known}")
    table_path = literature_table_path() if path is None else Path(path)
    rows = load_thermal_table(table_path, allow_synthetic=False)
    pH = spec["pH"]
    if pH is not None and not isinstance(pH, (int, float)):
        raise RuntimeError("named series pH must be numeric or null")
    return select_thermal_series(
        rows,
        doi=str(spec["doi"]),
        observable=str(spec["observable"]),
        method=str(spec["method"]),
        buffer=str(spec["buffer"]),
        pH=None if pH is None else float(pH),
        construct_family_name=str(spec["construct_family"]),
    )


def companion_delta_g_rows(
    series_id: str,
    path: Path | None = None,
) -> list[ThermalObservation]:
    """Unfolding ΔG rows for one named series, or an empty list.

    Cortajarena 2011 has no companion column. This does not borrow
    ΔG rows from another DOI, method, or construct family.
    """
    return _companion_rows(series_id, path)


def _companion_rows(
    series_id: str,
    path: Path | None = None,
) -> list[ThermalObservation]:
    """ΔG rows for one named companion. An unknown or absent series is empty.

    An empty match does not raise. A custom table that has melting
    temperatures and no ΔG column stays a Tm table.
    """
    spec = _DELTA_G_COMPANION.get(series_id)
    if spec is None:
        return []
    table_path = literature_table_path() if path is None else Path(path)
    rows = load_thermal_table(table_path, allow_synthetic=False)
    pH = spec["pH"]
    if pH is not None and not isinstance(pH, (int, float)):
        raise RuntimeError("named series pH must be numeric or null")
    wanted = ThermalSeriesKey(
        doi=str(spec["doi"]),
        observable=str(spec["observable"]),
        method=str(spec["method"]),
        buffer=str(spec["buffer"]),
        pH=None if pH is None else float(pH),
        construct_family=str(spec["construct_family"]),
    )
    return [row for row in rows if series_key(row) == wanted]


def delta_g_at_n(
    series_id: str,
    n_repeats: int,
    path: Path | None = None,
) -> ThermalObservation | None:
    """Unfolding ΔG from the same table as ``series_id``, if that column exists.

    The Phillips 2012 CTPRa DSC series and the Phillips 2012 CTPR DSC series
    have companion ΔG columns. Those values are positive as printed
    (Gibbs–Helmholtz, 10°C). This does not flip signs from other papers
    and does not decide pass or fail. A repeat count with no single ΔG
    row returns None.
    """
    at_n = [row for row in _companion_rows(series_id, path) if row.n_repeats == n_repeats]
    if len(at_n) != 1:
        return None
    return at_n[0]


@dataclass(frozen=True)
class CitedDeltaGRank:
    """Lookup of the largest printed unfolding ΔG among eligible lengths.

    ``observation`` is set only when ``status`` is ``chosen``. A tie, a
    units mismatch, or a missing row does not pick a length and does not
    invent a value.
    """

    observation: ThermalObservation | None
    status: Literal["chosen", "no_companion", "not_rankable", "no_row", "mixed_units", "tie"]


def rank_printed_delta_g(
    rows: Sequence[ThermalObservation],
    eligible_n: Sequence[int],
    *,
    larger_printed_value_is_more_stable: bool,
) -> CitedDeltaGRank:
    """Largest printed ΔG among eligible lengths.

    ``larger_printed_value_is_more_stable`` must already have been decided
    by the caller from the source table. This function does not decide
    that a negative table should be flipped. It does not interpolate, it
    does not convert units, and it does not prefer a longer scaffold.
    Two eligible lengths with the same largest value are a tie.
    """
    if not larger_printed_value_is_more_stable:
        return CitedDeltaGRank(observation=None, status="not_rankable")
    eligible = set(eligible_n)
    by_n: dict[int, list[ThermalObservation]] = {}
    for row in rows:
        if row.observable != "delta_G":
            continue
        if row.n_repeats not in eligible:
            continue
        by_n.setdefault(row.n_repeats, []).append(row)
    singles = [group[0] for group in by_n.values() if len(group) == 1]
    if not singles:
        return CitedDeltaGRank(observation=None, status="no_row")
    units = {row.units for row in singles}
    if len(units) != 1:
        return CitedDeltaGRank(observation=None, status="mixed_units")
    largest = max(row.value for row in singles)
    winners = [row for row in singles if row.value == largest]
    if len(winners) != 1:
        return CitedDeltaGRank(observation=None, status="tie")
    return CitedDeltaGRank(observation=winners[0], status="chosen")


def rank_companion_delta_g(
    series_id: str,
    eligible_n: Sequence[int],
    path: Path | None = None,
) -> CitedDeltaGRank:
    """Largest printed unfolding ΔG among ``eligible_n`` for one companion.

    This is a lookup in the same column ``delta_g_at_n`` reads. If two
    eligible lengths share the largest printed value, the status is
    ``tie`` and no length is chosen. Chemical-denaturation series are
    not companions here.
    """
    spec = _DELTA_G_COMPANION.get(series_id)
    if spec is None:
        return CitedDeltaGRank(observation=None, status="no_companion")
    return rank_printed_delta_g(
        _companion_rows(series_id, path),
        eligible_n,
        larger_printed_value_is_more_stable=spec.get("larger_printed_value_is_more_stable")
        is True,
    )
