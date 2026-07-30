# src/experiment_design/acquisition.py
import numpy as np
from scipy.stats import norm

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
    tradeoff: float = 0.01
) -> np.ndarray:
    """
    Calculates Expected Improvement (EI) over the current best observed value.
    """
    improvement = mean - current_best - tradeoff
    
    # Avoid divide-by-zero where std is near zero
    zero_std_mask = std <= 1e-9
    std_safe = np.where(zero_std_mask, 1.0, std)
    
    Z = improvement / std_safe
    ei = improvement * norm.cdf(Z) + std_safe * norm.pdf(Z)
    
    # Set EI to 0 where uncertainty is negligible
    ei[zero_std_mask] = 0.0
    return ei