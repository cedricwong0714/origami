"""Load the team-supplied CaM–M13 series. Sequences are not generated here."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

_DATA = Path(__file__).resolve().parents[2] / "data" / "constructs" / "team_cam_m13_series.json"


class ConstructError(ValueError):
    """The construct table cannot be used."""


def load_series(path: Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else _DATA
    try:
        doc = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConstructError(f"cannot read construct table: {exc}") from exc
    if not isinstance(doc, dict) or "constructs" not in doc:
        raise ConstructError("construct table missing constructs")
    for row in doc["constructs"]:
        seq = str(row["sequence"]).upper()
        digest = hashlib.sha256(seq.encode()).hexdigest()
        if digest != row["sequence_sha256"]:
            raise ConstructError(
                f"checksum mismatch for n={row['n_repeats']}. "
                "The amino-acid string was changed without updating the digest."
            )
    return doc


def construct_for_n(n_repeats: int) -> dict[str, Any]:
    doc = load_series()
    for row in doc["constructs"]:
        if int(row["n_repeats"]) == int(n_repeats):
            return row
    raise ConstructError(f"no team sequence for n={n_repeats}")
