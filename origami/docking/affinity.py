"""Decide whether a typed Kd or Ka holds two constructs together.

The local concentration is the Gaussian-chain effective concentration
at the screw chord. Default radii are the deposited SpyCatcher and
LgBiT clash radii, so the concentration is computable without a typed
radius.

Holding rule, not a fitted biological threshold:

    theta = C_eff / (C_eff + Kd)
    holds when theta >= 1/2, which is Kd <= C_eff

That midpoint is the definition of a dissociation constant.

LgBiT–SmBiT uses the printed Dixon Kd at the same local concentration.
SpyCatcher–SpyTag uses the Zakeri on-rate at the same concentration.
Those payload numbers are reported only when the association holds.
If it does not, the tether is not occupied, so those payloads do not
see this local concentration.

``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

from origami.docking.evaluate import DockingError, evaluate_docking
from origami.physical.payload_radii import PayloadRadiusError, payload_radius
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN

# Unit conversion to molar. These factors are the definitions of the
# metric prefixes, not biological parameters.
_TO_MOLAR = {
    "M": 1.0,
    "mM": 1e-3,
    "uM": 1e-6,
    "nM": 1e-9,
    "pM": 1e-12,
}

# Langmuir half occupancy. Not a measured cutoff.
_HALF = 0.5

_DEFAULT_RADIUS_KEYS = ("spycatcher", "lgbit")


class AffinityError(ValueError):
    """The affinity request is not usable."""


def evaluate_affinity(
    n_repeats: int,
    *,
    affinity: str,
    value: float,
    unit: str,
    indices: list[int] | None = None,
    radii_A: list[float] | None = None,
) -> dict[str, Any]:
    """Compare one Kd or Ka with the local concentration at this length."""
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise AffinityError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise AffinityError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    kd_M, conversion = _dissociation_constant(affinity, value, unit)
    radii, radius_records, radius_origin = _radii(radii_A)
    try:
        docking = evaluate_docking(n_repeats, indices=indices, radii_A=radii)
    except DockingError as exc:
        raise AffinityError(str(exc)) from exc
    if not docking.get("clash_computable"):
        raise AffinityError("effective concentration was not computed")
    c_eff = float(docking["c_eff_M"])
    if not math.isfinite(c_eff) or c_eff <= 0:
        raise AffinityError("effective concentration must be finite and > 0")
    theta = c_eff / (c_eff + kd_M)
    holds = kd_M <= c_eff
    local = docking.get("local_kinetics") if isinstance(docking.get("local_kinetics"), dict) else {}
    nano = local.get("nanobit") if isinstance(local.get("nanobit"), dict) else {}
    spy = local.get("spy") if isinstance(local.get("spy"), dict) else {}
    nano_theta = _finite(nano.get("theta_ss"))
    nano_kd = _finite(nano.get("printed_kd_M"))
    nano_half = nano_theta is not None and nano_theta >= _HALF
    k_obs = _finite(spy.get("k_obs_per_s"))
    spy_half = _finite(spy.get("t_half_s"))
    spy_note = spy.get("t_half_note") if isinstance(spy.get("t_half_note"), str) else None
    if spy_half is None and k_obs is not None and k_obs > 0:
        spy_half = math.log(2.0) / k_obs
        spy_note = (
            "Point half-life is ln(2) / k_obs. "
            "The 95% band on k_obs reaches zero, so an interval on the half-life is omitted."
        )
    drives_nano = bool(holds and nano_half)
    drives_spy = bool(holds and spy_half is not None and spy_half > 0)
    low = _theta_at(docking.get("c_eff_95_lower_M"), kd_M)
    high = _theta_at(docking.get("c_eff_95_upper_M"), kd_M)
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "n_repeats": n_repeats,
        "indices": docking["indices"],
        "chord_A": docking["chord_A"],
        "chord_95_low_A": docking["chord_95_low_A"],
        "chord_95_high_A": docking["chord_95_high_A"],
        "radii_A": radii,
        "radius_origin": radius_origin,
        "radius_records": radius_records,
        "c_eff_M": c_eff,
        "c_eff_95_lower_M": docking.get("c_eff_95_lower_M"),
        "c_eff_95_upper_M": docking.get("c_eff_95_upper_M"),
        "p_clash": docking.get("p_clash"),
        "affinity": conversion["affinity"],
        "input_value": conversion["input_value"],
        "input_unit": conversion["input_unit"],
        "kd_M": kd_M,
        "ka_per_M": 1.0 / kd_M,
        "conversion": conversion["conversion"],
        "association_theta": theta,
        "association_theta_at_c_eff_low": low,
        "association_theta_at_c_eff_high": high,
        "association_holds": holds,
        "criterion": (
            "The ends stay together when at least half of them are bound. "
            "That happens when your Kd is at or below the local concentration. "
            "Half-bound is the usual meaning of a Kd. It is not a cutoff from a paper."
        ),
        "nanobit_theta": nano_theta,
        "nanobit_printed_kd_M": nano_kd,
        "nanobit_occupancy_at_least_half": nano_half,
        "drives_lgbit_smbit": drives_nano,
        "spy_k_obs_per_s": k_obs,
        "spy_half_life_s": spy_half,
        "spy_half_life_note": spy_note,
        "drives_spycatcher_spytag": drives_spy,
        "equation": "theta = C_eff / (C_eff + Kd); Spy k_obs = k_on * C_eff",
        "verdict": _verdict(holds, theta, kd_M, c_eff, nano_theta, spy_half, drives_nano, drives_spy),
        "note": (
            "One effective concentration, from the screw chord and the two radii, "
            "is the local concentration of the tether. "
            "LgBiT–SmBiT uses the printed Dixon Kd at that concentration. "
            "SpyCatcher–SpyTag uses the Zakeri on-rate at that concentration. "
            "Payload binding is not claimed when the association does not hold."
        ),
    }


def docking_geometry(
    n_repeats: int,
    *,
    indices: list[int] | None = None,
    radii_A: list[float] | None = None,
) -> dict[str, Any]:
    """Screw chord, clash, and effective concentration for one length."""
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise AffinityError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise AffinityError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    radii, radius_records, radius_origin = _radii(radii_A)
    try:
        docking = evaluate_docking(n_repeats, indices=indices, radii_A=radii)
    except DockingError as exc:
        raise AffinityError(str(exc)) from exc
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "radius_origin": radius_origin,
        "radius_records": radius_records,
        "docking": docking,
    }


def _dissociation_constant(affinity: str, value: float, unit: str) -> tuple[float, dict[str, Any]]:
    kind = affinity.strip().lower()
    if kind not in {"kd", "ka"}:
        raise AffinityError("affinity must be kd or ka")
    token = unit.strip()
    if token not in _TO_MOLAR:
        raise AffinityError("unit must be M, mM, uM, nM, or pM")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AffinityError("value must be a number")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise AffinityError("value must be finite and > 0")
    factor = _TO_MOLAR[token]
    if kind == "kd":
        kd_M = number * factor
        conversion = f"{number} {token} × {factor} = {kd_M} M"
    else:
        # "per nM" means divide by the molar size of that prefix.
        ka_per_M = number / factor
        kd_M = 1.0 / ka_per_M
        conversion = f"Ka {number} per {token} = {ka_per_M} M-1; Kd = 1/Ka = {kd_M} M"
    return kd_M, {
        "affinity": kind,
        "input_value": number,
        "input_unit": token,
        "conversion": conversion,
    }


def _radii(radii_A: list[float] | None) -> tuple[list[float], list[dict[str, Any]], str]:
    if radii_A is not None:
        if len(radii_A) != 2:
            raise AffinityError("radii_A must contain two angstrom values")
        radii = [float(radii_A[0]), float(radii_A[1])]
        if any((not math.isfinite(radius)) or radius <= 0 for radius in radii):
            raise AffinityError("each radius must be finite and > 0")
        return radii, [], "caller"
    records: list[dict[str, Any]] = []
    radii: list[float] = []
    try:
        for key in _DEFAULT_RADIUS_KEYS:
            radius = payload_radius(key)
            radii.append(radius.clash_radius_A)
            records.append(
                {
                    "key": radius.key,
                    "pdb_id": radius.pdb_id,
                    "clash_radius_A": radius.clash_radius_A,
                    "description": radius.description,
                    "note": radius.note,
                }
            )
    except PayloadRadiusError as exc:
        raise AffinityError(str(exc)) from exc
    return radii, records, "deposited_clash_radii"


def _theta_at(c_eff: object, kd_M: float) -> float | None:
    if isinstance(c_eff, bool) or not isinstance(c_eff, (int, float)):
        return None
    concentration = float(c_eff)
    if not math.isfinite(concentration) or concentration <= 0:
        return None
    return concentration / (concentration + kd_M)


def _finite(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def _verdict(
    holds: bool,
    theta: float,
    kd_M: float,
    c_eff: float,
    nano_theta: float | None,
    spy_half: float | None,
    drives_nano: bool,
    drives_spy: bool,
) -> str:
    nano_text = "not computed" if nano_theta is None else f"{nano_theta:.3e}"
    spy_text = "not computed" if spy_half is None else f"{spy_half:.3e} s"
    if not holds:
        return (
            f"Your Kd ({kd_M:.3e} M) is weaker than the local concentration ({c_eff:.3e} M). "
            f"Only {theta:.0%} of the pairs stay together. "
            "The reporter and the Spy lock are not driven at this length."
        )
    if drives_nano and drives_spy:
        return (
            f"The ends stay together ({theta:.0%} bound). "
            f"LgBiT–SmBiT occupancy is {nano_text}. "
            f"SpyCatcher–SpyTag half-life is {spy_text}."
        )
    return (
        f"The ends stay together ({theta:.0%} bound). "
        f"LgBiT–SmBiT occupancy is {nano_text}, below half. "
        f"SpyCatcher–SpyTag half-life is {spy_text}."
    )
