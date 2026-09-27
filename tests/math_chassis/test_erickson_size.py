"""Erickson 2009 Rmin is a mass lower bound, not a clash radius.

Scientific basis: Erickson, Biol Proced Online 11:32-51 (2009),
DOI 10.1007/s12575-009-9008-x, equation 2.2 and Table 1.
Failure mode: treating Rmin as a measured enzyme radius would understate
excluded volume and silently replace the caller clash sphere.
"""

from __future__ import annotations

import pytest

from origami.physical.erickson_size import (
    ERICKSON_RMIN_PREFACTOR_NM,
    erickson_rmin_A,
    erickson_rmin_bounds_nm,
    erickson_rmin_nm,
    payload_size_note,
)


def test_rmin_matches_printed_prefactor() -> None:
    mass = 50_000.0
    assert erickson_rmin_nm(mass) == pytest.approx(
        ERICKSON_RMIN_PREFACTOR_NM * mass ** (1.0 / 3.0)
    )
    assert erickson_rmin_A(mass) == pytest.approx(10.0 * erickson_rmin_nm(mass))


def test_table_1_rounded_examples() -> None:
    """Table 1 prints rounded Rmin. The formula is 0.066 M^{1/3}."""
    assert erickson_rmin_nm(5_000.0) == pytest.approx(1.1, abs=0.05)
    assert erickson_rmin_nm(10_000.0) == pytest.approx(1.42, abs=0.02)
    assert erickson_rmin_nm(20_000.0) == pytest.approx(1.78, abs=0.02)
    assert erickson_rmin_nm(50_000.0) == pytest.approx(2.4, abs=0.05)
    assert erickson_rmin_nm(100_000.0) == pytest.approx(3.05, abs=0.03)
    assert erickson_rmin_nm(200_000.0) == pytest.approx(3.84, abs=0.03)
    assert erickson_rmin_nm(500_000.0) == pytest.approx(5.21, abs=0.03)


def test_eightfold_mass_doubles_rmin() -> None:
    """
    Volume is linear in mass. A sphere radius scales as M^{1/3}.
    Failure mode: a linear MW-to-radius map would violate that geometry.
    """
    small = erickson_rmin_nm(10_000.0)
    large = erickson_rmin_nm(80_000.0)
    assert large / small == pytest.approx(2.0)


def test_v2_range_brackets_the_center() -> None:
    low, high = erickson_rmin_bounds_nm(50_000.0)
    center = erickson_rmin_nm(50_000.0)
    assert low < center < high


def test_size_note_does_not_claim_clash_is_rmin() -> None:
    note = payload_size_note(50_000.0, clash_radius_A=25.0)
    assert note["clash_radius_is_rmin"] is False
    assert "radius_A" in note["notes"][1]
    assert note["source"].startswith("Erickson (2009)")


def test_rejects_nonpositive_mass() -> None:
    with pytest.raises(ValueError, match="mw_Da"):
        erickson_rmin_nm(0.0)
