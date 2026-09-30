"""Run kinetics simulations from an explicit request body."""

from __future__ import annotations

from typing import Any

from origami.kinetics.covalent import simulate_covalent_timecourse
from origami.kinetics.rates import apply_user_rates, default_rate_slots
from origami.physical.recruitment import recruitment_occupancy
from origami.priors import SPY_K_ON_PER_M_S, get_parameter_or_warn


class KineticsSimError(Exception):
    """User-facing simulation error (missing rates, bad mode)."""


def _require_positive(name: str, raw: object) -> float:
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise KineticsSimError(f"{name} must be a number")
    value = float(raw)
    if value != value or value in (float("inf"), float("-inf")):
        raise KineticsSimError(f"{name} must be finite")
    if value < 0:
        raise KineticsSimError(f"{name} must be >= 0")
    return value


def _slot_map(slots: list[Any]) -> dict[str, Any]:
    return {s.name: s for s in slots}


def _numeric_from_slot(slot: Any, name: str) -> float | None:
    if slot.value is None:
        get_parameter_or_warn(name, None, slot.source)
        return None
    return float(slot.value)


def simulate_kinetics(body: dict[str, Any]) -> dict[str, Any]:
    mode = body.get("mode")
    if mode not in ("recruitment_steady", "covalent_timecourse"):
        raise KineticsSimError(
            "mode must be 'recruitment_steady' or 'covalent_timecourse'"
        )

    rate_overrides = body.get("rates")
    if rate_overrides is not None and not isinstance(rate_overrides, dict):
        raise KineticsSimError("rates must be an object when present")

    merged: dict[str, Any] = dict(rate_overrides or {})
    for key in (
        "spy_k_on_per_M_s",
        "spy_k_rev_per_s",
        "spy_k_bond_per_s",
        "cam_m13_kd_M",
    ):
        if key in body and key not in merged:
            merged[key] = body[key]

    use_lit = body.get("use_literature_priors", True)
    if use_lit is False:
        for key in ("spy_k_on_per_M_s", "cam_m13_kd_M"):
            if key not in merged:
                merged[key] = None

    slots = apply_user_rates(default_rate_slots(), merged)

    if mode == "recruitment_steady":
        if "c_free_M" not in body:
            raise KineticsSimError("c_free_M is required for recruitment_steady")
        c_free = _require_positive("c_free_M", body["c_free_M"])
        kon = body.get("kon_per_M_s")
        if kon is not None:
            kon = _require_positive("kon_per_M_s", kon)
            if kon == 0:
                raise KineticsSimError("kon_per_M_s must be > 0 when supplied")
        t_end = body.get("t_end_s")
        if t_end is not None:
            t_end = _require_positive("t_end_s", t_end)
            if t_end == 0:
                raise KineticsSimError("t_end_s must be > 0 when supplied")
        signal_on = bool(body.get("signal_on", True))
        kd_slot = _slot_map(slots)["cam_m13_kd_M"]
        kd_val = _numeric_from_slot(kd_slot, "cam_m13_kd_M")
        if kd_val is None:
            raise KineticsSimError(
                "cam_m13_kd_M is vacant; supply a lab Kd or leave literature priors on"
            )
        kd_sigma = kd_slot.sigma
        result = recruitment_occupancy(
            c_free_M=c_free,
            kon_per_M_s=kon,
            kd_M=kd_val,
            kd_sigma_M=kd_sigma,
            t_end_s=t_end,
            signal_on=signal_on,
        )
        derived: dict[str, float | None] = {"k_off_per_s": None}
        if kon is not None:
            derived["k_off_per_s"] = float(kon * result.kd_M)
        return {
            "mode": mode,
            "calibrated": False,
            "confidence_tier": "hypothesis_only",
            "human_review_required": True,
            "rate_slots": [s.to_dict() for s in slots],
            "recruitment": {
                "theta_ss": result.theta_ss,
                "theta_95_lower": result.theta_95_lower,
                "theta_95_upper": result.theta_95_upper,
                "kd_M": result.kd_M,
                "kd_sigma_M": result.kd_sigma_M,
                "c_free_M": result.c_free_M,
                "kon_per_M_s": result.kon_per_M_s,
                "units": result.units,
                "time_s": None
                if result.time_s is None
                else [float(x) for x in result.time_s],
                "theta_t": None
                if result.theta_t is None
                else [float(x) for x in result.theta_t],
                "assumptions": result.assumptions,
                "warnings": result.warnings,
            },
            "derived": derived,
        }

    by_name = _slot_map(slots)
    k_on = _numeric_from_slot(by_name["spy_k_on_per_M_s"], "spy_k_on_per_M_s")
    if k_on is None:
        raise KineticsSimError(
            "spy_k_on_per_M_s is vacant in the schema and was not supplied "
            "for covalent_timecourse"
        )
    if k_on == 0:
        raise KineticsSimError("SpyTag rates must be strictly positive")
    k_rev = _numeric_from_slot(by_name["spy_k_rev_per_s"], "spy_k_rev_per_s")
    k_bond = _numeric_from_slot(by_name["spy_k_bond_per_s"], "spy_k_bond_per_s")
    if (k_rev is None) ^ (k_bond is None):
        raise KineticsSimError(
            "spy_k_rev_per_s and spy_k_bond_per_s must both be lab-supplied "
            "or both vacant (lumped Zakeri path)"
        )
    if k_rev is not None and (k_rev == 0 or k_bond == 0):
        raise KineticsSimError("SpyTag rates must be strictly positive")

    tag0 = _require_positive("tag0_M", body.get("tag0_M", 10e-6))
    catcher0 = _require_positive("catcher0_M", body.get("catcher0_M", 10e-6))
    t_end = float(body.get("t_end_s", 600.0))
    num_points = int(body.get("num_points", 100))
    sim = simulate_covalent_timecourse(
        tag0_M=tag0,
        catcher0_M=catcher0,
        k_on_per_M_s=k_on,
        k_rev_per_s=k_rev,
        k_bond_per_s=k_bond,
        t_end_s=t_end,
        num_points=num_points,
    )
    payload = sim.to_dict()
    payload["mode"] = mode
    payload["rate_slots"] = [s.to_dict() for s in slots]
    payload["rates_used"] = {
        "spy_k_on_per_M_s": k_on,
        "spy_k_rev_per_s": k_rev,
        "spy_k_bond_per_s": k_bond,
        "path": "three_step" if k_rev is not None else "lumped_irreversible",
        "literature_k_on_per_M_s": float(SPY_K_ON_PER_M_S.value),
    }
    return payload
