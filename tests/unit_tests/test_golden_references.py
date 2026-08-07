"""Regression tests against tracked golden reference fixtures."""

from src.compiler.expression_vector import ExpressionPlan
from src.core.asset_paths import (
    DATA_DIR,
    GOLDEN_DIR,
    KINETIC_MODELS_DIR,
    MODELS_DIR,
    REPO_ROOT,
    load_json,
    load_kinetic_defaults,
)
from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.ui.design_mode import DesignMode


def test_kinetic_defaults_exist_for_all_mechanisms():
    for mechanism in MechanismType:
        payload = load_kinetic_defaults(mechanism.value)
        assert payload["mechanism_type"] == mechanism.value
        assert "params" in payload
        assert (KINETIC_MODELS_DIR / f"{mechanism.value}.defaults.json").is_file()


def test_data_schemas_and_examples_exist():
    assert (DATA_DIR / "stage1_ingestion" / "schema.json").is_file()
    assert (DATA_DIR / "stage2_baselines" / "schema.json").is_file()
    stage1 = load_json(
        DATA_DIR
        / "stage1_ingestion"
        / "examples"
        / "example_nanobit_plate_metadata.json"
    )
    assert stage1["data_class"] == "synthetic_fixture"


def test_ctpr5_intermediate_transfer_golden():
    golden_path = GOLDEN_DIR / "clasp_ctpr5_intermediate_transfer.json"
    golden = load_json(golden_path)
    d = golden["design"]
    spec = DesignSpec(
        design_id=d["design_id"],
        chassis=d["chassis"],
        mechanism_type=MechanismType(d["mechanism_type"]),
        scaffold=ScaffoldSpec(**d["scaffold"]),
        payload_ids=d["payload_ids"],
        operating_mode=d["operating_mode"],
    )
    parts = [MoCloPart(**p) for p in golden["parts"]]
    plan = ExpressionPlan(**golden["expression_plan"])

    result = DesignMode().run(spec, parts, expression_plan=plan)
    exp = golden["expectations"]

    assert result["status"] == exp["design_status"]
    assert result["passport"]["mechanism_profile"] == exp["mechanism_profile"]
    assert result["verification_report"].is_valid is exp["verification_is_valid"]
    assert result["prediction"]["primary_metric_value"] >= exp["min_prediction_value"]


def test_benchmark_index_points_at_golden():
    index = load_json(MODELS_DIR / "benchmarks" / "held_out_index.json")
    smoke = next(e for e in index["entries"] if e["benchmark_id"] == "syn_intermediate_transfer_smoke")
    assert smoke["synthetic_fixture"] is True
    assert (REPO_ROOT / smoke["fixture_path"]).is_file()
