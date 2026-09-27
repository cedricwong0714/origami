"""Minimum sphere radius from a caller-supplied molecular weight.

This is equation 2.2 in Erickson (2009) Biological Procedures Online
11:32–51, DOI 10.1007/s12575-009-9008-x, PMC3055910. The paper states
that a protein of mass M (dalton) that is a smooth anhydrous sphere has

    Rmin (nm) = 0.066 × M^(1/3)

That is a lower bound. The same page says real proteins have an irregular
surface, so their average radius is larger than Rmin. Gel filtration
reports a Stokes radius, not this minimum.

This module does not estimate a clash radius and does not write
``radius_A`` on a payload.
"""

from __future__ import annotations

import math
from typing import Any

# Parameter: partial specific volume used to derive Rmin
# Value: 0.73
# Units: cm^3/g
# Source: Erickson (2009) Biol Proced Online 11:32-51, DOI 10.1007/s12575-009-9008-x
# System: average of globular proteins; paper states v2 ranges 0.70-0.76
# Method: review average, not a measurement of OtsA or OtsB
# Notes: Rmin uses the printed 0.066 prefactor, not a refit of v2
ERICKSON_V2_CM3_PER_G = 0.73
ERICKSON_V2_LOW_CM3_PER_G = 0.70
ERICKSON_V2_HIGH_CM3_PER_G = 0.76

# Parameter: Rmin prefactor
# Value: 0.066
# Units: nm / Da^(1/3)
# Source: Erickson (2009) eq 2.2, DOI 10.1007/s12575-009-9008-x
# System: anhydrous smooth sphere of mass M
# Method: Rmin = (3V/4π)^(1/3) with V from v2 = 0.73 cm^3/g
# Notes: Table 1 values are rounded. Clash must not use this as radius_A.
ERICKSON_RMIN_PREFACTOR_NM = 0.066

ERICKSON_SOURCE = (
    "Erickson (2009) Biol Proced Online 11:32-51, "
    "DOI: 10.1007/s12575-009-9008-x, PMC3055910, equation 2.2"
)


def erickson_rmin_nm(mw_Da: float) -> float:
    """Return Rmin in nanometres for a mass in dalton.

    ``mw_Da`` must be finite and strictly positive. The value is the
    printed 0.066 × M^(1/3). It is not a Stokes radius.
    """
    if isinstance(mw_Da, bool) or not isinstance(mw_Da, (int, float)):
        raise TypeError("mw_Da must be a number")
    mass = float(mw_Da)
    if not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("mw_Da must be finite and greater than 0")
    return ERICKSON_RMIN_PREFACTOR_NM * mass ** (1.0 / 3.0)


def erickson_rmin_A(mw_Da: float) -> float:
    """Return Rmin in ångström. 1 nm = 10 Å."""
    return erickson_rmin_nm(mw_Da) * 10.0


def erickson_rmin_bounds_nm(mw_Da: float) -> tuple[float, float]:
    """Scale Rmin by the paper's v2 range 0.70–0.76 cm^3/g.

    Volume is proportional to v2, so Rmin scales as v2^(1/3) around 0.73.
    This is the paper's stated range, not a fitted uncertainty on OtsA.
    """
    center = erickson_rmin_nm(mw_Da)
    low = center * (ERICKSON_V2_LOW_CM3_PER_G / ERICKSON_V2_CM3_PER_G) ** (1.0 / 3.0)
    high = center * (ERICKSON_V2_HIGH_CM3_PER_G / ERICKSON_V2_CM3_PER_G) ** (1.0 / 3.0)
    return low, high


def payload_size_note(mw_Da: float, clash_radius_A: float) -> dict[str, Any]:
    """Compare the clash sphere to Erickson Rmin. Does not change the clash radius."""
    rmin_A = erickson_rmin_A(mw_Da)
    low_nm, high_nm = erickson_rmin_bounds_nm(mw_Da)
    return {
        "mw_Da": float(mw_Da),
        "rmin_A": float(rmin_A),
        "rmin_nm": float(erickson_rmin_nm(mw_Da)),
        "rmin_nm_v2_low": float(low_nm),
        "rmin_nm_v2_high": float(high_nm),
        "clash_radius_A": float(clash_radius_A),
        "clash_radius_is_rmin": abs(clash_radius_A - rmin_A) <= 1e-9,
        "source": ERICKSON_SOURCE,
        "notes": [
            "Rmin is the anhydrous-sphere lower bound from Erickson eq 2.2.",
            "It is not a Stokes radius and it is not written into radius_A.",
            "A gel-filtration column reports Rs, which is larger than Rmin.",
        ],
    }
