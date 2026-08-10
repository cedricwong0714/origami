"""Cylindrical-screw CTPR geometry — docking indices and helix chord checks."""

import numpy as np

from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
    generate_scaffold_geometry,
    helical_chord_distance_nm,
    screw_point_nm,
)
from src.core.schema import ScaffoldSpec


def test_docking_one_based_includes_terminal_repeat():
    """Repeat N on an N-repeat scaffold must produce a docking site."""
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[5],
        )
    )
    assert len(geo.docking_sites) == 1
    assert geo.docking_sites[0].repeat_index == 5
    assert abs(geo.docking_sites[0].position_nm[2] - 4 * CTPR_RISE_NM) < 1e-6


def test_docking_one_maps_to_first_screw_point():
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1],
        )
    )
    assert geo.docking_sites[0].repeat_index == 1
    r = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM
    assert abs(geo.docking_sites[0].position_nm[0] - r) < 1e-9
    assert abs(geo.docking_sites[0].position_nm[1]) < 1e-9
    assert abs(geo.docking_sites[0].position_nm[2] - 0.0) < 1e-9


def test_out_of_range_docking_omitted_from_geometry():
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 8],
        )
    )
    assert [s.repeat_index for s in geo.docking_sites] == [1]


def test_backbone_follows_cylindrical_screw_not_axis():
    geo = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1, 3])
    )
    # Repeat centers sit on scaffold cylinder (non-zero x for first bead)
    assert abs(geo.backbone_coordinates_nm[0][0] - CTPR_RADIUS_NM) < 1e-9
    assert abs(geo.backbone_coordinates_nm[0][1]) < 1e-9
    # Second bead rotates 45°
    x1, y1, z1 = geo.backbone_coordinates_nm[1]
    assert abs(z1 - CTPR_RISE_NM) < 1e-9
    assert abs(x1 - CTPR_RADIUS_NM * np.cos(np.radians(CTPR_TWIST_DEG))) < 1e-9
    assert abs(y1 - CTPR_RADIUS_NM * np.sin(np.radians(CTPR_TWIST_DEG))) < 1e-9
    # Axis remains the centerline for sterics
    assert geo.axis_coordinates_nm[2] == (0.0, 0.0, 2 * CTPR_RISE_NM)


def test_inter_site_distance_matches_helix_chord_formula():
    r_dock = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM
    geo = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR8", repeat_count=8, docking_positions=[2, 5])
    )
    d = geo.get_inter_site_distance_nm(0, 1)
    expected = helical_chord_distance_nm(3, r_dock)  # Δi = 5-2 = 3
    assert abs(d - expected) < 1e-9


def test_screw_point_and_chord_consistency():
    r = 2.15
    p0 = np.array(screw_point_nm(0, r))
    p3 = np.array(screw_point_nm(3, r))
    assert abs(np.linalg.norm(p3 - p0) - helical_chord_distance_nm(3, r)) < 1e-9


def test_com_radial_extra_increases_docking_radius():
    geo0 = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1]),
        com_radial_extra_nm=0.0,
    )
    geo1 = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1]),
        com_radial_extra_nm=3.2,
    )
    assert geo1.docking_radius_nm == geo0.docking_radius_nm + 3.2
    assert abs(geo1.docking_sites[0].position_nm[0] - geo1.docking_radius_nm) < 1e-9
