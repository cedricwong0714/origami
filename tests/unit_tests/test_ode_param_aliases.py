"""Profile kinetic JSON aliases must affect the canonical mechanism solvers."""

import numpy as np

from src.ode_model.mechanisms.covalent import simulate_covalent_capture
from src.ode_model.mechanisms.redox import simulate_redox_transfer


def test_covalent_accepts_k_bond_alias():
    t, slow = simulate_covalent_capture({"S": 1.0, "E": 1.0}, params={"k_bond": 0.05}, num_points=50)
    _, fast = simulate_covalent_capture({"S": 1.0, "E": 1.0}, params={"k_bond": 5.0}, num_points=50)
    assert float(fast["P"][-1]) > float(slow["P"][-1])


def test_redox_accepts_k_et_alias():
    _, low = simulate_redox_transfer({"S": 1.0, "E": 1.0}, params={"k_et": 1.0}, num_points=50)
    _, high = simulate_redox_transfer({"S": 1.0, "E": 1.0}, params={"k_et": 80.0}, num_points=50)
    assert float(high["P"][-1]) > float(low["P"][-1])


def test_shim_modules_export_same_simulator():
    from src.ode_model import intermediate as shim
    from src.ode_model.mechanisms import intermediate as canon

    assert shim.simulate_intermediate_transfer is canon.simulate_intermediate_transfer
