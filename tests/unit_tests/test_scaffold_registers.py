"""Test reconciled canonical scaffold length registers across SSDK, physical registers, and backbone."""

from __future__ import annotations

from origami.physical.backbone import (
    CANONICAL_CONSTRUCT_N_VALUES,
    CONSTRUCT_N_VALUES,
    M13_GRAFT_1BASED,
    backbone_constructs,
    m13_graft_index,
)
from origami.physical.registers import (
    CANONICAL_LENGTH_ROLES,
    TEAM_BIOMARKER_N,
    TEAM_CANONICAL_LENGTHS,
    TEAM_CHANNELING_N,
    TEAM_GEOMETRY_SERIES,
    TEAM_LONG_N,
    TEAM_LOWER_N,
    TEAM_ONE_TURN_N,
    TEAM_UPPER_N,
)


def test_canonical_registers_definitions():
    assert TEAM_LOWER_N == 2
    assert TEAM_BIOMARKER_N == 3
    assert TEAM_ONE_TURN_N == 8
    assert TEAM_CHANNELING_N == 14
    assert TEAM_LONG_N == 17
    assert TEAM_UPPER_N == 20

    assert TEAM_GEOMETRY_SERIES == (8, 14, 17)
    assert TEAM_CANONICAL_LENGTHS == (3, 8, 14, 17)

    assert set(CANONICAL_LENGTH_ROLES.keys()) == {2, 3, 8, 14, 17, 20}
    for n, role in CANONICAL_LENGTH_ROLES.items():
        assert isinstance(role, str)
        assert len(role) > 5


def test_backbone_constructs_supports_all_canonical_lengths():
    assert CONSTRUCT_N_VALUES == (3, 8, 14)
    assert CANONICAL_CONSTRUCT_N_VALUES == (3, 8, 14, 17)

    # Default constructs are backwards-compatible (3, 8, 14)
    default_bundle = backbone_constructs()
    assert [c["n_repeats"] for c in default_bundle["constructs"]] == [3, 8, 14]
    assert default_bundle["m13_graft_repeat_index_by_n"] == {"3": 1, "8": 2, "14": 6}

    # Extended bundle with n=17
    bundle_17 = backbone_constructs(CANONICAL_CONSTRUCT_N_VALUES)
    assert [c["n_repeats"] for c in bundle_17["constructs"]] == [3, 8, 14, 17]
    assert "17" in bundle_17["m13_graft_repeat_index_by_n"]
    assert bundle_17["m13_graft_repeat_index_by_n"]["17"] == 8  # 9th repeat, 0-indexed is 8
    assert m13_graft_index(17) == 8
