# src/experiment_design/acquisition.py
import numpy as np
from origami.acquisition_core import expected_improvement_core

def upper_confidence_bound(mean: np.ndarray, std: np.ndarray, beta: float = 2.0) -> np.ndarray:
    """
    Calculates Upper Confidence Bound (UCB).
    UCB(x) = mean(x) + beta * std(x)
    """
    return mean + beta * std

def expected_improvement(
    mean: np.ndarray,
    std: np.ndarray,
    current_best: float,
    tradeoff: float = 0.01,
) -> np.ndarray:
    """Expected Improvement over the current best observed value."""
    return expected_improvement_core(
        mean, std, current_best, xi=tradeoff, zero_below=1e-9
    )
