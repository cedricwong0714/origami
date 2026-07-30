# tests/unit_tests/test_gp_model.py
import pytest
import numpy as np
from src.gp_model.trainer import GPCorrectionModel
from src.gp_model.predictor import predict_augmented_kinetics

def test_gp_correction_fitting():
    time_points = np.linspace(0, 50, 20)
    ode_predictions = 0.5 * time_points
    # Real experimental data has a slight non-linear curve offset
    experimental_data = 0.5 * time_points + 2.0 * np.sin(time_points / 5.0)

    gp = GPCorrectionModel()
    gp.fit(time_points, ode_predictions, experimental_data)

    assert gp.is_fitted is True

    # Test prediction on evaluation points
    res = predict_augmented_kinetics(time_points, ode_predictions, gp)
    
    assert "mean" in res
    assert "std" in res
    assert len(res["mean"]) == len(time_points)
    # Check that corrected output matches experimental trend better than raw ODE
    raw_error = np.mean(np.abs(experimental_data - ode_predictions))
    corrected_error = np.mean(np.abs(experimental_data - res["mean"]))
    assert corrected_error < raw_error

def test_unfitted_gp_fallback():
    time_points = np.linspace(0, 10, 5)
    ode_predictions = np.ones(5)
    
    res = predict_augmented_kinetics(time_points, ode_predictions, gp_model=None)
    np.testing.assert_array_equal(res["mean"], ode_predictions)
    np.testing.assert_array_equal(res["std"], np.zeros(5))