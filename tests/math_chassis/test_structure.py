"""Structural invariants of the CTPR screw.

45° per repeat is the Kajander et al. 2007 superhelical turn
(eight repeats per turn). Pitch, phase, and curvature below are
identities of that screw. They are not a new fit and not a folded pose.
"""

import math

import numpy as np
import pytest

from origami.physical.geometry import build_ctpr
from origami.physical.structure import (
    chord_sigma_A,
    helix_curvature_torsion,
    structural_report,
)
from src.core.ctpr_geometry import PERSISTENCE_LENGTH_NM, wlc_mean_square_end_to_end


def test_eight_repeats_complete_one_turn_and_four_repeats_face_opposite():
    """Scientific basis: CTPR8 completes one superhelical turn, so the
    twist per repeat is 45°. Failure mode: a straight or 24° model would
    not put repeat 8 on the same radial face as repeat 0.
    """
    report = structural_report(build_ctpr(9), [0, 4, 8])
    assert report.repeats_per_turn == pytest.approx(8.0)
    assert report.pitch_A == pytest.approx(report.repeats_per_turn * report.rise_A)
    pairs = {(pair.i, pair.j): pair for pair in report.pairs}
    full_turn = pairs[(0, 8)]
    opposite = pairs[(0, 4)]
    assert full_turn.phase_rad == pytest.approx(2.0 * math.pi)
    assert full_turn.facing_cosine == pytest.approx(1.0, abs=1e-8)
    assert opposite.phase_rad == pytest.approx(math.pi)
    assert opposite.facing_cosine == pytest.approx(-1.0, abs=1e-8)
    assert report.calibrated is False


def test_curvature_and_torsion_match_the_circular_helix():
    report = structural_report(build_ctpr(8))
    kappa, tau = helix_curvature_torsion(report.docking_radius_A, report.pitch_A)
    axial_per_rad = report.pitch_A / (2.0 * math.pi)
    radius = report.docking_radius_A
    denom = radius**2 + axial_per_rad**2
    assert kappa == pytest.approx(radius / denom)
    assert tau == pytest.approx(axial_per_rad / denom)
    assert report.docking_curvature_per_A == pytest.approx(kappa)
    assert report.docking_torsion_per_A == pytest.approx(tau)
    assert tau > 0.0
    assert report.backbone_curvature_per_A > report.docking_curvature_per_A


def test_chord_matches_the_coordinate_distance_and_one_rise_of_axis():
    geom = build_ctpr(6)
    report = structural_report(geom, [1, 4])
    pair = report.pairs[0]
    expected = float(np.linalg.norm(geom.coordinates[4] - geom.coordinates[1]))
    assert pair.chord_A == pytest.approx(expected)
    assert pair.axial_A == pytest.approx(3 * geom.rise_A)
    assert pair.delta_repeats == 3


def test_chord_interval_uses_the_joint_jacobian_covariance():
    """Sites one repeat apart share the rise error. The axial part of that
    shared error shrinks the chord variance relative to independent sites.
    A different pair can widen it. The report must use the joint block
    either way, not a single rule that correlation always helps.
    """
    geom = build_ctpr(8)
    cov = geom.coord_covariance

    def block(i: int, j: int) -> np.ndarray:
        return cov[3 * i : 3 * i + 3, 3 * j : 3 * j + 3]

    def sigma(i: int, j: int, joint: bool) -> float:
        delta = geom.sites[j].xyz_A - geom.sites[i].xyz_A
        unit = delta / np.linalg.norm(delta)
        matrix = block(i, i) + block(j, j)
        if joint:
            cross = block(i, j)
            matrix = matrix - cross - cross.T
        return math.sqrt(float(unit @ matrix @ unit))

    reported = chord_sigma_A(geom, 1, 2)
    assert reported == pytest.approx(sigma(1, 2, joint=True))
    assert reported < sigma(1, 2, joint=False)
    # Repeat 0 does not accumulate rise, so its covariance with repeat 1
    # is not the same correction. The reported number still matches the joint.
    assert chord_sigma_A(geom, 0, 1) == pytest.approx(sigma(0, 1, joint=True))
    pair = structural_report(geom, [1, 2]).pairs[0]
    assert pair.chord_95_high_A - pair.chord_95_low_A == pytest.approx(2.0 * 1.96 * reported)
    assert pair.linearization_crosses_zero is (pair.chord_95_low_A < 0.0)


def test_rigid_rod_flag_follows_the_existing_persistence_length():
    """Contour is n * rise, the definition in generate_scaffold_geometry.
    The flag flips when that contour passes PERSISTENCE_LENGTH_NM.
    """
    rise_nm = build_ctpr(1).rise_A / 10.0
    last_rigid = int(PERSISTENCE_LENGTH_NM // rise_nm)
    short = structural_report(build_ctpr(last_rigid))
    long = structural_report(build_ctpr(last_rigid + 1))
    assert short.contour_nm == pytest.approx(last_rigid * rise_nm)
    assert short.contour_nm <= PERSISTENCE_LENGTH_NM
    assert short.rigid_screw is True
    assert long.rigid_screw is False
    assert any("exceeds persistence" in line for line in long.warnings)
    expected_rms = math.sqrt(
        wlc_mean_square_end_to_end(long.contour_nm, PERSISTENCE_LENGTH_NM)
    )
    assert long.wlc_end_to_end_rms_nm == pytest.approx(expected_rms)
    assert long.wlc_end_to_end_rms_nm < long.contour_nm


def test_run_design_attaches_the_screw_report_without_claiming_calibration():
    from origami.engine import run_design

    report = run_design("screw", 8)
    structure = report.structure
    assert structure is not None
    assert structure["calibrated"] is False
    assert structure["repeats_per_turn"] == pytest.approx(8.0)
    assert structure["rigid_screw"] is True
    assert structure["provenance"] == "src.core.ctpr_geometry"
    assert len(structure["pairs"]) == 1
    assert "sequence" not in structure
    payload = report.to_dict()
    assert payload["structure"]["n_repeats"] == 8
    assert report.calibrated is False
