"""Smoke tests for profiles, Explore/Design/Learn modes, and allowlist compiler."""

import numpy as np
import pytest

from src.compiler.expression_vector import (
    ExpressionPlan,
    validate_expression_plan,
    verify_parts_against_allowlist,
)
from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.profiles import get_profile
from src.ui.design_mode import DesignMode
from src.ui.explore_mode import ExploreMode
from src.ui.learn_mode import LearnMode


def _spec(mechanism: MechanismType = MechanismType.INTERMEDIATE_TRANSFER) -> DesignSpec:
    return DesignSpec(
        design_id="STUB_FIX_001",
        chassis="E_coli",
        mechanism_type=mechanism,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
            persistence_length_nm=15.0,
        ),
        payload_ids=["OtsA", "OtsB"],
        operating_mode="reversible" if mechanism != MechanismType.COVALENT_CAPTURE else "locking",
    )


def test_all_profiles_predict():
    for mechanism in MechanismType:
        profile = get_profile(mechanism)
        spec = _spec(mechanism)
        if mechanism == MechanismType.TARGET_COMPLEMENTATION:
            spec = spec.model_copy(update={"operating_mode": "target_triggered", "chassis": "cell_free"})
        errors = profile.validate_inputs(spec)
        assert errors == []
        pred = profile.predict(spec)
        assert pred.profile_id
        assert pred.primary_metric_value >= 0


def test_explore_mode_returns_evidence_or_refuses():
    mode = ExploreMode()
    ok = mode.ask("k_cat_OtsA")
    assert ok["status"] == "OK"
    assert ok["evidence_class"] == "direct_evidence"

    refused = mode.ask("definitely_missing_parameter_xyz")
    assert refused["status"] == "INSUFFICIENT_EVIDENCE"


def test_expression_plan_rejects_solo_pet28():
    plan = ExpressionPlan(
        scaffold_vector_id="pET28a+",
        payload_vector_ids=["pET28a+"],
        coexpression_strategy="dual_plasmid",
    )
    report = validate_expression_plan(plan)
    assert report["ok"] is False
    assert any("forbidden" in e.lower() or "rejected" in e.lower() for e in report["errors"])


def test_allowlist_blocks_unknown_part():
    report = verify_parts_against_allowlist(["not_a_real_part"])
    assert report["ok"] is False


def test_design_mode_emits_passport():
    parts = [
        MoCloPart(part_id="Promoter_J23100", overhang_5prime="GGAG", overhang_3prime="AATG", sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT"),
        MoCloPart(part_id="RBS_B0034", overhang_5prime="AATG", overhang_3prime="CGCT", sequence="AAAGAGGAGAAA"),
    ]
    plan = ExpressionPlan(
        scaffold_vector_id="vector_pETDuet",
        payload_vector_ids=["vector_dual_plasmid_set"],
        coexpression_strategy="dual_cassette",
    )
    result = DesignMode().run(_spec(), parts, expression_plan=plan)
    assert "passport" in result
    assert result["passport"]["mechanism_profile"] == "trehalose_synthesis"


def test_learn_mode_recommends_experiments():
    t = np.linspace(0.0, 100.0, 40)
    exp = 0.8 * (1.0 - np.exp(-0.04 * t))
    result = LearnMode().run(_spec(), experimental_product=exp)
    assert result["status"] == "SUCCESS"
    assert len(result["next_experiment_recommendations"]) == 3
