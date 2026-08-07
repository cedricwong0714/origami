"""UI wiring for Stream 1 engines (dose-response, EIG Learn)."""

from __future__ import annotations

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
