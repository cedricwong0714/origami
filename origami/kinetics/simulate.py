"""Run kinetics simulations from an explicit request body."""

from __future__ import annotations

from typing import Any

from origami.kinetics.covalent import simulate_covalent_timecourse
from origami.kinetics.rates import apply_user_rates, default_rate_slots
from origami.physical.recruitment import recruitment_occupancy


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


def simulate_kinetics(body: dict[str, Any]) -> dict[str, Any]:
    mode = body.get("mode")
    if mode not in ("recruitment_steady", "covalent_timecourse"):
        raise KineticsSimError(
            "mode must be 'recruitment_steady' or 'covalent_timecourse'"
        )

    rate_overrides = body.get("rates")
    if rate_overrides is not None and not isinstance(rate_overrides, dict):
        raise KineticsSimError("rates must be an object when present")
    slots = apply_user_rates(default_rate_slots(), rate_overrides)

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
        result = recruitment_occupancy(
            c_free_M=c_free,
            kon_per_M_s=kon,
            t_end_s=t_end,
            signal_on=signal_on,
        )
        derived: dict[str, float | None] = {"k_off_per_s": None}
        if kon is not None:
            derived["k_off_per_s"] = float(kon * result.kd_M)
        return {
            "mode": mode,
            "calibrated": False,
            "confidence_tier": result.confidence_tier,
            "human_review_required": True,
            "rate_slots": slots,
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

    # covalent_timecourse — every Spy rate must be in the request (or rates override)
    def _rate(name: str) -> float:
        if rate_overrides and name in rate_overrides:
            return _require_positive(name, rate_overrides[name])
        if name in body:
            return _require_positive(name, body[name])
        raise KineticsSimError(
            f"{name} is vacant in the schema and was not supplied for covalent_timecourse"
        )

    tag0 = _require_positive("tag0_M", body.get("tag0_M", 1.0))
    catcher0 = _require_positive("catcher0_M", body.get("catcher0_M", 1.0))
    k_on = _rate("spy_k_on_per_M_s")
    k_rev = _rate("spy_k_rev_per_s")
    k_bond = _rate("spy_k_bond_per_s")
    if k_on == 0 or k_rev == 0 or k_bond == 0:
        raise KineticsSimError("SpyTag rates must be strictly positive")

    t_end = float(body.get("t_end_s", 100.0))
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
    payload["rate_slots"] = slots
    payload["rates_used"] = {
        "spy_k_on_per_M_s": k_on,
        "spy_k_rev_per_s": k_rev,
        "spy_k_bond_per_s": k_bond,
    }
    return payload
