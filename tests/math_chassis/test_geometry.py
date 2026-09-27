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
