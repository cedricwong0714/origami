import numpy as np

from origami.physical.geometry import build_ctpr
from origami.physical.steric import clash_probability, clash_probability_mc, steric_report


def test_adjacent_large_enzymes_clash():
    geom = build_ctpr(6)
    report = steric_report(geom, [0, 1], [25.0, 25.0])
    assert report.pairs[0].p_clash > 0.8
    assert report.p_any_payload_clash > 0.8


def test_distant_small_payloads_rarely_clash():
    geom = build_ctpr(20)
    report = steric_report(geom, [0, 19], [8.0, 8.0])
    assert report.pairs[0].p_clash < 0.05
    assert report.p_any_payload_clash < 0.05


def test_delta_method_tracks_monte_carlo():
    geom = build_ctpr(8)
    a, b = geom.site(0), geom.site(3)
    p_an = clash_probability(a, b, 18.0, 18.0)
    p_mc = clash_probability_mc(a, b, 18.0, 18.0, n_samples=8000, rng=np.random.default_rng(1))
    assert abs(p_an - p_mc) < 0.12
