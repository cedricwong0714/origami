"""Δi scan on one canonical scaffold.

These tests lock the screw geometry and the unfitted residual GP.
They do not treat next_delta_i as a wet-lab optimum, and they do not
train that GP toward a team length.
"""

import inspect
import math

import pytest

from origami.design_engine.active_learning import recommend
from origami.engine import Observation, run_design
from origami.physical.geometry import build_ctpr
from origami.physical.score import physics_report
from origami.physical.separation import separation_library
from origami.physical.structure import structural_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A

# Same cutoff recommend() uses. Not a second threshold.
_CLASH_LIMIT = float(inspect.signature(recommend).parameters["clash_limit"].default)


def _expected_next_delta(candidates: list[dict]) -> int:
    """First UCB pick when the posterior std is flat and the mean is the score."""
    legal = [row for row in candidates if row["p_instability"] < _CLASH_LIMIT]
    if legal:
        best = max(row["physics_score"] for row in legal)
        return next(row["delta_i"] for row in legal if row["physics_score"] == best)
    lowest = min(row["p_instability"] for row in candidates)
    return next(row["delta_i"] for row in candidates if row["p_instability"] == lowest)


def test_unfitted_scan_matches_the_screw_and_the_physics_score():
    radius = DEFAULT_PAYLOAD_RADIUS_A.value
    scan = separation_library(
        16,
        radius_anchor_A=radius,
        radius_partner_A=radius,
        thermal_state="not_scored",
        design_delta_i=15,
    )
    assert scan["calibrated"] is False
    assert scan["gp_fitted"] is False
    assert scan["active_process"] == "unfitted_residual_gp_plus_recommend"
    assert scan["one_turn_n"] == 8
    assert scan["design_delta_i"] == 15
    assert scan["next_delta_i"] == _expected_next_delta(scan["candidates"])
    assert scan["next_delta_i"] != 14
    assert "UCB" in scan["acquisition_name"]

    geom = build_ctpr(16)
    rise = geom.rise_A
    twist = geom.rotation_rad
    stds = {row["posterior_std"] for row in scan["candidates"]}
    assert len(stds) == 1
    for row in scan["candidates"]:
        delta = row["delta_i"]
        pair = structural_report(geom, [0, delta]).pairs[0]
        scored = physics_report(16, payload_indices=[0, delta], radii_A=[radius, radius])
        assert row["chord_A"] == pytest.approx(pair.chord_A)
        assert row["chord_sigma_A"] == pytest.approx(pair.chord_sigma_A)
        assert row["axial_A"] == pytest.approx(delta * rise)
        assert row["phase_rad"] == pytest.approx(delta * twist)
        assert row["facing_cosine"] == pytest.approx(math.cos(delta * twist))
        assert row["physics_score"] == pytest.approx(scored.physics_score)
        assert row["p_clash"] == pytest.approx(scored.steric.pairs[0].p_clash)
        assert row["posterior_mean"] == pytest.approx(row["physics_score"])
        assert row["on_integer_turn"] is (delta % 8 == 0)

    full_turn = next(row for row in scan["candidates"] if row["delta_i"] == 8)
    assert full_turn["on_integer_turn"] is True
    assert full_turn["facing_cosine"] == pytest.approx(1.0)
    assert full_turn["phase_rad"] == pytest.approx(2.0 * math.pi)


def test_extrapolated_scaffold_reports_candidates_and_recommends_none():
    radius = DEFAULT_PAYLOAD_RADIUS_A.value
    scan = separation_library(
        14,
        radius_anchor_A=radius,
        radius_partner_A=radius,
        thermal_state="extrapolated",
        design_delta_i=13,
    )
    assert scan["candidates"]
    assert scan["next_delta_i"] is None
    assert scan["acquisition_name"].startswith("withheld:")
    assert all(row["posterior_mean"] == pytest.approx(row["physics_score"]) for row in scan["candidates"])
    assert any("no separation was recommended" in note for note in scan["notes"])


def test_half_turn_faces_opposite_and_stays_inside_the_clash_mask():
    """Outward spheres half a turn apart do not meet.

    400 Å is a caller fixture, not a measured enzyme radius. At that size
    every other separation on an 8-repeat screw exceeds recommend()'s clash
    limit. Δi = 4 is half a turn, facing cosine -1, and remains legal.
    The acquisition therefore keeps it. It does not fall through, and it
    does not return 14.
    """
    scan = separation_library(
        8,
        radius_anchor_A=400.0,
        radius_partner_A=400.0,
        thermal_state="pass",
    )
    half = next(row for row in scan["candidates"] if row["delta_i"] == 4)
    assert half["facing_cosine"] == pytest.approx(-1.0)
    assert half["phase_rad"] == pytest.approx(math.pi)
    assert half["p_instability"] < _CLASH_LIMIT
    assert all(
        row["p_instability"] >= _CLASH_LIMIT
        for row in scan["candidates"]
        if row["delta_i"] != 4
    )
    assert "exceed steric threshold" not in scan["acquisition_name"]
    assert scan["next_delta_i"] == 4
    assert scan["next_delta_i"] == _expected_next_delta(scan["candidates"])


def test_run_design_ranks_delta_i_without_using_repeat_count_observations():
    plain = run_design("separation-plain", 8)
    trained_on_n = run_design(
        "separation-n-obs",
        8,
        observations=[
            Observation(n_repeats=3, y=0.2, notes="caller fixture, not a Δi assay"),
            Observation(n_repeats=6, y=1.4, notes="caller fixture, not a Δi assay"),
            Observation(n_repeats=10, y=0.3, notes="caller fixture, not a Δi assay"),
        ],
        thermal_prior=False,
    )
    assert plain.separation is not None
    assert plain.separation["thermal_state"] == "pass"
    assert plain.separation["design_delta_i"] == 7
    assert plain.separation["gp_fitted"] is False
    assert plain.separation["next_delta_i"] == _expected_next_delta(plain.separation["candidates"])
    assert all(row["delta_i"] != 14 for row in plain.separation["candidates"])

    assert trained_on_n.separation is not None
    assert trained_on_n.separation["thermal_state"] == "not_scored"
    assert trained_on_n.separation["gp_fitted"] is False
    for row in trained_on_n.separation["candidates"]:
        assert row["posterior_mean"] == pytest.approx(row["physics_score"])
    assert trained_on_n.separation["next_delta_i"] == _expected_next_delta(
        trained_on_n.separation["candidates"]
    )


def test_run_design_withholds_delta_i_when_the_scaffold_is_extrapolated():
    report = run_design("separation-14", 14)
    assert report.stability_state == "extrapolated"
    assert report.separation is not None
    assert report.separation["thermal_state"] == "extrapolated"
    assert report.separation["next_delta_i"] is None
    assert report.separation["design_delta_i"] == 13
    assert report.registers["channeling_candidate_n"] == 14
    assert report.registers["channeling_candidate_is_steric_minimum"] is False
    assert any("not trained toward 14" in note for note in report.separation["notes"])
