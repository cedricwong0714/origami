"""Score a blank-corrected plate against checksummed scaffold freezes.

A row is compared only when its repeat count has a frozen file and its
``calcium_uM`` matches a luminescence key in that file. Contour, axial
span, and the Phillips length curve have no plate column, so they are
listed as untested. A row with no calcium is not compared to the
dose-response. The luminescence interval in the checked-in freezes is
still the ±30% placeholder. ``calibrated`` stays false.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from origami.lab.plate_reader import parse_plate_csv
from src.core.asset_paths import FROZEN_PREDICTIONS_DIR
from src.predictions.freeze import verify_frozen_checksum
from src.predictions.luminescence_interval import parameter_error_report


class FreezeCompareError(ValueError):
    """The plate cannot be scored against the frozen files."""


def compare_plate_csv(
    text: str,
    *,
    source: str = "plate.csv",
    sha256: str | None = None,
    frozen_dir: Path | None = None,
) -> dict[str, Any]:
    """Blank-correct ``text`` and score each row against ``scaffold-n{n}.json``."""
    plate = parse_plate_csv(text, source, sha256=sha256)
    directory = Path(frozen_dir) if frozen_dir is not None else FROZEN_PREDICTIONS_DIR
    loaded: dict[int, dict[str, Any]] = {}
    comparisons: list[dict[str, Any]] = []
    tested_keys: dict[int, set[str]] = {}
    for row in plate["observations"]:
        n_repeats = int(row["n_repeats"])
        frozen = _load_frozen(directory, n_repeats, loaded)
        comparisons.append(_score_row(row, frozen))
        if frozen is not None and comparisons[-1]["status"] == "compared":
            tested_keys.setdefault(n_repeats, set()).add(str(comparisons[-1]["frozen_key"]))
    untested = _untested(loaded, tested_keys)
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "normalization_method": plate["normalization_method"],
        "input_sha256": plate["input_sha256"],
        "source": plate["source"],
        "parameter_error": parameter_error_report(),
        "comparisons": comparisons,
        "untested_predictions": untested,
        "note": (
            "Within-interval uses the frozen bounds. For luminescence those "
            "bounds are the ±30% placeholder until ODE parameter sigmas exist. "
            "A row inside that band is not a validation."
        ),
    }


def _load_frozen(
    directory: Path,
    n_repeats: int,
    cache: dict[int, dict[str, Any]],
) -> dict[str, Any] | None:
    if n_repeats in cache:
        return cache[n_repeats]
    path = directory / f"scaffold-n{n_repeats}.json"
    if not path.is_file():
        return None
    if not verify_frozen_checksum(path):
        raise FreezeCompareError(
            f"Frozen prediction checksum mismatch for {path.name}. "
            "The file was not used."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["_path"] = str(path)
    cache[n_repeats] = payload
    return payload


def _score_row(row: dict[str, Any], frozen: dict[str, Any] | None) -> dict[str, Any]:
    base = {
        "construct": row["construct"],
        "n_repeats": row["n_repeats"],
        "batch": row["batch"],
        "calcium_uM": row.get("calcium_uM"),
        "observed": row["y"],
        "observed_units": row["units"],
        "observed_sigma": row.get("sigma"),
    }
    if frozen is None:
        base["status"] = "no_frozen_scaffold"
        base["detail"] = (
            f"No checksummed scaffold-n{row['n_repeats']}.json was found. "
            "The planned series files are n = 3, 8, and 14."
        )
        return base
    base["frozen_prediction_id"] = frozen.get("prediction_id")
    base["frozen_checksum"] = frozen.get("file_checksum")
    calcium = row.get("calcium_uM")
    if calcium is None:
        base["status"] = "not_comparable"
        base["detail"] = (
            "This row has no calcium_uM. The frozen luminescence entries are "
            "a calcium dose-response, so the row was not scored against them."
        )
        return base
    key = _matching_calcium_key(frozen.get("predictions") or {}, float(calcium))
    if key is None:
        base["status"] = "missing_in_frozen"
        base["detail"] = (
            f"scaffold file has no luminescence entry at {calcium:g} µM."
        )
        return base
    pred = frozen["predictions"][key]
    yhat = float(pred["predicted_value"])
    low = float(pred["uncertainty_95_lower"])
    high = float(pred["uncertainty_95_upper"])
    observed = float(row["y"])
    base.update(
        {
            "status": "compared",
            "frozen_key": key,
            "predicted": yhat,
            "error": observed - yhat,
            "uncertainty_95_lower": low,
            "uncertainty_95_upper": high,
            "within_95ci": low <= observed <= high,
            "uncertainty_method": pred.get("uncertainty_method"),
            "confidence_tier": pred.get("confidence_tier", "hypothesis_only"),
        }
    )
    return base


def _matching_calcium_key(predictions: dict[str, Any], calcium_uM: float) -> str | None:
    for key in predictions:
        if not (key.startswith("ca_") and key.endswith("uM")):
            continue
        try:
            stored = float(key[len("ca_") : -len("uM")])
        except ValueError:
            continue
        if math.isclose(stored, calcium_uM, rel_tol=0.0, abs_tol=1e-9):
            return key
    return None


def _untested(
    loaded: dict[int, dict[str, Any]],
    tested_keys: dict[int, set[str]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n_repeats, payload in sorted(loaded.items()):
        used = tested_keys.get(n_repeats, set())
        for key in payload.get("predictions") or {}:
            if key in used:
                continue
            if key.startswith("ca_"):
                reason = "No plate row carried this calcium concentration."
            else:
                reason = "The plate CSV has no column for this quantity."
            rows.append(
                {
                    "n_repeats": n_repeats,
                    "prediction_id": payload.get("prediction_id"),
                    "key": key,
                    "reason": reason,
                }
            )
    return rows
