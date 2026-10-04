"""Canonical scaffold length registers. n=17 is deliberately not used."""

from __future__ import annotations

from origami.physical.backbone import CONSTRUCT_N_VALUES, M13_GRAFT_1BASED, backbone_constructs
from origami.physical.registers import (
    CANONICAL_LENGTH_ROLES,
    TEAM_CANONICAL_LENGTHS,
    TEAM_GEOMETRY_SERIES,
)


def test_canonical_registers():
    assert TEAM_GEOMETRY_SERIES == (8, 14)
    assert TEAM_CANONICAL_LENGTHS == (3, 8, 14)
    assert set(CANONICAL_LENGTH_ROLES) == {2, 3, 8, 14, 20}
    assert 17 not in M13_GRAFT_1BASED


def test_backbone_default_constructs():
    assert CONSTRUCT_N_VALUES == (3, 8, 14)
    bundle = backbone_constructs()
    assert [c["n_repeats"] for c in bundle["constructs"]] == [3, 8, 14]
    assert bundle["m13_graft_repeat_index_by_n"] == {"3": 1, "8": 3, "14": 6}
