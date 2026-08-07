"""Compatibility shim — canonical code lives in ``mechanisms.intermediate``."""

from src.ode_model.mechanisms.intermediate import (
    intermediate_derivatives,
    simulate_intermediate_transfer,
)

__all__ = ["intermediate_derivatives", "simulate_intermediate_transfer"]
