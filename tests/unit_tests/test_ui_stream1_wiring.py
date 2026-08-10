"""UI wiring for Stream 1 engines (dose-response, EIG Learn)."""

from __future__ import annotations

import json

import numpy as np

from src.compiler.expression_vector import ExpressionPlan
from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.ui.design_mode import DesignMode
from src.ui.learn_mode import LearnMode


def _parts():
    return [
        MoCloPart(
            part_id="Promoter_J23100",
            overhang_5prime="GGAG",
            overhang_3prime="AATG",
            sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT",
        ),
        MoCloPart(
            part_id="RBS_B0034",
            overhang_5prime="AATG",
            overhang_3prime="CGCT",
            sequence="AAAGAGGAGAAA",
        ),
    ]


def test_design_mode_includes_assembly_dose_response_and_distance_sigma():
    spec = DesignSpec(
        design_id="UI_WIRE_001",
        chassis="E_coli",
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["OtsA", "OtsB"],
    )
    plan = ExpressionPlan(
        scaffold_vector_id="vector_pETDuet",
        payload_vector_ids=["vector_dual_plasmid_set"],
        coexpression_strategy="dual_cassette",
    )
    result = DesignMode().run(spec, _parts(), expression_plan=plan)
    assert "assembly_dose_response" in result
    adr = result["assembly_dose_response"]
    assert len(adr["calcium_M"]) == len(adr["luminescence_RLU"]) >= 5
    assert max(adr["calcium_M"]) <= 1e-4 + 1e-15  # ≤ 100 µM
    assert min(adr["calcium_M"]) >= 1e-7 - 1e-15  # ≥ 0.1 µM
    assert adr.get("ec50_M") is not None
    assert adr["ec50_uncertainty_lower_M"] <= adr["ec50_M"] <= adr["ec50_uncertainty_upper_M"]
    assert adr.get("cam_parameter_ec50_M") == 2e-6
    hill = adr.get("hill_fit")
    assert hill is not None
    assert hill["success"] is True
    assert hill["ec50_M"] > 0
    assert hill["dynamic_range"] > 0
    assert "hill_n" in hill
    assert result.get("inter_site_distance_nm") is not None
    assert result.get("inter_site_distance_uncertainty_nm") is not None
    assert result["inter_site_distance_uncertainty_nm"] >= 0
    assert "inter_site_distance_uncertainty_nm" in result["passport"]["geometry_summary"]


def test_learn_mode_information_gain_strategy():
    spec = DesignSpec(
        design_id="UI_LEARN_EIG",
        chassis="E_coli",
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["OtsA", "OtsB"],
    )
    t = np.linspace(0, 100, 20)
    exp = 0.7 * (1.0 - np.exp(-0.05 * t))
    result = LearnMode().run(
        spec,
        experimental_product=exp,
        experimental_time=t,
        strategy="information_gain",
        top_k=3,
        data_class="synthetic_fixture",
    )
    assert result["status"] == "SUCCESS"
    recs = result["next_experiment_recommendations"]
    assert len(recs) == 3
    assert recs[0]["objective"] == "information_gain"
    assert "acquisition_score" in recs[0]
    ident = result["identifiability"]
    assert ident is not None
    assert "phenomenological" in ident.get("model", "")
    assert "note" in ident
    if ident.get("success"):
        assert "fitted_values" in ident
        assert "uncertainties" in ident
        assert isinstance(ident["non_identifiable_parameters"], list)


def test_compare_to_frozen_roundtrip(tmp_path):
    from src.predictions.freeze import compare_to_frozen, freeze_prediction

    frozen = freeze_prediction(
        "ui_stream1_cmp_demo",
        design_spec={"design_id": "UI_CMP"},
        predictions={
            "primary": {
                "predicted_value": 1.0,
                "uncertainty_95_lower": 0.7,
                "uncertainty_95_upper": 1.3,
                "confidence_tier": "hypothesis_only",
            }
        },
        model_version="test",
        output_dir=tmp_path / "frozen",
    )
    out = compare_to_frozen(
        frozen,
        {"primary": 1.05},
        comparison_id="ui_stream1_cmp_demo_obs",
        output_dir=tmp_path / "comparisons",
    )
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["comparisons"]["primary"]["within_95ci"] is True


def test_stacked_ensemble_fits_synthetic_ca_curve():
    from src.core.clasp_assembly import CLASPParameters, predict_luminescence
    from src.gp_model.stacked_ensemble import StackedEnsemblePredictor

    ca_M = np.logspace(-7, -5, 6)
    params = CLASPParameters()
    y_mech = predict_luminescence(ca_M, params)
    y_obs = y_mech * 1.05
    X = np.column_stack([ca_M, np.full_like(ca_M, 1e-6), np.full_like(ca_M, 1e-6)])
    ens = StackedEnsemblePredictor(params=params)
    info = ens.fit_observations(X, y_obs, y_mechanistic=y_mech, try_xgb=False)
    assert info["gp_fitted"] is True
    pred = ens.predict(float(ca_M[2]))
    assert pred.mechanistic_prediction > 0
    assert pred.uncertainty_95_lower <= pred.predicted_value <= pred.uncertainty_95_upper
