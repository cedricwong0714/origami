"""AGENTS.md compliance layer — unit and invariant tests."""

import warnings
from pathlib import Path

import pytest

from src.compliance import (
    ORIGAMI_PARAMETER_LIBRARY,
    compute_sequence_checksum,
    convert_concentration,
    get_parameter_or_warn,
    profile_prediction_to_result,
    safe_write_experimental_data,
    verify_reading_frame,
    verify_sequence_unchanged,
)
from src.compliance.units import ConcentrationUnit, UnitMismatchError
from src.core.schema import EvidenceMaturity, MechanismType
from src.profiles.base import ProfilePrediction
from src.ui.explore_mode import ExploreMode


def test_unsourced_parameter_warns():
    with pytest.warns(UserWarning, match="no verified source"):
        assert get_parameter_or_warn("fake_kcat", None, None) is None


def test_origami_parameter_library_has_ctpr_rise():
    param = ORIGAMI_PARAMETER_LIBRARY["CTPR_RISE_NM"]
    assert param.value == 1.1
    assert param.units == "nm"
    assert "CLASP" in param.source or "Dueber" in param.source


def test_sequence_checksum_stable():
    seq = "ATCGATCG"
    assert compute_sequence_checksum(seq) == compute_sequence_checksum("atcgatcg")


def test_verify_sequence_unchanged_raises():
    with pytest.raises(Exception):
        verify_sequence_unchanged("ATCG", "ATCC", "test_op")


def test_reading_frame_allows_non_coding_short_part():
    result = verify_reading_frame("TTGACAGCTAG", None, "promoter")
    assert result.valid is True


def test_convert_concentration_um_to_m():
    assert convert_concentration(2.0, ConcentrationUnit.MICROMOLAR, ConcentrationUnit.MOLAR) == pytest.approx(2e-6)


def test_unit_mismatch_raises():
    with pytest.raises(UnitMismatchError):
        from src.compliance.units import assert_units_match

        assert_units_match(1.0, "M", 1.0, "mM", "add")


def test_profile_prediction_maps_to_agents_prediction_result():
    pred = ProfilePrediction(
        profile_id="trehalose_synthesis",
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        primary_metric_name="product",
        primary_metric_value=0.5,
        unit="relative",
        uncertainty_95ci=(0.35, 0.65),
        evidence_maturity=EvidenceMaturity.TIER_3_COMPUTATIONAL,
    )
    result = profile_prediction_to_result(pred)
    assert result.uncertainty_95_lower <= result.predicted_value <= result.uncertainty_95_upper
    assert result.is_extrapolation is True
    assert "hypothesis" in result.confidence_tier


def test_explore_structured_refuses_unknown_key():
    answer = ExploreMode().ask_structured("totally_unknown_parameter_xyz")
    assert answer.status == "INSUFFICIENT_EVIDENCE"
    assert answer.human_review_required is True


def test_explore_structured_separates_direct_evidence():
    answer = ExploreMode().ask_structured("k_cat_OtsA")
    assert answer.status == "OK"
    assert answer.value is not None
    assert answer.direct_evidence or answer.model_inference


def test_safe_write_refuses_silent_overwrite(tmp_path: Path):
    path = tmp_path / "tier1.json"
    safe_write_experimental_data({"a": 1}, path)
    with pytest.raises(Exception):
        safe_write_experimental_data({"a": 2}, path, overwrite=False)
