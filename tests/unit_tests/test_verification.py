# tests/unit_tests/test_verification.py
import pytest
from src.core.schema import DesignSpec, ScaffoldSpec, MoCloPart
from src.verification.engine import evaluate_design

@pytest.fixture
def mock_design_context():
    spec = DesignSpec(
        design_id="DS_VERIFY_001",
        chassis="E_coli",
        scaffold=ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[2, 5],
            persistence_length_nm=15.0
        ),
        payload_ids=["OtsA", "OtsB"],
        operating_mode="reversible"
    )
    
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
    
    initial_concs = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}
    
    return spec, parts, initial_concs

def test_valid_design_verification(mock_design_context):
    spec, parts, initial_concs = mock_design_context
    report = evaluate_design(spec, parts, initial_concs, profile_version="1.0.0-test")
    
    assert report.is_valid is True
    assert report.overhang_check is True
    assert report.mass_balance_check is True
    assert len(report.errors) == 0
    assert len(report.layers) == 5

def test_out_of_bounds_docking_position_fails(mock_design_context):
    spec, parts, initial_concs = mock_design_context
    
    # Set docking position 8 on a 5-repeat scaffold
    invalid_spec = spec.model_copy(
        update={"scaffold": ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[8])}
    )
    
    report = evaluate_design(invalid_spec, parts, initial_concs)
    
    assert report.is_valid is False
    assert any("out of bounds" in err for err in report.errors)