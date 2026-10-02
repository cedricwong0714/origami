"""Runtime CTPR screw constants must agree with an independent refit of the
deposited C-alpha coordinates (PDB 2AVP, 2HYZ, 2FO7; Kajander et al. 2007,
DOI 10.1107/S0907444907024353).

Failure mode: the runtime geometry has drifted from the deposited structures.
This checks consistency with crystals only. It is not wet-lab calibration.
"""

import pytest

from origami.physical.deposited import deposited_summary
from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
)


@pytest.fixture(scope="module")
def summary():
    return deposited_summary(
        runtime_rise_A=CTPR_RISE_NM * 10,
        runtime_twist_deg=CTPR_TWIST_DEG,
        runtime_scaffold_radius_A=CTPR_RADIUS_NM * 10,
        runtime_docking_radius_A=(CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) * 10,
    )


def test_rise_and_radii_equal_deposited_means(summary):
    assert summary["rise_mean_A"] == pytest.approx(CTPR_RISE_NM * 10, abs=1e-6)
    assert summary["centroid_radius_mean_A"] == pytest.approx(CTPR_RADIUS_NM * 10, abs=1e-6)


def test_twist_within_one_sample_sd_of_deposited_mean(summary):
    gap = abs(summary["twist_mean_deg"] - CTPR_TWIST_DEG)
    assert gap <= summary["twist_sample_std_deg"], (
        f"Runtime twist {CTPR_TWIST_DEG} deg is {gap:.2f} deg from the deposited "
        f"mean, beyond one SD ({summary['twist_sample_std_deg']:.2f})."
    )


def test_not_marked_calibrated(summary):
    assert summary["calibrated"] is False


def test_scaffold_centroid_radius_is_below_outer_ca_radius(summary):
    """The runtime radius is a centroid radius, not an excluded-volume radius."""
    assert summary["outer_ca_radius_min_A"] > CTPR_RADIUS_NM * 10
