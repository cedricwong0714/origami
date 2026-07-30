# src/gp_model/predictor.py
import numpy as np
from typing import Optional
from src.gp_model.trainer import GPCorrectionModel

def predict_augmented_kinetics(
    time_points: np.ndarray,
    ode_predictions: np.ndarray,
    gp_model: Optional[GPCorrectionModel] = None
) -> dict[str, np.ndarray]:
    """
    Combines baseline ODE outputs with GP error correction if a trained model is provided.
    """
    if gp_model is None or not gp_model.is_fitted:
        return {
            "mean": ode_predictions,
            "std": np.zeros_like(ode_predictions),
            "lower_bound": ode_predictions,
            "upper_bound": ode_predictions
        }

    mean_delta, std_delta = gp_model.predict_correction(time_points)
    corrected_mean = np.maximum(0.0, ode_predictions + mean_delta)  # Maintain physical non-negativity

    return {
        "mean": corrected_mean,
        "std": std_delta,
        "lower_bound": np.maximum(0.0, corrected_mean - 1.96 * std_delta),
        "upper_bound": corrected_mean + 1.96 * std_delta
    }