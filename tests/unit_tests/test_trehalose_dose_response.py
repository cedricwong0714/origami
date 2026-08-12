"""Trehalose Ca²⁺ dose–response (scaffolded vs free)."""

from __future__ import annotations

import numpy as np

from src.core.schema import DesignSpec, MechanismType, MoCloPart, ScaffoldSpec
from src.compiler.expression_vector import ExpressionPlan
from src.profiles.trehalose_dose_response import predict_trehalose_ca_dose_response
from src.ui.design_mode import DesignMode


def test_trehalose_product_increases_with_calcium():
    """
    Scientific basis: CaM–M13 occupancy rises with Ca²⁺, increasing effective
    channeling; scaffolded trehalose endpoint should be non-decreasing.
    Failure mode: inverted dose–response would mislead SCALE Stage L design.
    """
    ca = np.logspace(-7, -4, 15)
    out = predict_trehalose_ca_dose_response(ca)
    p = np.asarray(out["trehalose_scaffold"])
    assert np.all(np.diff(p) >= -1e-6)
    assert p[-1] > p[0]


def test_scaffolded_beats_free_at_high_calcium():
    """Free control has k_channel=0; at high occupancy scaffolded yield should exceed free."""
    ca = np.array([1e-4])
    out = predict_trehalose_ca_dose_response(ca)
    assert out["trehalose_scaffold"][0] > out["trehalose_free"][0]
    assert out["fold_change"][0] > 1.0


def test_design_mode_includes_trehalose_dose_response_for_ots():
    parts = [
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
    spec = DesignSpec(
        design_id="TRE_DOSE_001",
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
    result = DesignMode().run(spec, parts, expression_plan=plan)
    tdr = result.get("trehalose_dose_response")
    assert tdr is not None
    assert len(tdr["calcium_M"]) == len(tdr["trehalose_scaffold"])
    assert tdr["hill_fit_scaffold"]["success"] is True


def test_non_trehalose_mechanism_skips_trehalose_curve():
    parts = [
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
    spec = DesignSpec(
        design_id="TRE_SKIP_001",
        chassis="E_coli",
        mechanism_type=MechanismType.TARGET_COMPLEMENTATION,
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 3],
        ),
        payload_ids=["recognition", "SmBiT"],
    )
    plan = ExpressionPlan(
        scaffold_vector_id="vector_pETDuet",
        payload_vector_ids=["vector_dual_plasmid_set"],
        coexpression_strategy="dual_cassette",
    )
    result = DesignMode().run(spec, parts, expression_plan=plan)
    assert result.get("trehalose_dose_response") is None
