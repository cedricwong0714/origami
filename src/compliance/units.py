"""Explicit unit handling (AGENTS.md §8.3)."""

from __future__ import annotations

from enum import Enum


class ConcentrationUnit(str, Enum):
    MOLAR = "M"
    MILLIMOLAR = "mM"
    MICROMOLAR = "uM"
    NANOMOLAR = "nM"
    PICOMOLAR = "pM"


class UnitMismatchError(ValueError):
    """Raised when arithmetic mixes incompatible units."""


def convert_concentration(
    value: float,
    from_unit: ConcentrationUnit,
    to_unit: ConcentrationUnit,
) -> float:
    """Convert concentration with explicit unit logging responsibility on caller."""
    to_molar = {
        ConcentrationUnit.MOLAR: 1.0,
        ConcentrationUnit.MILLIMOLAR: 1e-3,
        ConcentrationUnit.MICROMOLAR: 1e-6,
        ConcentrationUnit.NANOMOLAR: 1e-9,
        ConcentrationUnit.PICOMOLAR: 1e-12,
    }
    value_in_molar = value * to_molar[from_unit]
    return value_in_molar / to_molar[to_unit]


def assert_units_match(
    value_a: float,
    unit_a: str,
    value_b: float,
    unit_b: str,
    operation: str,
) -> None:
    if unit_a != unit_b:
        raise UnitMismatchError(
            f"Cannot perform '{operation}' on values with different units: "
            f"{unit_a} and {unit_b}. Values: {value_a} {unit_a} and {value_b} {unit_b}."
        )
