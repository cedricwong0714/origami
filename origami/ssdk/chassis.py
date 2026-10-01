"""One evaluation of the four SSDK chassis.

Structure returns the screw. Stability returns the Phillips length
model, and a caller melting temperature only when one was typed.
Docking returns the chord always, and clash plus C_eff only with
caller radii. Kinetics runs only with the rates and concentrations
in the request. Surrogate rows are not invented here. Active learning
stays on ``POST /api/ssdk/learn``.
"""

from __future__ import annotations

import math
from typing import Any

from origami.docking.evaluate import DockingError, evaluate_docking
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN, SPY_K_ON_PER_M_S
from origami.stability.length_fit import fit_named_delta_g, fit_named_tm
from origami.stability.series import (
    DEFAULT_OPERATING_TEMPERATURE_C,
    PHILLIPS_2012_CTPRA_DSC,
)


class ChassisError(ValueError):
    """The SSDK request is not usable."""


def evaluate_chassis(body: dict[str, Any]) -> dict[str, Any]:
    """Run structure, stability, docking, and kinetics for one length."""
    if not isinstance(body, dict):
        raise ChassisError("JSON object required")
    n_repeats = body.get("n_repeats", 8)
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise ChassisError("n_repeats must be an integer")
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise ChassisError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    kinetics_body = (
        body.get("kinetics") if isinstance(body.get("kinetics"), dict) else {}
    )
    try:
        docking = evaluate_docking(
            n_repeats,
            indices=_optional_indices(body.get("indices")),
            radii_A=_optional_radii(body.get("radii_A")),
            linker_sigma_A=_optional_float(
                body.get("linker_sigma_A"), "linker_sigma_A"
            ),
            spy_k_on_per_M_s=_optional_float(
                kinetics_body.get("spy_k_on_per_M_s"), "kinetics.spy_k_on_per_M_s"
            ),
            spy_k_on_sigma=_optional_float(
                kinetics_body.get("spy_k_on_sigma"), "kinetics.spy_k_on_sigma"
            ),
        )
    except DockingError as exc:
        raise ChassisError(str(exc)) from exc
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "n_repeats": n_repeats,
        "structure": _structure(n_repeats),
        "stability": _stability(n_repeats, body.get("lab_tm_C"), body.get("t_assay_C")),
        "docking": docking,
        "kinetics": _kinetics(body.get("kinetics")),
    }


def _structure(n_repeats: int) -> dict[str, Any]:
    report = structural_report(build_ctpr(n_repeats))
    return {
        "calibrated": False,
        "n_repeats": n_repeats,
        "contour_nm": report.contour_nm,
        "axial_span_A": report.axial_span_A,
        "rise_A": report.rise_A,
        "rigid_screw": report.rigid_screw,
        "persistence_length_nm": report.persistence_length_nm,
        "note": "Contour uses n times the deposited rise. It is not a measured end-to-end distance.",
    }


def _stability(n_repeats: int, lab_tm: object, t_assay: object) -> dict[str, Any]:
    assay = (
        DEFAULT_OPERATING_TEMPERATURE_C
        if t_assay is None
        else _required_float(t_assay, "t_assay_C")
    )
    tm = fit_named_tm(PHILLIPS_2012_CTPRA_DSC).predict(n_repeats)
    dg = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC).predict(n_repeats)
    lab_value = None if lab_tm is None else _required_float(lab_tm, "lab_tm_C")
    lab_pass = None if lab_value is None else lab_value > assay
    return {
        "calibrated": False,
        "series_id": PHILLIPS_2012_CTPRA_DSC,
        "t_assay_C": assay,
        "tm_C": tm.value,
        "tm_sigma_C": tm.sigma,
        "tm_95_lower_C": tm.band_95_low,
        "tm_95_upper_C": tm.band_95_high,
        "past_longest_cited_length": tm.past_longest_cited_length,
        "delta_g": dg.value,
        "delta_g_sigma": dg.sigma,
        "delta_g_95_lower": dg.band_95_low,
        "delta_g_95_upper": dg.band_95_high,
        "lab_tm_C": lab_value,
        "lab_tm_above_assay": lab_pass,
        "note": (
            "The melting temperature and ΔG are the Phillips 2012 CTPRa DSC length models. "
            "A typed lab Tm is compared with the assay temperature and does not refit that model."
        ),
    }


def _kinetics(body: object) -> dict[str, Any]:
    if not isinstance(body, dict) or "mode" not in body:
        return {
            "computable": False,
            "calibrated": False,
            "missing": ["kinetics.mode plus the concentrations that mode requires"],
            "literature_k_on_per_M_s": SPY_K_ON_PER_M_S.value,
            "note": "No rate was invented. Recruitment needs c_free_M. Covalent locking needs the Spy rate or the literature prior.",
        }
    try:
        simulated = simulate_kinetics(body)
    except KineticsSimError as exc:
        return {
            "computable": False,
            "calibrated": False,
            "missing": [str(exc)],
            "literature_k_on_per_M_s": SPY_K_ON_PER_M_S.value,
        }
    return {
        "computable": True,
        "calibrated": False,
        "literature_k_on_per_M_s": SPY_K_ON_PER_M_S.value,
        "simulation": _kinetics_summary(simulated),
        "note": "Kinetics uses the posted rates. Surrogate y is not part of this chassis.",
    }


def _kinetics_summary(simulated: dict[str, Any]) -> dict[str, Any]:
    """Keep the scalar outputs. Drop long time-series arrays."""
    summary = {
        key: value
        for key, value in simulated.items()
        if key not in {"time_s", "series", "theta_t"}
    }
    summary["calibrated"] = simulated.get("calibrated", False)
    return summary


def _optional_indices(value: object) -> list[int] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ChassisError("indices must be two integers or omitted")
    parsed: list[int] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, int):
            raise ChassisError("each index must be an integer")
        parsed.append(item)
    return parsed


def _optional_radii(value: object) -> list[float] | None:
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ChassisError("radii_A must be two numbers or omitted")
    return [
        _required_float(value[0], "radii_A[0]"),
        _required_float(value[1], "radii_A[1]"),
    ]


def _optional_float(value: object, name: str) -> float | None:
    if value is None:
        return None
    return _required_float(value, name)


def _required_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ChassisError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise ChassisError(f"{name} must be a finite number")
    return number
