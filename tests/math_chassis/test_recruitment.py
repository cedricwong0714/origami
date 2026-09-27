import numpy as np

from origami.physical.recruitment import recruitment_occupancy, steady_occupancy
from origami.priors import CAM_M13_KD_M


def test_steady_state_is_langmuir():
    c = 1e-9
    kd = CAM_M13_KD_M.value
    assert steady_occupancy(c, kd) == c / (c + kd)


def test_occupancy_bounds_follow_kd_sigma():
    result = recruitment_occupancy(c_free_M=1e-9)
    assert result.theta_95_lower <= result.theta_ss <= result.theta_95_upper
    assert result.calibrated is False
    assert result.time_s is None


def test_ode_relaxes_to_steady_state():
    result = recruitment_occupancy(c_free_M=1e-8, kon_per_M_s=1e6)
    assert result.theta_t is not None
    assert abs(result.theta_t[-1] - result.theta_ss) < 1e-3


def test_signal_off_is_empty():
    result = recruitment_occupancy(c_free_M=1e-6, signal_on=False)
    assert result.theta_ss == 0.0


def test_negative_concentration_rejected():
    try:
        steady_occupancy(-1.0, 1e-9)
    except ValueError as exc:
        assert "C_free" in str(exc)
    else:
        raise AssertionError("expected ValueError")
