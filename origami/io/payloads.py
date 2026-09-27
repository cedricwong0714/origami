"""Import caller-supplied protein physical properties.

This module does not measure, estimate, or fill in radii, linker sigmas,
dissociation constants, or sequences. Every physical number must already be
present on the input row. Structure identifiers are stored as given; this
module does not fetch PDB entries or generate coordinates.

An optional fusion-context group (``external_ddg`` and its units, source,
and tool) is stored only when the caller supplied the whole group. This
module does not call FoldX, CamSol, Aggrescan, or any other tool, and it
does not apply a cutoff to ``external_ddg``.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_REQUIRED_FIELDS = (
    "payload_id",
    "role",
    "fusion_terminus",
    "repeat_index",
    "radius_A",
    "linker_sigma_A",
)
_PHYSICAL_FIELDS = ("radius_A", "linker_sigma_A")
_FUSION_CONTEXT_FIELDS = (
    "external_ddg",
    "external_ddg_units",
    "external_ddg_source",
    "external_tool",
)
_TERMINI = ("N", "C")


@dataclass(frozen=True)
class PayloadRecord:
    """One payload's caller-supplied physical properties.

    ``repeat_index`` is the 0-based docking repeat on the scaffold.
    ``radius_A`` and ``linker_sigma_A`` are in angstroms and must be provided
    by the caller. They are not estimated here.

    ``external_ddg``, ``external_ddg_units``, ``external_ddg_source``, and
    ``external_tool`` are one optional annotation. All four are None when
    the caller omitted them. When the caller supplies the annotation, all
    four are stored as given. ``external_ddg`` is not compared to a cutoff.
    """

    payload_id: str
    role: str
    fusion_terminus: Literal["N", "C"]
    repeat_index: int
    radius_A: float
    linker_sigma_A: float
    structure_id: str | None = None
    external_ddg: float | None = None
    external_ddg_units: str | None = None
    external_ddg_source: str | None = None
    external_tool: str | None = None


def load_payloads(rows: list[dict]) -> list[PayloadRecord]:
    """Build payload records from row dicts.

    Each row must include ``payload_id``, ``role``, ``fusion_terminus``,
    ``repeat_index``, ``radius_A``, and ``linker_sigma_A``. ``structure_id``
    is optional.

    ``external_ddg``, ``external_ddg_units``, ``external_ddg_source``, and
    ``external_tool`` are optional as a group. If every one of them is
    absent or null, all four are stored as None. If any one is present,
    all four must be present and non-empty. The number is stored as a
    float and is not thresholded.

    Raises
    ------
    ValueError
        If ``radius_A`` or ``linker_sigma_A`` is missing or null, if either
        is not strictly positive, if ``repeat_index`` is negative, or if
        ``fusion_terminus`` is not ``N`` or ``C``. The error names the
        ``payload_id`` and the field that failed. The same error is raised
        when part of the external fusion-context group is missing or blank.
    """
    if not isinstance(rows, list):
        raise ValueError("payload rows must be a list of objects")

    records: list[PayloadRecord] = []
    for index, row in enumerate(rows):
        records.append(_record_from_row(index, row))
    return records


def load_payloads_json(path: Path) -> list[PayloadRecord]:
    """Load payload rows from a JSON file.

    The file must contain a JSON array of objects accepted by
    ``load_payloads``. Missing physical properties are not filled in.
    """
    file_path = Path(path)
    try:
        parsed = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"payload file {file_path} is not valid JSON") from exc
    if not isinstance(parsed, list):
        raise ValueError(f"payload file {file_path} must contain a JSON array")
    return load_payloads(parsed)


def _record_from_row(index: int, row: object) -> PayloadRecord:
    if not isinstance(row, dict):
        raise ValueError(f"payload row {index} must be an object")

    payload_id = _payload_id(index, row)
    _reject_missing_physical_fields(payload_id, row)
    for field in _REQUIRED_FIELDS:
        if field not in row or row[field] is None:
            raise ValueError(f"payload {payload_id}: missing required field {field}")

    role = _role(payload_id, row["role"])
    fusion_terminus = _fusion_terminus(payload_id, row["fusion_terminus"])
    repeat_index = _repeat_index(payload_id, row["repeat_index"])
    radius_A = _positive_angstrom(payload_id, "radius_A", row["radius_A"])
    linker_sigma_A = _positive_angstrom(
        payload_id, "linker_sigma_A", row["linker_sigma_A"]
    )
    structure_id = _structure_id(payload_id, row)
    external_ddg, external_ddg_units, external_ddg_source, external_tool = (
        _fusion_context(payload_id, row)
    )
    return PayloadRecord(
        payload_id=payload_id,
        role=role,
        fusion_terminus=fusion_terminus,
        repeat_index=repeat_index,
        radius_A=radius_A,
        linker_sigma_A=linker_sigma_A,
        structure_id=structure_id,
        external_ddg=external_ddg,
        external_ddg_units=external_ddg_units,
        external_ddg_source=external_ddg_source,
        external_tool=external_tool,
    )


def _payload_id(index: int, row: dict) -> str:
    if "payload_id" not in row or row["payload_id"] is None:
        raise ValueError(f"payload row {index}: missing required field payload_id")
    payload_id = row["payload_id"]
    if not isinstance(payload_id, str) or payload_id.strip() == "":
        raise ValueError(
            f"payload row {index}: payload_id must be a non-empty string"
        )
    return payload_id


def _reject_missing_physical_fields(payload_id: str, row: dict) -> None:
    """Fail before any other value checks when a physical field was omitted.

    Radius and linker width are never defaulted. A missing or null value is
    an import error that names both the payload and the field.
    """
    for field in _PHYSICAL_FIELDS:
        if field not in row or row[field] is None:
            raise ValueError(f"payload {payload_id}: missing required field {field}")


def _role(payload_id: str, role: object) -> str:
    if not isinstance(role, str) or role.strip() == "":
        raise ValueError(f"payload {payload_id}: role must be a non-empty string")
    return role


def _fusion_terminus(payload_id: str, terminus: object) -> Literal["N", "C"]:
    if terminus not in _TERMINI:
        raise ValueError(
            f"payload {payload_id}: fusion_terminus must be one of {list(_TERMINI)}, "
            f"got {terminus!r}"
        )
    if terminus == "N":
        return "N"
    return "C"


def _repeat_index(payload_id: str, repeat_index: object) -> int:
    if isinstance(repeat_index, bool) or not isinstance(repeat_index, int):
        raise ValueError(
            f"payload {payload_id}: repeat_index must be an integer >= 0"
        )
    if repeat_index < 0:
        raise ValueError(
            f"payload {payload_id}: repeat_index must be >= 0, got {repeat_index}"
        )
    return repeat_index


def _positive_angstrom(payload_id: str, field: str, raw: object) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"payload {payload_id}: {field} must be a number greater than 0")
    value = float(raw)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(
            f"payload {payload_id}: {field} must be greater than 0, got {raw!r}"
        )
    return value


def _fusion_context(
    payload_id: str, row: dict
) -> tuple[float | None, str | None, str | None, str | None]:
    """Read the optional external fusion-context group.

    Absent and null are the same: the caller did not supply that field.
    When every field in the group is absent or null, the group is omitted
    and each stored value is None. A single supplied field makes the whole
    group required. Blank strings are not a supplied value, so they are
    reported as missing. ``external_ddg`` is converted to float and kept,
    including zero and negative values. It is not compared to a cutoff.
    """
    raw = {
        field: row[field] if field in row else None for field in _FUSION_CONTEXT_FIELDS
    }
    if all(value is None for value in raw.values()):
        return None, None, None, None

    missing = [field for field, value in raw.items() if _is_blank(value)]
    if missing:
        raise ValueError(
            f"payload {payload_id}: missing required field {', '.join(missing)}"
        )

    return (
        _external_ddg(payload_id, raw["external_ddg"]),
        _nonempty_text(payload_id, "external_ddg_units", raw["external_ddg_units"]),
        _nonempty_text(payload_id, "external_ddg_source", raw["external_ddg_source"]),
        _nonempty_text(payload_id, "external_tool", raw["external_tool"]),
    )


def _is_blank(value: object) -> bool:
    """True when a fusion-context value was omitted or is only whitespace."""
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def _external_ddg(payload_id: str, raw: object) -> float:
    """Store a caller-supplied ddg number without applying a cutoff.

    Zero and negative values are kept. This function does not decide
    whether the number is stabilizing, destabilizing, or in range.
    """
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise ValueError(f"payload {payload_id}: external_ddg must be a number")
    return float(raw)


def _nonempty_text(payload_id: str, field: str, raw: object) -> str:
    if not isinstance(raw, str) or raw.strip() == "":
        raise ValueError(f"payload {payload_id}: {field} must be a non-empty string")
    return raw


def _structure_id(payload_id: str, row: dict) -> str | None:
    if "structure_id" not in row:
        return None
    structure_id = row["structure_id"]
    if structure_id is None:
        return None
    if not isinstance(structure_id, str):
        raise ValueError(
            f"payload {payload_id}: structure_id must be a string or null"
        )
    return structure_id
