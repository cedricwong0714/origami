import pytest

from origami.physical.geometry import build_ctpr
from origami.physical.steric import steric_report


def test_default_is_unchanged_and_exclusion_is_monotone():
    """Fattening each C-alpha can only raise the probability of overlap."""
    geom = build_ctpr(8)
    base = steric_report(geom, [0, 7], [22.5, 22.5])
    zero = steric_report(geom, [0, 7], [22.5, 22.5], ca_exclusion_A=0.0)
    assert base.p_scaffold_clash == zero.p_scaffold_clash
    prev = zero.p_scaffold_clash
    for excl in (2.0, 4.0, 8.0):
        cur = steric_report(geom, [0, 7], [22.5, 22.5], ca_exclusion_A=excl).p_scaffold_clash
        assert all(c >= p - 1e-12 for c, p in zip(cur, prev))
        prev = cur


def test_negative_exclusion_rejected():
    with pytest.raises(ValueError):
        steric_report(build_ctpr(8), [0, 7], [22.5, 22.5], ca_exclusion_A=-1.0)
