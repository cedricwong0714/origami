"""Immutable experimental data writes (AGENTS.md §8.1–8.2)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field


class DataOverwriteError(ValueError):
    """Raised when raw experimental data would be silently overwritten."""


class ExperimentalDataset(BaseModel):
    dataset_id: str
    version: str
    created_date: str
    operator: str
    construct_ids: list[str] = Field(default_factory=list)
    chassis: str = ""
    experimental_conditions: dict[str, Any] = Field(default_factory=dict)
    instrument: str = ""
    instrument_settings: dict[str, Any] = Field(default_factory=dict)
    normalization_method: str = ""
    blank_correction_applied: bool = False
    negative_controls: list[str] = Field(default_factory=list)
    positive_controls: list[str] = Field(default_factory=list)
    replicates: int = 1
    raw_data_checksum: str = ""
    approved_for_model_training: bool = False
    approved_by: Optional[str] = None
    approval_date: Optional[str] = None
    known_issues: list[str] = Field(default_factory=list)
    notes: str = ""


def _checksum_payload(data: dict[str, Any]) -> str:
    blob = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def safe_write_experimental_data(
    data: dict[str, Any],
    filepath: Path,
    overwrite: bool = False,
) -> Path:
    """
    Write experimental data safely. Raw data is immutable once recorded unless
    a versioned backup is created first.
    """
    if filepath.exists() and not overwrite:
        raise DataOverwriteError(
            f"File '{filepath}' already exists. Raw experimental data must not "
            f"be overwritten. Create a versioned file instead."
        )

    if filepath.exists() and overwrite:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_path = filepath.with_suffix(f".backup_{timestamp}{filepath.suffix}")
        shutil.copy2(filepath, backup_path)

    payload = dict(data)
    payload.setdefault("raw_data_checksum", _checksum_payload(payload))
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    return filepath
