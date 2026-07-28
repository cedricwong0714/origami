# tests/unit_tests/test_ode_solver.py
import pytest
import numpy as np
from src.ode_model.solver import run_system_simulation

def test_mass_conservation():
    initial_concentrations = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}
    time_span = (0, 100)
    
    time_points, concentrations = run_system_simulation(initial_concentrations, time_span)
    
    # Calculate total substrate + product concentration at each time step
    total_substrate_axis = concentrations["S"] + concentrations["ES"] + concentrations["P"]
    initial_total = initial_concentrations["S"]
    
    # Assert mass conservation holds throughout integration
    np.testing.assert_allclose(total_substrate_axis, initial_total, atol=1e-6)