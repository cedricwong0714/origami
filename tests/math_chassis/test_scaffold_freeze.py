"""Checked-in scaffold freezes differ by repeat count.

Scientific basis: contour length on this screw is n times the deposited
rise, and axial span is (n - 1) times that rise. The Phillips length
curve is a function of n. predict_luminescence is not.
Failure mode: three copies of one prediction, or a ±30% placeholder
applied to the screw.
A passing test is not scientific validation.
"""

from __future__ import annotations

import json

import pytest

from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report
from origami.stability.length_fit import fit_named_tm
from origami.stability.series import PHILLIPS_2012_CTPRA_DSC
from src.core.asset_paths import FROZEN_PREDICTIONS_DIR
from src.predictions.freeze import verify_frozen_checksum
from src.predictions.scaffold_freeze import (
    PLANNED_REPEAT_COUNTS,
    STANDARD_NORMAL_97_5,
    write_scaffold_freeze,
)

_IDS = {3: "scaffold-n3", 8: "scaffold-n8", 14: "scaffold-n14"}


def _load(n_repeats: int) -> dict:
    path = FROZEN_PREDICTIONS_DIR / f"{_IDS[n_repeats]}.json"
    assert path.is_file(), f"missing checked-in freeze {path}"
    assert verify_frozen_checksum(path)
    return json.loads(path.read_text(encoding="utf-8"))


def test_planned_files_match_the_series() -> None:
    assert PLANNED_REPEAT_COUNTS == (3, 8, 14)
    payloads = [_load(n) for n in PLANNED_REPEAT_COUNTS]
    assert [item["design_spec"]["n_repeats"] for item in payloads] == [3, 8, 14]
    assert all(item["design_spec"]["calibrated"] is False for item in payloads)
    assert all(item["design_spec"]["planned_series_member"] is True for item in payloads)


def test_contour_and_tm_change_with_repeat_count() -> None:
    """Contour scales with n. The length-curve Tm is not one shared number."""
    short = _load(3)
    mid = _load(8)
    long = _load(14)
    contours = [
        item["predictions"]["contour_nm"]["predicted_value"]
        for item in (short, mid, long)
    ]
    assert contours[0] < contours[1] < contours[2]
    spans = [
        item["predictions"]["axial_span_A"]["predicted_value"]
        for item in (short, mid, long)
    ]
    assert spans[0] < spans[1] < spans[2]
    tm_values = [
        item["predictions"]["phillips_tm_length_curve"]["predicted_value"]
        for item in (short, mid, long)
    ]
    assert len(set(tm_values)) == 3


def test_contour_band_is_the_deposited_rise_scatter() -> None:
    row = _load(8)["predictions"]["contour_nm"]
    assert row["uncertainty_method"] == "delta_method_deposited_rise_sample_std"
    assert row["depends_on_n_repeats"] is True
    assert row["calibrated"] is False
    half = (
        STANDARD_NORMAL_97_5
        * row["repeat_factor"]
        * row["rise_sigma_A"]
        / 10.0
    )
    assert row["uncertainty_95_upper"] - row["predicted_value"] == pytest.approx(half)
    assert row["predicted_value"] - row["uncertainty_95_lower"] == pytest.approx(half)
    assert row["uncertainty_95_lower"] != pytest.approx(row["predicted_value"] * 0.7)


def test_checked_in_contour_matches_the_screw() -> None:
    for n_repeats in PLANNED_REPEAT_COUNTS:
        report = structural_report(build_ctpr(n_repeats))
        frozen = _load(n_repeats)
        assert frozen["predictions"]["contour_nm"]["predicted_value"] == pytest.approx(
            report.contour_nm
        )
        assert frozen["predictions"]["axial_span_A"]["predicted_value"] == pytest.approx(
            report.axial_span_A
        )
        recorded = frozen["design_spec"]["recorded_without_interval"]
        assert recorded["rigid_screw"] is report.rigid_screw
        assert recorded["wlc_end_to_end_rms_nm"] == pytest.approx(
            report.wlc_end_to_end_rms_nm
        )


def test_length_curve_tm_matches_the_fit_and_is_not_the_placeholder() -> None:
    fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    for n_repeats in PLANNED_REPEAT_COUNTS:
        fresh = fit.predict(n_repeats)
        row = _load(n_repeats)["predictions"]["phillips_tm_length_curve"]
        assert fresh.value is not None
        assert row["predicted_value"] == pytest.approx(fresh.value)
        assert row["uncertainty_95_lower"] == pytest.approx(fresh.band_95_low)
        assert row["uncertainty_95_upper"] == pytest.approx(fresh.band_95_high)
        assert row["uncertainty_method"] == "length_curve_linearized_covariance"
        assert row["past_longest_cited_length"] is fresh.past_longest_cited_length
        assert row["calibrated"] is False


def test_luminescence_is_independent_of_n_and_keeps_the_placeholder() -> None:
    payloads = [_load(n) for n in PLANNED_REPEAT_COUNTS]
    curves = []
    for payload in payloads:
        assert payload["design_spec"]["luminescence"]["depends_on_n_repeats"] is False
        assert any(
            "does not take n_repeats" in item for item in payload["assumptions"]
        )
        assert any(
            "fixed_relative_placeholder_pm_30_percent" in item
            for item in payload["assumptions"]
        )
        rows = {
            key: row
            for key, row in payload["predictions"].items()
            if key.startswith("ca_")
        }
        assert rows
        for row in rows.values():
            assert row["depends_on_n_repeats"] is False
            assert row["uncertainty_method"] == "fixed_relative_placeholder_pm_30_percent"
            assert row["confidence_tier"] == "hypothesis_only"
            assert row["uncertainty_95_lower"] == pytest.approx(row["predicted_value"] * 0.7)
            assert row["uncertainty_95_upper"] == pytest.approx(row["predicted_value"] * 1.3)
        curves.append({key: row["predicted_value"] for key, row in rows.items()})
    assert curves[0] == curves[1] == curves[2]


def test_regenerated_freeze_matches_geometry_and_refuses_overwrite(tmp_path) -> None:
    path = write_scaffold_freeze(
        3,
        "scaffold-n3-regen",
        output_dir=tmp_path,
        calcium_uM=(1.0,),
        t_end=10.0,
    )
    assert verify_frozen_checksum(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    report = structural_report(build_ctpr(3))
    assert payload["predictions"]["contour_nm"]["predicted_value"] == pytest.approx(
        report.contour_nm
    )
    assert payload["predictions"]["ca_1uM"]["depends_on_n_repeats"] is False
    with pytest.raises(Exception):
        write_scaffold_freeze(
            3,
            "scaffold-n3-regen",
            output_dir=tmp_path,
            calcium_uM=(1.0,),
            t_end=10.0,
        )
