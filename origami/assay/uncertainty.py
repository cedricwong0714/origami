"""First-order uncertainty for lab-chassis results.

The factor 1.96 is the 97.5 percentile of the standard normal
distribution. It is not a biological constant. A reported 95% band is
value ± 1.96 σ. It is a linear approximation, not a wet-lab confidence
interval.

A missing sigma is omitted. It is not stored as zero. An explicit
sigma of zero, typed by the caller, is kept.
"""

from __future__ import annotations

import math

# Standard-normal 97.5 percentile. Not a measured biological parameter.
Z95 = 1.96


def finite_number(name: str, value: object) -> float:
    """Return ``value`` as a finite float, or raise ``ValueError``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        # One error type so every caller can report the field as missing.
        raise ValueError(f"{name} must be a finite number")  # noqa: TRY004
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def optional_sigma(name: str, value: object) -> float | None:
    """Return a non-negative sigma, or None when the caller omitted it."""
    if value is None:
        return None
    sigma = finite_number(name, value)
    if sigma < 0:
        raise ValueError(f"{name} cannot be negative")
    return sigma


def band(value: float, sigma: float | None) -> tuple[float | None, float | None]:
    """Return the 95% band, or ``(None, None)`` when sigma was omitted."""
    if sigma is None:
        return None, None
    half = Z95 * sigma
    return value - half, value + half


def quotient(
    numerator: float,
    denominator: float,
    sigma_numerator: float | None,
    sigma_denominator: float | None,
) -> tuple[float, float | None]:
    """Return ``numerator / denominator`` and a first-order sigma.

    The sigma uses independent errors:

        σ_q² = (σ_n / d)² + (n σ_d / d²)²

    If either sigma was omitted, the quotient sigma is omitted too.
    """
    if denominator == 0.0:
        raise ValueError("denominator must be non-zero")
    value = numerator / denominator
    if sigma_numerator is None or sigma_denominator is None:
        return value, None
    variance = (sigma_numerator / denominator) ** 2 + (
        numerator * sigma_denominator / denominator**2
    ) ** 2
    return value, math.sqrt(variance)
