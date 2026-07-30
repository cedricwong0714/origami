# tests/unit_tests/test_pipeline_integration.py
import pytest
import numpy as np
from src.core.schema import DesignSpec, ScaffoldSpec, MoCloPart
from src.ui.dashboard_backend import PipelineController

def test_full_pipeline_execution():
    spec = DesignSpec(
        design_id="INTEGRATION_TEST_001",
        chassis="E_coli",
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR4",
            repeat_count=4,
            docking_positions=[1, 3],
            persistence_length_nm=15.0
        ),
        payload_ids=["Enzyme_A", "Enzyme_B"],
        operating_mode="reversible"
    )

    parts = [
        MoCloPart(part_id="Part_1", overhang_5prime="GGAG", overhang_3prime="AATG", sequence="ATCG"),
        MoCloPart(part_id="Part_2", overhang_5prime="AATG", overhang_3prime="CGCT", sequence="GCTA")
    ]

    initial_concs = {"S": 2.0, "E": 0.2, "ES": 0.0, "P": 0.0}
    
    # Mock experimental product values over 50 points
    time_points = np.linspace(0.0, 100.0, 50)
    mock_exp_data = 2.0 * (1.0 - np.exp(-0.05 * time_points))

    controller = PipelineController()
    results = controller.run_full_pipeline(
        spec=spec,
        parts=parts,
        initial_concentrations=initial_concs,
        experimental_data=mock_exp_data
    )

    assert results["status"] == "SUCCESS"
    assert "assembled_dna" in results
    assert "genbank_file" in results
    assert "augmented_kinetics" in results
    assert len(results["next_experiment_recommendations"]) == 3