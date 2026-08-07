"""Learn Mode CSV + metadata package ingestion (checklist D)."""

from pathlib import Path

import numpy as np
import pytest

from src.core.asset_paths import DATA_DIR
from src.core.schema import DesignSpec, MechanismType, ScaffoldSpec
from src.data_ingestion import (
    LearnTimeseriesValidationError,
    load_learn_timeseries_package,
)
from src.data_ingestion.learn_timeseries import resolve_example_package
from src.ui.learn_mode import LearnMode

EXAMPLE_DIR = DATA_DIR / "stage1_ingestion" / "examples" / "learn_product_timeseries"
TEMPLATE_META = (
    DATA_DIR / "stage1_ingestion" / "templates" / "learn_product_timeseries.metadata.json"
)


def test_schema_and_templates_exist():
    assert (DATA_DIR / "stage1_ingestion" / "schema_learn_timeseries.json").is_file()
    assert (
        DATA_DIR / "stage1_ingestion" / "templates" / "learn_product_timeseries.csv"
    ).is_file()
    assert TEMPLATE_META.is_file()


def test_load_synthetic_example_package():
    csv_path, meta_path = resolve_example_package()
    pkg = load_learn_timeseries_package(csv_path, meta_path)
    assert pkg.metadata.data_class == "synthetic_fixture"
    assert pkg.metadata.mechanism_type == MechanismType.INTERMEDIATE_TRANSFER
    assert len(pkg.time) == len(pkg.product) >= 2
    assert pkg.warnings
    assert any("synthetic_fixture" in w for w in pkg.warnings)


def test_learn_mode_uses_experimental_time_grid():
    csv_path, meta_path = resolve_example_package()
    pkg = load_learn_timeseries_package(csv_path, meta_path)
    spec = DesignSpec(
        design_id="LEARN_INGEST_001",
        chassis="E_coli",
        mechanism_type=pkg.metadata.mechanism_type,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["OtsA", "OtsB"],
        operating_mode="reversible",
    )
    result = LearnMode().run(
        spec,
        experimental_product=pkg.product,
        experimental_time=pkg.time,
        data_class=pkg.metadata.data_class,
        package_warnings=pkg.warnings,
    )
    assert result["status"] == "SUCCESS"
    assert result["data_class"] == "synthetic_fixture"
    np.testing.assert_allclose(result["time_points"], pkg.time)
    assert result["comparison"]["n_points"] == len(pkg.product)


def test_mismatched_lengths_rejected(tmp_path: Path):
    csv = tmp_path / "bad.csv"
    csv.write_text("time,product\n0,0.1\n10,\n", encoding="utf-8")
    meta = EXAMPLE_DIR / "SYN_LEARN_001.metadata.json"
    with pytest.raises(LearnTimeseriesValidationError, match="both be filled"):
        load_learn_timeseries_package(csv, meta)


def test_tier1_requires_operator(tmp_path: Path):
    csv_path, _ = resolve_example_package()
    meta = tmp_path / "tier1.json"
    meta.write_text(
        """
        {
          "record_id": "T1",
          "data_class": "tier1_experimental",
          "assay_type": "product_timeseries",
          "created_utc": "2026-08-07T12:00:00Z",
          "operator": "",
          "mechanism_type": "intermediate_transfer",
          "primary_metric": "product",
          "unit": "relative",
          "time_unit": "s",
          "biological_replicate_id": "bio_01",
          "metadata": {
            "temperature_C": 25.0,
            "buffer": "PBS",
            "host_or_format": "E_coli",
            "instrument": "plate_reader"
          },
          "controls": {"blank_or_negative_recorded": true, "notes": "ok"},
          "csv_columns": {"time": "time", "product": "product"}
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(LearnTimeseriesValidationError, match="operator"):
        load_learn_timeseries_package(csv_path, meta)


def test_tier1_requires_controls_recorded(tmp_path: Path):
    csv_path, _ = resolve_example_package()
    meta = tmp_path / "tier1.json"
    meta.write_text(
        """
        {
          "record_id": "T1",
          "data_class": "tier1_experimental",
          "assay_type": "product_timeseries",
          "created_utc": "2026-08-07T12:00:00Z",
          "operator": "origami",
          "mechanism_type": "intermediate_transfer",
          "primary_metric": "product",
          "unit": "relative",
          "time_unit": "s",
          "biological_replicate_id": "bio_01",
          "metadata": {
            "temperature_C": 25.0,
            "buffer": "PBS",
            "host_or_format": "E_coli",
            "instrument": "plate_reader"
          },
          "controls": {"blank_or_negative_recorded": false, "notes": "missing"},
          "csv_columns": {"time": "time", "product": "product"}
        }
        """,
        encoding="utf-8",
    )
    with pytest.raises(LearnTimeseriesValidationError, match="blank"):
        load_learn_timeseries_package(csv_path, meta)


def test_blank_template_csv_rejected_until_filled():
    template_csv = (
        DATA_DIR / "stage1_ingestion" / "templates" / "learn_product_timeseries.csv"
    )
    # Template metadata still has placeholder created_utc / empty operator —
    # even as synthetic it should fail CSV emptiness first when forced synthetic.
    meta = EXAMPLE_DIR / "SYN_LEARN_001.metadata.json"
    with pytest.raises(LearnTimeseriesValidationError):
        load_learn_timeseries_package(template_csv, meta)
