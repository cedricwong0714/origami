"""Plate-reader CSV import into SSDK observation rows.

Input is a long-format CSV, one row per well, with columns:
  well, construct, n_repeats, batch, role, rlu
``role`` is ``sample`` or ``blank``. ``rlu`` is raw luminescence in RLU.
Optional ``calcium_uM`` is free calcium in µM. When that column is
present, sample wells must fill it, and replicates are averaged only
when construct, repeat count, batch, and calcium all match. Blanks stay
per batch.

Processing is deterministic and explicit:
  1. Blank correction: for each batch, the mean RLU of that batch's blank
     wells is subtracted from every sample well in the same batch. A batch
     with samples but no blanks is rejected rather than left uncorrected.
  2. Replicates: sample wells sharing (construct, n_repeats, batch) are
     averaged. ``sigma`` is the standard error of the mean, using the
     unbiased sample SD (n - 1) divided by sqrt(n). With a single well the
     sigma is omitted (None), never invented.
  3. The input file SHA-256 is recorded so the rows trace to raw data.

Raw files are only read, never modified. Output units are blank-corrected RLU.
The blank correction does not model between-plate gain or furimazine decay;
those must be handled by the caller's normalization before intake.
"""

from __future__ import annotations

import csv
import hashlib
import io
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = ("well", "construct", "n_repeats", "batch", "role", "rlu")
NORMALIZATION_METHOD = "blank_subtracted_RLU"


class PlateReaderError(ValueError):
    """Raised when a plate-reader file cannot be imported safely."""


def _finite(value: str, label: str, line: int) -> float:
    try:
        x = float(value)
    except (TypeError, ValueError):
        raise PlateReaderError(f"line {line}: {label} {value!r} is not a number") from None
    if not math.isfinite(x):
        raise PlateReaderError(f"line {line}: {label} must be finite")
    return x


def parse_plate_csv(text: str, source: str, sha256: str | None = None) -> dict[str, Any]:
    """Parse CSV text into observation rows plus provenance."""
    reader = csv.DictReader(io.StringIO(text))
    missing = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
    if missing:
        raise PlateReaderError(f"missing required columns: {missing}")

    has_calcium = "calcium_uM" in (reader.fieldnames or [])
    blanks: dict[str, list[float]] = defaultdict(list)
    samples: dict[tuple[str, int, str, float | None], list[float]] = defaultdict(list)
    for line, row in enumerate(reader, start=2):
        role = (row["role"] or "").strip().lower()
        batch = (row["batch"] or "").strip()
        if not batch:
            raise PlateReaderError(f"line {line}: batch is empty")
        rlu = _finite(row["rlu"], "rlu", line)
        if rlu < 0:
            raise PlateReaderError(f"line {line}: rlu {rlu} is negative")
        if role == "blank":
            blanks[batch].append(rlu)
        elif role == "sample":
            n_f = _finite(row["n_repeats"], "n_repeats", line)
            if n_f != int(n_f) or n_f < 1:
                raise PlateReaderError(f"line {line}: n_repeats must be a positive integer")
            construct = (row["construct"] or "").strip()
            if not construct:
                raise PlateReaderError(f"line {line}: construct is empty")
            calcium = _sample_calcium(row, line, has_calcium)
            samples[(construct, int(n_f), batch, calcium)].append(rlu)
        else:
            raise PlateReaderError(f"line {line}: role must be 'sample' or 'blank', got {role!r}")

    if not samples:
        raise PlateReaderError("no sample wells found")

    out_rows: list[dict[str, Any]] = []
    for (construct, n_repeats, batch, calcium), values in sorted(
        samples.items(), key=_sample_sort_key
    ):
        if batch not in blanks:
            raise PlateReaderError(f"batch {batch!r} has sample wells but no blank wells")
        blank_mean = sum(blanks[batch]) / len(blanks[batch])
        corrected = [v - blank_mean for v in values]
        n = len(corrected)
        mean = sum(corrected) / n
        sigma: float | None = None
        if n >= 2:
            var = sum((v - mean) ** 2 for v in corrected) / (n - 1)
            sigma = math.sqrt(var) / math.sqrt(n)
            if sigma == 0.0:
                sigma = None
        out_rows.append(
            {
                "n_repeats": n_repeats,
                "y": mean,
                "sigma": sigma,
                "source": f"{source}:{construct}:{batch}:{_calcium_label(calcium)}",
                "construct": construct,
                "batch": batch,
                "calcium_uM": calcium,
                "n_wells": n,
                "blank_mean_rlu": blank_mean,
                "units": "RLU",
            }
        )
    return {
        "observations": out_rows,
        "normalization_method": NORMALIZATION_METHOD,
        "input_sha256": sha256,
        "source": source,
        "calibrated": False,
    }


def _sample_calcium(row: dict[str, str], line: int, has_calcium: bool) -> float | None:
    if not has_calcium:
        return None
    raw = (row.get("calcium_uM") or "").strip()
    if raw == "":
        raise PlateReaderError(f"line {line}: calcium_uM is empty")
    calcium = _finite(raw, "calcium_uM", line)
    if calcium < 0:
        raise PlateReaderError(f"line {line}: calcium_uM {calcium} is negative")
    return calcium


def _calcium_label(calcium: float | None) -> str:
    if calcium is None:
        return "no-calcium"
    return f"{calcium:g}uM"


def _sample_sort_key(
    item: tuple[tuple[str, int, str, float | None], list[float]],
) -> tuple[str, int, str, int, float]:
    construct, n_repeats, batch, calcium = item[0]
    # None sorts before any measured calcium. The pair (0, 0.0) is a
    # sort key, not a concentration.
    if calcium is None:
        return (construct, n_repeats, batch, 0, 0.0)
    return (construct, n_repeats, batch, 1, calcium)


def load_plate_csv(path: str | Path) -> dict[str, Any]:
    """Read a plate-reader CSV from disk (read-only) and parse it."""
    p = Path(path)
    raw = p.read_bytes()
    return parse_plate_csv(
        raw.decode("utf-8"), source=p.name, sha256=hashlib.sha256(raw).hexdigest()
    )
