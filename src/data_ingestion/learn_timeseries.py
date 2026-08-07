"""
Load and validate Learn Mode product time-series packages.

A package is a CSV (time, product) plus a JSON sidecar that records
mechanism profile, units, assay conditions, and control status
(Verification checklist D).
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, BinaryIO, Optional, TextIO, Union

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

from src.core.schema import MechanismType

PathLike = Union[str, Path]
TextSource = Union[PathLike, TextIO, BinaryIO]


class LearnTimeseriesValidationError(ValueError):
    """Raised when a Learn package fails checklist gates."""


class AssayConditions(BaseModel):
    temperature_C: float
    buffer: str
    host_or_format: str
    instrument: str
    n_technical_replicates: int = Field(default=1, ge=1)


class ControlRecord(BaseModel):
    blank_or_negative_recorded: bool
    notes: str = ""


class CsvColumns(BaseModel):
    time: str = "time"
    product: str = "product"


class LearnTimeseriesMetadata(BaseModel):
    record_id: str
    data_class: str
    assay_type: str = "product_timeseries"
    created_utc: str
    operator: Optional[str] = None
    mechanism_type: MechanismType
    primary_metric: str
    unit: str
    time_unit: str = "s"
    biological_replicate_id: str
    metadata: AssayConditions
    controls: ControlRecord
    csv_columns: CsvColumns = Field(default_factory=CsvColumns)
    csv_filename: Optional[str] = None
    notes: str = ""

    @field_validator("data_class")
    @classmethod
    def _known_data_class(cls, value: str) -> str:
        allowed = {"synthetic_fixture", "tier1_experimental", "literature_extracted"}
        if value not in allowed:
            raise ValueError(f"data_class must be one of {sorted(allowed)}")
        return value

    @field_validator("assay_type")
    @classmethod
    def _assay_type(cls, value: str) -> str:
        if value != "product_timeseries":
            raise ValueError("assay_type must be 'product_timeseries'")
        return value

    @field_validator("time_unit")
    @classmethod
    def _time_unit(cls, value: str) -> str:
        if value not in {"s", "min", "h"}:
            raise ValueError("time_unit must be s, min, or h")
        return value

    @model_validator(mode="after")
    def _tier1_requires_operator(self) -> LearnTimeseriesMetadata:
        if self.data_class == "tier1_experimental":
            if not self.operator or not str(self.operator).strip():
                raise ValueError(
                    "tier1_experimental packages require a non-empty operator field"
                )
            if "YYYY" in self.created_utc or not self.created_utc.strip():
                raise ValueError(
                    "tier1_experimental packages require a real created_utc timestamp"
                )
        return self


class LearnTimeseriesPackage(BaseModel):
    """Validated package ready for LearnMode.run."""

    model_config = {"arbitrary_types_allowed": True}

    metadata: LearnTimeseriesMetadata
    time: Any  # np.ndarray
    product: Any  # np.ndarray
    warnings: list[str] = Field(default_factory=list)

    @property
    def time_span(self) -> tuple[float, float]:
        t = np.asarray(self.time, dtype=float)
        return float(t[0]), float(t[-1])


def _read_text(source: TextSource) -> str:
    if isinstance(source, (str, Path)):
        return Path(source).read_text(encoding="utf-8")
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return str(raw)
    raise TypeError(f"Unsupported text source: {type(source)!r}")


def _load_metadata(source: TextSource) -> LearnTimeseriesMetadata:
    try:
        payload = json.loads(_read_text(source))
    except json.JSONDecodeError as exc:
        raise LearnTimeseriesValidationError(f"Invalid metadata JSON: {exc}") from exc
    try:
        return LearnTimeseriesMetadata.model_validate(payload)
    except Exception as exc:
        raise LearnTimeseriesValidationError(f"Metadata failed validation: {exc}") from exc


def _parse_csv(
    source: TextSource,
    time_col: str,
    product_col: str,
) -> tuple[np.ndarray, np.ndarray]:
    text = _read_text(source)
    reader = csv.DictReader(text.splitlines())
    if not reader.fieldnames:
        raise LearnTimeseriesValidationError("CSV has no header row")

    fields = {name.strip(): name for name in reader.fieldnames if name}
    lower = {name.lower(): orig for name, orig in fields.items()}

    t_key = fields.get(time_col) or lower.get(time_col.lower())
    p_key = fields.get(product_col) or lower.get(product_col.lower())
    if t_key is None or p_key is None:
        raise LearnTimeseriesValidationError(
            f"CSV must include columns '{time_col}' and '{product_col}' "
            f"(found: {list(reader.fieldnames)})"
        )

    times: list[float] = []
    products: list[float] = []
    for i, row in enumerate(reader, start=2):
        t_raw = (row.get(t_key) or "").strip()
        p_raw = (row.get(p_key) or "").strip()
        if not t_raw and not p_raw:
            continue
        if not t_raw or not p_raw:
            raise LearnTimeseriesValidationError(
                f"CSV row {i}: time and product must both be filled"
            )
        try:
            times.append(float(t_raw))
            products.append(float(p_raw))
        except ValueError as exc:
            raise LearnTimeseriesValidationError(
                f"CSV row {i}: non-numeric value ({exc})"
            ) from exc

    if len(times) < 2:
        raise LearnTimeseriesValidationError(
            "Learn Mode requires ≥2 numeric time/product rows"
        )

    t = np.asarray(times, dtype=float)
    p = np.asarray(products, dtype=float)
    if t.shape != p.shape:
        raise LearnTimeseriesValidationError("Time and product lengths do not match")
    if np.any(np.diff(t) <= 0):
        raise LearnTimeseriesValidationError("Time column must be strictly increasing")
    if not np.all(np.isfinite(t)) or not np.all(np.isfinite(p)):
        raise LearnTimeseriesValidationError("Non-finite values in time or product")
    return t, p


def load_learn_timeseries_package(
    csv_source: TextSource,
    metadata_source: TextSource,
    *,
    require_controls_recorded: bool = True,
) -> LearnTimeseriesPackage:
    """
    Validate sidecar + CSV and return arrays for Learn Mode.

    Honesty: ``data_class`` is preserved from metadata. Callers must not
    relabel synthetic fixtures as Tier-1 experimental.
    """
    meta = _load_metadata(metadata_source)
    time, product = _parse_csv(
        csv_source,
        meta.csv_columns.time,
        meta.csv_columns.product,
    )

    warnings: list[str] = []
    if meta.data_class == "synthetic_fixture":
        warnings.append(
            "Package is labeled synthetic_fixture — not Tier-1 lab data; "
            "do not present these numbers as measurements on the wiki."
        )
    if not meta.controls.blank_or_negative_recorded:
        msg = (
            "controls.blank_or_negative_recorded is false; "
            "record blank/negative controls before wiki use."
        )
        if require_controls_recorded and meta.data_class == "tier1_experimental":
            raise LearnTimeseriesValidationError(msg)
        warnings.append(msg)

    return LearnTimeseriesPackage(
        metadata=meta,
        time=time,
        product=product,
        warnings=warnings,
    )


def resolve_example_package(
    example_dir: PathLike | None = None,
) -> tuple[Path, Path]:
    """Return (csv_path, metadata_path) for the tracked SYN_LEARN_001 fixture."""
    from src.core.asset_paths import DATA_DIR

    root = Path(example_dir) if example_dir else (
        DATA_DIR / "stage1_ingestion" / "examples" / "learn_product_timeseries"
    )
    return root / "SYN_LEARN_001.csv", root / "SYN_LEARN_001.metadata.json"
