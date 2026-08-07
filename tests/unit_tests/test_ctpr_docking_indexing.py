"""Docking positions are 1-based and must map onto the CTPR backbone correctly."""

from src.core.ctpr_geometry import CTPR_RISE_NM, generate_scaffold_geometry
from src.core.schema import ScaffoldSpec


def test_docking_one_based_includes_terminal_repeat():
    """Repeat N on an N-repeat scaffold must produce a docking site (was previously dropped)."""
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[5],
        )
    )
    assert len(geo.docking_sites) == 1
    assert geo.docking_sites[0].repeat_index == 5
    # Terminal repeat sits near z ≈ (5-1)*rise
    assert abs(geo.docking_sites[0].position_nm[2] - 4 * CTPR_RISE_NM) < 1e-6


def test_docking_one_maps_to_first_backbone_bead():
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1],
        )
    )
    assert geo.docking_sites[0].repeat_index == 1
    assert abs(geo.docking_sites[0].position_nm[2] - 0.0) < 1e-6


def test_out_of_range_docking_omitted_from_geometry():
    geo = generate_scaffold_geometry(
        ScaffoldSpec(
            scaffold_id="CTPR5",
            repeat_count=5,
            docking_positions=[1, 8],
        )
    )
    assert [s.repeat_index for s in geo.docking_sites] == [1]
