import pytest

from origami.stability.implied_cp import implied_delta_cp
from origami.stability.thermo import gibbs_helmholtz_report


def test_round_trip_through_gibbs_helmholtz():
    """Feeding the implied ΔCp back into the forward equation returns the ΔG."""
    out = implied_delta_cp(10.0, 63.0, 65.0, 4.8)
    fwd = gibbs_helmholtz_report(10.0, 63.0, 65.0, out["delta_cp_implied"])
    assert fwd["delta_g"] == pytest.approx(4.8, abs=1e-9)


def test_cp_positive_for_phillips_rows_and_roughly_per_repeat_constant():
    """A folded protein's ΔCp(unfolding) is positive (more exposed nonpolar area)."""
    c3 = implied_delta_cp(10.0, 63.0, 65.0, 4.8)["delta_cp_implied"]
    c8 = implied_delta_cp(10.0, 74.0, 178.0, 14.3)["delta_cp_implied"]
    assert c3 > 0 and c8 > 0
    assert (c8 / 8) == pytest.approx(c3 / 3, rel=0.25)


def test_labelled_derived_and_uncalibrated():
    out = implied_delta_cp(10.0, 63.0, 65.0, 4.8, 3.0, 0.4)
    assert out["calibrated"] is False and "not_literature" in out["origin"]
    assert out["delta_cp_sigma_first_order"] > 0


@pytest.mark.parametrize("args", [(63.0, 63.0, 65.0, 4.8), (10.0, float("nan"), 65.0, 4.8), (-300.0, 63.0, 65.0, 4.8)])
def test_bad_inputs(args):
    with pytest.raises(ValueError):
        implied_delta_cp(*args)
