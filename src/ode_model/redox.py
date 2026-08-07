"""Compatibility shim — canonical code lives in ``mechanisms.redox``."""

from src.ode_model.mechanisms.redox import (
    redox_derivatives,
    simulate_redox_transfer,
)

__all__ = ["redox_derivatives", "simulate_redox_transfer"]
