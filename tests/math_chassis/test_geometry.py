import numpy as np
import pytest

from origami.physical.geometry import build_ctpr


def test_repeat_count_matches_sites():
    geom = build_ctpr(8)
    assert len(geom.sites) == 8
    assert geom.coordinates.shape == (8, 3)


def test_superhelix_is_not_a_straight_ruler():
    geom = build_ctpr(12)
    xy = geom.coordinates[:, :2]
    radii = np.linalg.norm(xy, axis=1)
    assert np.allclose(radii, geom.radius_A, atol=1e-8)
    # successive xy headings should rotate, not stay collinear with origin only
    dots = []
    for i in range(1, 6):
        v0 = geom.coordinates[i][:2]
        v1 = geom.coordinates[i + 1][:2]
        a = v0 / np.linalg.norm(v0)
        b = v1 / np.linalg.norm(v1)
        dots.append(float(a @ b))
    assert all(d < 0.999 for d in dots)


def test_axial_rise_accumulates():
    geom = build_ctpr(10)
    z = geom.coordinates[:, 2]
    assert np.all(np.diff(z) > 0)
    assert z[-1] == pytest.approx((10 - 1) * geom.rise_A, rel=1e-9)


def test_positional_covariance_is_spd():
    geom = build_ctpr(6)
    for site in geom.sites:
        eig = np.linalg.eigvalsh(site.covariance_A2)
        assert np.all(eig > 0)


def test_coordinates_match_src_screw_after_nm_to_angstrom():
    """1 nm = 10 Å, applied only when reading screw_point_nm."""
    import math

    from origami.priors import CTPR_RADIUS_A, CTPR_RISE_A, CTPR_ROTATION_RAD
    from src.core.ctpr_geometry import (
        CTPR_RADIUS_NM,
        CTPR_RISE_NM,
        CTPR_TWIST_DEG,
        DOCKING_LOOP_OFFSET_NM,
        generate_scaffold_geometry,
        screw_point_nm,
    )
    from src.core.schema import ScaffoldSpec

    geom = build_ctpr(4)
    assert geom.provenance == "src.core.ctpr_geometry"
    assert geom.rise_A == pytest.approx(CTPR_RISE_NM * 10.0)
    assert geom.rise_A == pytest.approx(8.416139416984938)
    assert geom.rotation_rad == pytest.approx(math.pi / 4)
    assert geom.radius_A == pytest.approx((CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) * 10.0)
    assert geom.radius_A == pytest.approx(21.5)
    assert CTPR_RISE_A.value == pytest.approx(geom.rise_A)
    assert CTPR_ROTATION_RAD.value == pytest.approx(geom.rotation_rad)
    assert CTPR_RADIUS_A.value == pytest.approx(geom.radius_A)
    assert CTPR_RISE_A.calibrated is False
    assert CTPR_ROTATION_RAD.calibrated is False
    assert CTPR_RADIUS_A.calibrated is False
    assert CTPR_RISE_A.provenance == "literature_placeholder"
    assert CTPR_ROTATION_RAD.provenance == "literature_placeholder"
    assert CTPR_RADIUS_A.provenance == "literature_placeholder"

    radius_nm = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM
    for i in range(4):
        point_nm = screw_point_nm(i, radius_nm, CTPR_RISE_NM, CTPR_TWIST_DEG)
        assert np.allclose(geom.coordinates[i], np.asarray(point_nm) * 10.0)

    spec = ScaffoldSpec(
        scaffold_id="ctpr-canonical",
        repeat_count=4,
        docking_positions=[1, 2, 3, 4],
    )
    src_geo = generate_scaffold_geometry(spec)
    for site in src_geo.docking_sites:
        i = site.repeat_index - 1
        assert np.allclose(geom.coordinates[i], np.asarray(site.position_nm) * 10.0)
