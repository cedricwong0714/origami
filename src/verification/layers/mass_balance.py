# src/verification/layers/mass_balance.py
import numpy as np
from src.ode_model.solver import run_system_simulation

def verify_mass_conservation(
    initial_concentrations: dict[str, float], 
    time_span: tuple[float, float] = (0.0, 100.0),
    tolerance: float = 1e-5
) -> tuple[bool, str | None]:
    """
    Verifies that substrate pool (S + ES + P) and enzyme pool (E + ES) 
    independently satisfy mass conservation across ODE integration.
    """
    try:
        _, concs = run_system_simulation(initial_concentrations, time_span)
        
        # 1. Substrate Pool Conservation: S + ES + P = Constant
        initial_substrate_total = (
            initial_concentrations.get("S", 0.0) + 
            initial_concentrations.get("ES", 0.0) + 
            initial_concentrations.get("P", 0.0)
        )
        current_substrate_total = concs["S"] + concs["ES"] + concs["P"]
        sub_deviation = float(np.max(np.abs(current_substrate_total - initial_substrate_total)))

        # 2. Enzyme Pool Conservation: E + ES = Constant
        initial_enzyme_total = (
            initial_concentrations.get("E", 0.0) + 
            initial_concentrations.get("ES", 0.0)
        )
        current_enzyme_total = concs["E"] + concs["ES"]
        enz_deviation = float(np.max(np.abs(current_enzyme_total - initial_enzyme_total)))

        max_deviation = max(sub_deviation, enz_deviation)

        if max_deviation > tolerance:
            return False, f"Mass conservation violation: max deviation = {max_deviation:.2e} > {tolerance}"

        return True, None

    except Exception as e:
        return False, f"ODE Integration failure: {str(e)}"