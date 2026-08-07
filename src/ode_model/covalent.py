"""Compatibility shim — canonical code lives in ``mechanisms.covalent``."""

from src.ode_model.mechanisms.covalent import (
    covalent_derivatives,
    simulate_covalent_capture,
)

__all__ = ["covalent_derivatives", "simulate_covalent_capture"]
