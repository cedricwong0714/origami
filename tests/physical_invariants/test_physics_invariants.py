# tests/physical_invariants/test_physics_invariants.py
import pytest
import numpy as np
from src.ode_model.solver import run_system_simulation

def test_non_negative_concentrations():
    """Ensure species concentrations never drop below zero during integration."""
    initial_concentrations = {"S": 1.0, "E": 0.1, "ES": 0.0, "P": 0.0}
    time_span = (0, 100)
    
    _, concentrations = run_system_simulation(initial_concentrations, time_span)
    
    for species, vals in concentrations.items():
        assert np.all(vals >= 0.0), f"Species {species} dropped below zero."