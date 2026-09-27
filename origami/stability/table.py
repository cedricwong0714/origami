"""Load a literature thermal table from caller-supplied JSON.

This module does not store melting temperatures, folding free energies,
or any other biological constant. Every number is taken from the file
the caller passes in. Units are recorded as stated and are not converted.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_OBSERVABLES = ("Tm_C", "delta_G")
_DATA_CLASSES = ("literature", "synthetic_fixture")
# Unit token required when observable is Tm_C. This is a label, not a temperature.
_TM_UNIT = "C"

# Absent, null, or blank values of these fields are import errors.
_REQUIRED_PRESENT = (
    "doi",
    "n_repeats",
    "value",
    "units",
    "observable",
    "data_class",
)
_STRING_FIELDS = (
    "citation",
    "construct",
    "method",
    "buffer",
    "figure_or_table",
)


@dataclass(frozen=True)
class ThermalObservation:
    """One thermal observation read from a literature or fixture row.

    ``value`` and ``uncertainty`` use ``units`` as written on the row.
    This type does not convert units and does not fill in a missing value.
    """

    record_id: str
    doi: str
    citation: str
    year: int
    construct: str
    n_repeats: int
    observable: Literal["Tm_C", "delta_G"]
    value: float
    units: str
    uncertainty: float | None
    method: str
    buffer: str
    pH: float | None
    figure_or_table: str
    peer_reviewed: bool
    data_class: Literal["literature", "synthetic_fixture"]


def load_thermal_table(
    path: Path,
    *,
    allow_synthetic: bool = False,
) -> list[ThermalObservation]:
    """Load thermal observations from a JSON file.

    The file may be a JSON list of row objects or an object
    ``{"rows": [...]}``. An empty file and ``{"rows": []}`` both return
    an empty list.

    Rows with ``data_class`` ``synthetic_fixture`` are omitted when
    ``allow_synthetic`` is false. They are kept, in file order, when
    ``allow_synthetic`` is true. A synthetic row is not an error by itself.

    Parameters
    ----------
    path:
        JSON file to read.
    allow_synthetic:
        When false, return only rows whose ``data_class`` is ``literature``.

    Returns
    -------
    list[ThermalObservation]
        Observations in file order, after the synthetic-row filter.

    Raises
    ------
    ValueError
        If ``doi``, ``n_repeats``, ``value``, ``units``, ``observable``,
        or ``data_class`` is missing. The message names ``record_id``.
        Also raised when ``observable`` is not ``Tm_C`` or ``delta_G``,
        when ``n_repeats`` is less than 1, when a ``Tm_C`` row does not
        use units ``C``, or when a ``delta_G`` row has an empty units
        string. Units are not converted.
    """
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    if text.strip() == "":
        return []

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"thermal table {file_path} is not valid JSON") from exc

    rows = _extract_rows(parsed, file_path)
    observations: list[ThermalObservation] = []
    for index, row in enumerate(rows):
        observation = _observation_from_row(index, row)
        if observation.data_class == "synthetic_fixture" and not allow_synthetic:
            continue
        observations.append(observation)
    return observations


def _extract_rows(parsed: object, path: Path) -> list[object]:
    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict) and "rows" in parsed:
        rows = parsed["rows"]
        if isinstance(rows, list):
            return rows
        raise ValueError(f"thermal table {path}: 'rows' must be a list")
    raise ValueError(
        f"thermal table {path} must be a JSON list or an object with a 'rows' list"
    )


def _observation_from_row(index: int, row: object) -> ThermalObservation:
    if not isinstance(row, dict):
        raise ValueError(f"thermal table row {index} must be an object")

    record_id = _record_id(index, row)
    _reject_missing_required(record_id, row)

    observable = _observable(record_id, row["observable"])
    data_class = _data_class(record_id, row["data_class"])
    n_repeats = _n_repeats(record_id, row["n_repeats"])
    units = _units(record_id, observable, row["units"])
    value = _finite_float(record_id, "value", row["value"])
    year = _year(record_id, row)
    uncertainty = _optional_float(record_id, "uncertainty", row)
    pH = _optional_float(record_id, "pH", row)
    peer_reviewed = _peer_reviewed(record_id, row)
    strings = {field: _required_text(record_id, row, field) for field in _STRING_FIELDS}

    return ThermalObservation(
        record_id=record_id,
        doi=_required_text(record_id, row, "doi"),
        citation=strings["citation"],
        year=year,
        construct=strings["construct"],
        n_repeats=n_repeats,
        observable=observable,
        value=value,
        units=units,
        uncertainty=uncertainty,
        method=strings["method"],
        buffer=strings["buffer"],
        pH=pH,
        figure_or_table=strings["figure_or_table"],
        peer_reviewed=peer_reviewed,
        data_class=data_class,
    )


def _record_id(index: int, row: dict) -> str:
    if "record_id" not in row or row["record_id"] is None:
        raise ValueError(f"thermal table row {index}: missing required field record_id")
    record_id = row["record_id"]
    if not isinstance(record_id, str) or record_id.strip() == "":
        raise ValueError(
            f"thermal table row {index}: record_id must be a non-empty string"
        )
    return record_id


def _reject_missing_required(record_id: str, row: dict) -> None:
    """Fail when a field the caller must supply was omitted.

    ``doi``, ``n_repeats``, ``value``, ``units``, ``observable``, and
    ``data_class`` are never defaulted. A missing or null value names
    both the record and the field.
    """
    for field in _REQUIRED_PRESENT:
        if field not in row or row[field] is None:
            raise ValueError(f"record {record_id}: missing required field {field}")
        if isinstance(row[field], str) and row[field].strip() == "":
            raise ValueError(f"record {record_id}: missing required field {field}")


def _observable(record_id: str, raw: object) -> Literal["Tm_C", "delta_G"]:
    if raw == "Tm_C":
        return "Tm_C"
    if raw == "delta_G":
        return "delta_G"
    raise ValueError(
        f"record {record_id}: observable must be one of {list(_OBSERVABLES)}, "
        f"got {raw!r}"
    )


def _data_class(
    record_id: str,
    raw: object,
) -> Literal["literature", "synthetic_fixture"]:
    if raw == "literature":
        return "literature"
    if raw == "synthetic_fixture":
        return "synthetic_fixture"
    raise ValueError(
        f"record {record_id}: data_class must be one of {list(_DATA_CLASSES)}, "
        f"got {raw!r}"
    )


def _n_repeats(record_id: str, raw: object) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"record {record_id}: n_repeats must be an integer")
    if raw < 1:
        raise ValueError(f"record {record_id}: n_repeats must be at least 1, got {raw}")
    return raw


def _units(record_id: str, observable: Literal["Tm_C", "delta_G"], raw: object) -> str:
    if not isinstance(raw, str):
        raise ValueError(f"record {record_id}: units must be a string")
    if observable == "Tm_C":
        if raw != _TM_UNIT:
            raise ValueError(
                f"record {record_id}: units for Tm_C must be 'C', got {raw!r}"
            )
        return raw
    if raw.strip() == "":
        raise ValueError(
            f"record {record_id}: units for delta_G must be stated and non-empty"
        )
    return raw


def _finite_float(record_id: str, field: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"record {record_id}: {field} must be a number")
    value = float(raw)
    if not math.isfinite(value):
        raise ValueError(f"record {record_id}: {field} must be finite, got {raw!r}")
    return value


def _year(record_id: str, row: dict) -> int:
    if "year" not in row or row["year"] is None:
        raise ValueError(f"record {record_id}: missing required field year")
    raw = row["year"]
    if isinstance(raw, bool) or not isinstance(raw, int):
        raise ValueError(f"record {record_id}: year must be an integer")
    return raw


def _optional_float(record_id: str, field: str, row: dict) -> float | None:
    if field not in row:
        raise ValueError(f"record {record_id}: missing required field {field}")
    raw = row[field]
    if raw is None:
        return None
    return _finite_float(record_id, field, raw)


def _peer_reviewed(record_id: str, row: dict) -> bool:
    if "peer_reviewed" not in row or row["peer_reviewed"] is None:
        raise ValueError(f"record {record_id}: missing required field peer_reviewed")
    raw = row["peer_reviewed"]
    if not isinstance(raw, bool):
        raise ValueError(f"record {record_id}: peer_reviewed must be a boolean")
    return raw


def _required_text(record_id: str, row: dict, field: str) -> str:
    if field not in row or row[field] is None:
        raise ValueError(f"record {record_id}: missing required field {field}")
    raw = row[field]
    if not isinstance(raw, str) or raw.strip() == "":
        raise ValueError(f"record {record_id}: {field} must be a non-empty string")
    return raw
