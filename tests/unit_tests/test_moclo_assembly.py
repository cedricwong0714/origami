# tests/unit_tests/test_moclo_assembly.py
import pytest
from src.core.schema import MoCloPart
from src.moclo_compiler.assembly import assemble_level1_vector
from src.moclo_compiler.exceptions import OverhangMismatchError, InvalidPartOrderError
from src.moclo_compiler.genbank import generate_genbank_file

@pytest.fixture
def valid_moclo_parts():
    p1 = MoCloPart(part_id="Promoter_J23100", overhang_5prime="GGAG", overhang_3prime="AATG", sequence="TTGACAGCTAGCTCAGTCCTAGGTATAATACTAGT")
    p2 = MoCloPart(part_id="RBS_B0034", overhang_5prime="AATG", overhang_3prime="AAGG", sequence="AAAGAGGAGAA")
    p3 = MoCloPart(part_id="CDS_GFP", overhang_5prime="AAGG", overhang_3prime="GCTT", sequence="ATGAGTAAAGGAGAAGAACTTTTCACTGGAGTTGTCCCAATTCTTGTTGAATTAGATGGTGATGTTAATGGGCACAAATTTTCTGTCAGTGGA")
    p4 = MoCloPart(part_id="Terminator_B0015", overhang_5prime="GCTT", overhang_3prime="CGCT", sequence="CCAGGCATCAAATAAAACGAAAGGCTCAGTCGAAAGACTGGGCCTTTCGTTTTATCTGTTGTTTGTCGGTGAACGCTCTC")
    return [p1, p2, p3, p4]

def test_successful_assembly(valid_moclo_parts):
    sequence = assemble_level1_vector(valid_moclo_parts)
    expected_length = sum(len(p.sequence) for p in valid_moclo_parts)
    assert len(sequence) == expected_length

def test_overhang_mismatch_raises_error(valid_moclo_parts):
    # Intentional mismatch: Change RBS 5' overhang from 'AATG' to 'CCCC'
    mismatched_rbs = MoCloPart(
        part_id="RBS_B0034_Bad", 
        overhang_5prime="CCCC", 
        overhang_3prime="AAGG", 
        sequence="AAAGAGGAGAA"
    )
    valid_moclo_parts[1] = mismatched_rbs

    with pytest.raises(OverhangMismatchError):
        assemble_level1_vector(valid_moclo_parts)

def test_genbank_export_contains_locus(valid_moclo_parts):
    sequence = assemble_level1_vector(valid_moclo_parts)
    gb_content = generate_genbank_file("TEST_VECTOR", valid_moclo_parts, sequence)
    assert "LOCUS       TEST_VECTOR" in gb_content
    assert "misc_feature    1..35" in gb_content
    assert "//" in gb_content