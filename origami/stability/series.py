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

from dataclasses import dataclass
from pathlib import Path

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

# Same Table I column as the default Tm series: Gibbs–Helmholtz unfolding
# ΔG at 10°C, positive as printed. Not a second pass/fail rule.
_DELTA_G_COMPANION: dict[str, dict[str, object]] = {
    PHILLIPS_2012_CTPRA_DSC: {
        "doi": "10.1002/pro.2018",
        "observable": "delta_G",
        "method": "DSC",
        "buffer": "50 mM phosphate",
        "pH": 7.0,
        "construct_family": "CTPRa",
    }
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


def delta_g_at_n(
    series_id: str,
    n_repeats: int,
    path: Path | None = None,
) -> ThermalObservation | None:
    """Unfolding ΔG from the same table as ``series_id``, if that column exists.

    Only the Phillips 2012 CTPRa DSC series has a companion ΔG column, and
    those values are positive as printed (Gibbs–Helmholtz, 10°C). This does
    not flip signs from other papers and does not decide pass or fail.
    A repeat count with no ΔG row returns None.
    """
    spec = _DELTA_G_COMPANION.get(series_id)
    if spec is None:
        return None
    table_path = literature_table_path() if path is None else Path(path)
    rows = load_thermal_table(table_path, allow_synthetic=False)
    pH = spec["pH"]
    matched = select_thermal_series(
        rows,
        doi=str(spec["doi"]),
        observable=str(spec["observable"]),
        method=str(spec["method"]),
        buffer=str(spec["buffer"]),
        pH=None if pH is None else float(pH),
        construct_family_name=str(spec["construct_family"]),
    )
    at_n = [row for row in matched if row.n_repeats == n_repeats]
    if len(at_n) != 1:
        return None
    return at_n[0]
