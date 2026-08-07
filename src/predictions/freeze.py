"""
Prospective frozen-prediction workflow (CLASP Docs §1.6).

Freeze predictions BEFORE wet-lab experiments; compare AFTER.
Uses checksums so frozen files are tamper-evident.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from src.compliance.data_integrity import DataOverwriteError
from src.core.asset_paths import COMPARISONS_DIR, FROZEN_PREDICTIONS_DIR


def _sha256_of_payload(payload: dict[str, Any]) -> str:
    """Checksum of canonical JSON (excluding the checksum field itself)."""
    body = {k: v for k, v in payload.items() if k != "file_checksum"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def freeze_prediction(
    prediction_id: str,
    design_spec: dict[str, Any],
    predictions: dict[str, dict[str, Any]],
    *,
    model_version: str,
    dataset_version: str = "literature_only_v1",
    parameter_sources: Optional[list[str]] = None,
    assumptions: Optional[list[str]] = None,
    output_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """
    Write an immutable frozen prediction JSON under data/predictions/frozen/.

    Each entry in ``predictions`` should include predicted_value,
    uncertainty_95_lower, uncertainty_95_upper, confidence_tier.
    """
    output_dir = Path(output_dir) if output_dir else FROZEN_PREDICTIONS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{prediction_id}.json"
    if path.exists() and not overwrite:
        raise DataOverwriteError(
            f"Frozen prediction '{path}' already exists. "
            f"Frozen predictions are immutable. Create a new prediction_id."
        )

    payload: dict[str, Any] = {
        "prediction_id": prediction_id,
        "frozen_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_version": model_version,
        "dataset_version": dataset_version,
        "design_spec": design_spec,
        "predictions": predictions,
        "parameter_sources": list(parameter_sources or []),
        "assumptions": list(assumptions or []),
    }
    payload["file_checksum"] = f"sha256:{_sha256_of_payload(payload)}"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def verify_frozen_checksum(path: Path) -> bool:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    expected = payload.get("file_checksum", "")
    actual = f"sha256:{_sha256_of_payload(payload)}"
    return expected == actual


def compare_to_frozen(
    frozen_path: Path,
    observations: dict[str, float],
    *,
    comparison_id: Optional[str] = None,
    output_dir: Optional[Path] = None,
    overwrite: bool = False,
) -> Path:
    """
    Compare observed values to a frozen prediction.

    Records whether each observation fell inside the predicted 95% interval
    and the signed error (observed − predicted).
    """
    frozen_path = Path(frozen_path)
    frozen = json.loads(frozen_path.read_text(encoding="utf-8"))
    if not verify_frozen_checksum(frozen_path):
        raise ValueError(
            f"Frozen prediction checksum mismatch for {frozen_path}. "
            f"File may have been tampered with."
        )

    comparisons: dict[str, Any] = {}
    for key, observed in observations.items():
        if key not in frozen["predictions"]:
            comparisons[key] = {
                "status": "missing_in_frozen",
                "observed": observed,
            }
            continue
        pred = frozen["predictions"][key]
        yhat = float(pred["predicted_value"])
        lo = float(pred["uncertainty_95_lower"])
        hi = float(pred["uncertainty_95_upper"])
        error = float(observed) - yhat
        comparisons[key] = {
            "observed": float(observed),
            "predicted": yhat,
            "error": error,
            "abs_error": abs(error),
            "within_95ci": lo <= float(observed) <= hi,
            "uncertainty_95_lower": lo,
            "uncertainty_95_upper": hi,
            "confidence_tier": pred.get("confidence_tier"),
        }

    comparison_id = comparison_id or f"{frozen['prediction_id']}_comparison"
    output_dir = Path(output_dir) if output_dir else COMPARISONS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{comparison_id}.json"
    if out_path.exists() and not overwrite:
        raise DataOverwriteError(
            f"Comparison '{out_path}' already exists. Use a new comparison_id."
        )

    payload = {
        "comparison_id": comparison_id,
        "frozen_prediction_id": frozen["prediction_id"],
        "frozen_checksum": frozen["file_checksum"],
        "frozen_path": str(frozen_path),
        "compared_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "comparisons": comparisons,
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return out_path
