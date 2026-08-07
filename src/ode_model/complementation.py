"""Compatibility shim — canonical code lives in ``mechanisms.complementation``."""

from src.ode_model.mechanisms.complementation import (
    complementation_derivatives,
    simulate_complementation,
)

__all__ = ["complementation_derivatives", "simulate_complementation"]
