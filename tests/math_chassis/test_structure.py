"""Structural invariants of the CTPR screw.

45° per repeat is the Kajander et al. 2007 superhelical turn
(eight repeats per turn). Pitch, phase, and curvature below are
identities of that screw. They are not a new fit and not a folded pose.
"""

import math

import numpy as np
import pytest

from origami.physical.backbone import backbone_constructs
from origami.physical.deposited import deposited_summary, screw_steps
from origami.physical.geometry import build_ctpr
from origami.physical.structure import (
    _NORMAL_97_5,
    chord_sigma_A,
    helix_curvature_torsion,
    structural_report,
)
from origami.priors import (
    CTPR_RADIUS_A,
    CTPR_RISE_A,
    CTPR_ROTATION_RAD,
    CTPR_SCAFFOLD_RADIUS_A,
)
from src.core.ctpr_geometry import (
    CTPR_RISE_NM,
    DEFAULT_RISE_STD_NM,
    DEFAULT_TWIST_STD_DEG,
    PERSISTENCE_LENGTH_NM,
    wlc_mean_square_end_to_end,
)


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
    """Shared helical error can shrink or widen a chord.

    With the deposited rise, twist, and junction-radius sample standard
    deviations, sites 2 and 3 and sites 1 and 2 both have a smaller joint
    chord width than independent sites. The report uses the joint block
    either way.
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

    shrunk = chord_sigma_A(geom, 2, 3)
    assert shrunk == pytest.approx(sigma(2, 3, joint=True))
    assert shrunk < sigma(2, 3, joint=False)
    narrowed = chord_sigma_A(geom, 1, 2)
    assert narrowed == pytest.approx(sigma(1, 2, joint=True))
    assert narrowed < sigma(1, 2, joint=False)
    pair = structural_report(geom, [1, 2]).pairs[0]
    assert pair.chord_95_high_A - pair.chord_95_low_A == pytest.approx(2.0 * 1.96 * narrowed)
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


def test_runtime_rise_is_the_deposited_screw_mean_and_twist_stays_one_turn():
    """The rise is the mean of the PDB 2AVP/2HYZ/2FO7 screw steps.

    Scientific basis: those entries are the coordinates cited by
    Kajander et al. 2007, DOI 10.1107/S0907444907024353.
    Failure mode: a 1.1 nm rise is outside that step range, so pitch,
    chords, and clash would describe a different screw.
    Twist stays 45° because that angle is inside the deposited range.
    The scaffold radius is the repeat centroid. The docking radius is
    the inter-repeat junction. Neither is the outer C-alpha shell.
    """
    steps = screw_steps()
    assert len(steps) == 7
    assert {step["pdb_id"] for step in steps} == {"2AVP", "2HYZ", "2FO7"}
    report = structural_report(build_ctpr(8))
    deposited = report.deposited
    assert deposited["calibrated"] is False
    assert deposited["persistence_length_retrieved"] is False
    assert deposited["doi"] == "10.1107/S0907444907024353"
    assert report.rise_A == pytest.approx(deposited["rise_mean_A"])
    assert CTPR_RISE_NM * 10.0 == pytest.approx(deposited["rise_mean_A"])
    assert CTPR_RISE_A.sigma == pytest.approx(deposited["rise_sample_std_A"])
    assert DEFAULT_RISE_STD_NM * 10.0 == pytest.approx(CTPR_RISE_A.sigma)
    assert deposited["runtime_rise_inside_deposited_range"] is True
    assert report.repeats_per_turn == pytest.approx(8.0)
    assert deposited["twist_min_deg"] <= 45.0 <= deposited["twist_max_deg"]
    assert deposited["runtime_twist_inside_deposited_range"] is True
    assert CTPR_ROTATION_RAD.sigma == pytest.approx(
        math.radians(deposited["twist_sample_std_deg"])
    )
    assert DEFAULT_TWIST_STD_DEG == pytest.approx(deposited["twist_sample_std_deg"])
    assert deposited["centroid_radius_mean_A"] == pytest.approx(12.185585199113614)
    assert deposited["junction_radius_mean_A"] == pytest.approx(12.363166305578243)
    assert deposited["runtime_scaffold_radius_inside_outer_ca_range"] is False
    assert deposited["runtime_docking_radius_inside_outer_ca_range"] is False
    assert CTPR_SCAFFOLD_RADIUS_A.value == pytest.approx(deposited["centroid_radius_mean_A"])
    assert CTPR_RADIUS_A.value == pytest.approx(deposited["junction_radius_mean_A"])
    assert CTPR_SCAFFOLD_RADIUS_A.sigma == pytest.approx(
        deposited["centroid_radius_sample_std_A"]
    )
    assert CTPR_RADIUS_A.sigma == pytest.approx(deposited["junction_radius_sample_std_A"])
    fresh = deposited_summary(
        runtime_rise_A=report.rise_A,
        runtime_twist_deg=45.0,
        runtime_scaffold_radius_A=CTPR_SCAFFOLD_RADIUS_A.value,
        runtime_docking_radius_A=CTPR_RADIUS_A.value,
    )
    assert fresh["rise_mean_A"] == pytest.approx(deposited["rise_mean_A"])


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


def test_fusion_end_chords_match_the_screw_identity():
    """End chord² = axial² + 2 R² (1 − cos Δθ), with Δθ = (n−1) × twist.

    Scientific basis: a circular helix of constant rise and twist.
    Failure mode: the wiki chart would plot a chord that is not the
    straight-line distance between junction 0 and junction n−1.
    """
    assert _NORMAL_97_5 == 1.96
    bundle = backbone_constructs((3, 8, 14, 18))
    by_n = {row["n_repeats"]: row for row in bundle["constructs"]}
    for n_repeats in (3, 8, 14, 18):
        geom = build_ctpr(n_repeats)
        row = by_n[n_repeats]
        delta = n_repeats - 1
        theta = delta * geom.rotation_rad
        axial = delta * geom.rise_A
        radius = geom.radius_A
        chord = math.sqrt(axial**2 + 2.0 * radius**2 * (1.0 - math.cos(theta)))
        end = row["end_junction"]
        assert row["contour_nm"] * 10.0 == pytest.approx(n_repeats * geom.rise_A)
        assert row["axial_span_A"] == pytest.approx(axial)
        assert end["axial_A"] == pytest.approx(axial)
        assert end["chord_A"] == pytest.approx(chord, abs=1e-6)
        assert end["phase_deg"] == pytest.approx(math.degrees(theta))
        assert end["facing_cosine"] == pytest.approx(math.cos(theta), abs=1e-8)
        assert end["chord_95_low_A"] == pytest.approx(
            end["chord_A"] - 1.96 * end["chord_sigma_A"]
        )
        assert end["chord_95_high_A"] == pytest.approx(
            end["chord_A"] + 1.96 * end["chord_sigma_A"]
        )
        assert end["chord_95_low_A"] < end["chord_A"] < end["chord_95_high_A"]
        assert end["chord_A"] > axial
        wlc = math.sqrt(
            wlc_mean_square_end_to_end(row["contour_nm"], PERSISTENCE_LENGTH_NM)
        )
        assert row["wlc_end_to_end_rms_nm"] == pytest.approx(wlc)
        assert row["rigid_screw"] is (row["contour_nm"] <= PERSISTENCE_LENGTH_NM)
        pitch = geom.rise_A * (2.0 * math.pi) / geom.rotation_rad
        axial_per_rad = pitch / (2.0 * math.pi)
        denom = radius**2 + axial_per_rad**2
        report = structural_report(geom, [])
        assert report.docking_curvature_per_A == pytest.approx(radius / denom)
        assert report.docking_torsion_per_A == pytest.approx(axial_per_rad / denom)
