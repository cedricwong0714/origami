# src/ode_model/solver.py
from typing import Tuple, Dict
import numpy as np
from src.core.schema import MechanismType
from src.ode_model.mechanisms.intermediate import simulate_intermediate_transfer
from src.ode_model.mechanisms.complementation import simulate_complementation
from src.ode_model.mechanisms.redox import simulate_redox_transfer
from src.ode_model.mechanisms.covalent import simulate_covalent_capture
from src.ode_model.mechanisms.trans_activation import simulate_trans_activation
from src.ode_model.mechanisms.protease_cleavage import simulate_protease_cleavage

def run_system_simulation(
    initial_concentrations: Dict[str, float],
    time_span: Tuple[float, float] = (0.0, 100.0),
    mechanism_type: MechanismType = MechanismType.INTERMEDIATE_TRANSFER,
    params: Dict[str, float] = None,
    num_points: int = 100
) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
    """
    Routes kinetic simulations to the corresponding mechanism solver.
    """
    params = params or {}

    if mechanism_type == MechanismType.INTERMEDIATE_TRANSFER:
        return simulate_intermediate_transfer(initial_concentrations, params, time_span, num_points)
    elif mechanism_type == MechanismType.TARGET_COMPLEMENTATION:
        return simulate_complementation(initial_concentrations, params, time_span, num_points)
    elif mechanism_type == MechanismType.REDOX_TRANSFER:
        return simulate_redox_transfer(initial_concentrations, params, time_span, num_points)
    elif mechanism_type == MechanismType.COVALENT_CAPTURE:
        return simulate_covalent_capture(initial_concentrations, params, time_span, num_points)
    elif mechanism_type == MechanismType.TRANS_ACTIVATION:
        return simulate_trans_activation(initial_concentrations, params, time_span, num_points)
    elif mechanism_type == MechanismType.PROTEASE_CLEAVAGE:
        return simulate_protease_cleavage(initial_concentrations, params, time_span, num_points)
    else:
        raise ValueError(f"Unsupported mechanism type: {mechanism_type}")