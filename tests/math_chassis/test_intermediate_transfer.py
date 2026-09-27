import numpy as np

from origami.mechanisms.intermediate_transfer import (
    capture_probability,
    damkohler,
    k_capture_from_specificity,
    simulate_from_ceff,
    simulate_transfer,
)


def test_capture_probability_is_da_over_one_plus_da():
    assert capture_probability(0.0) == 0.0
    assert abs(capture_probability(1.0) - 0.5) < 1e-12
    assert capture_probability(9.0) == 0.9


def test_higher_ceff_raises_damkohler():
    slow = k_capture_from_specificity(1e5, 1e-6)
    fast = k_capture_from_specificity(1e5, 1e-3)
    assert damkohler(fast, 1.0) > damkohler(slow, 1.0)


def test_ode_matches_analytical_steady_state():
    # Synthetic rates for the invariant. Not biological constants.
    result = simulate_transfer(v_prod_M_per_s=1e-6, k_escape_per_s=2.0, k_capture_per_s=8.0)
    assert abs(result.da - 4.0) < 1e-12
    assert abs(result.p_capture - 0.8) < 1e-12
    assert abs(result.intermediate_M[-1] - result.intermediate_ss_M) < 1e-8
    # late flux dP/dt ≈ k_cap * I
    dt = result.time_s[-1] - result.time_s[-2]
    flux = (result.product_M[-1] - result.product_M[-2]) / dt
    assert abs(flux - result.product_flux_M_per_s) / result.product_flux_M_per_s < 0.02
    assert result.calibrated is False
    assert result.confidence_tier == "hypothesis_only"


def test_ceff_path_uses_specificity():
    ceff = 1e-4
    spec = 2e4
    result = simulate_from_ceff(1e-7, 1.0, spec, ceff)
    assert abs(result.k_capture_per_s - spec * ceff) < 1e-12


def test_negative_escape_rejected():
    try:
        damkohler(1.0, 0.0)
    except ValueError:
        return
    raise AssertionError("expected ValueError")
