# src/gp_model/trainer.py
import numpy as np
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C

class GPCorrectionModel:
    """
    Fits a Gaussian Process on residual errors between baseline ODE simulation
    and actual experimental measurements.
    """
    def __init__(self, alpha: float = 1e-2):
        # RBF kernel with bounded hyperparameter optimization
        kernel = C(1.0, (1e-3, 1e2)) * RBF(length_scale=10.0, length_scale_bounds=(1e-1, 1e3))
        self.gp = GaussianProcessRegressor(
            kernel=kernel,
            alpha=alpha,
            n_restarts_optimizer=5,
            random_state=42
        )
        self.is_fitted = False

    def fit(self, time_points: np.ndarray, ode_predictions: np.ndarray, experimental_data: np.ndarray) -> None:
        """
        Calculates residual delta = (experimental - ODE) and fits GP model over time.
        """
        X = time_points.reshape(-1, 1)
        residuals = experimental_data - ode_predictions
        self.gp.fit(X, residuals)
        self.is_fitted = True

    def predict_correction(self, time_points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Returns predicted residual corrections and uncertainty standard deviations.
        """
        if not self.is_fitted:
            raise RuntimeError("GP model must be trained before calling predict_correction.")
            
        X = time_points.reshape(-1, 1)
        mean_delta, std_delta = self.gp.predict(X, return_std=True)
        return mean_delta, std_delta