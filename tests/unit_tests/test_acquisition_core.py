import numpy as np
import pytest
from scipy.stats import norm

from origami.acquisition_core import expected_improvement_core
from origami.design_engine.active_learning import expected_improvement as ei_engine
from src.experiment_design.acquisition import expected_improvement as ei_src


def _old_engine(mean, std, best):
    std = np.maximum(std, 1e-12)
    z = (mean - best) / std
    return (mean - best) * norm.cdf(z) + std * norm.pdf(z)


def _old_src(mean, std, best, tradeoff=0.01):
    imp = mean - best - tradeoff
    zero = std <= 1e-9
    safe = np.where(zero, 1.0, std)
    z = imp / safe
    ei = imp * norm.cdf(z) + safe * norm.pdf(z)
    ei[zero] = 0.0
    return ei


MEAN = np.array([0.1, 0.5, 1.0, 2.0, -1.0, 0.7])
STD = np.array([0.5, 0.0, 1e-10, 1.2, 0.3, 2.0])


def test_engine_wrapper_identical_to_previous_formula():
    np.testing.assert_array_equal(ei_engine(MEAN, STD, 0.6), _old_engine(MEAN, STD, 0.6))


def test_src_wrapper_identical_to_previous_formula():
    np.testing.assert_array_equal(ei_src(MEAN, STD, 0.6), _old_src(MEAN, STD, 0.6))
    np.testing.assert_array_equal(
        ei_src(MEAN, STD, 0.6, tradeoff=0.0), _old_src(MEAN, STD, 0.6, 0.0)
    )


def test_ei_is_non_negative_without_offset():
    """EI is the expectation of max(improvement, 0), so it cannot be negative."""
    assert np.all(ei_engine(MEAN, STD, 0.6) >= -1e-15)


def test_requires_exactly_one_std_policy():
    with pytest.raises(ValueError):
        expected_improvement_core(MEAN, STD, 0.0)
    with pytest.raises(ValueError):
        expected_improvement_core(MEAN, STD, 0.0, std_floor=1e-12, zero_below=1e-9)
