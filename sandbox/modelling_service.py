"""Run the live chassis, binding, length series, and next-length learner.

These wrappers do not add constants. They call evaluate_chassis,
simulate_kinetics, and learn_ssdk.
"""

from __future__ import annotations

from typing import Any

from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from origami.ssdk.chassis import ChassisError, evaluate_chassis
from origami.ssdk.learn import SsdkLearnError, learn_ssdk


def score_length(
    n_repeats: int,
    radii_A: list[float] | None = None,
    kinetics: dict[str, Any] | None = None,
    lab_tm_C: float | None = None,
) -> dict[str, Any]:
    """Score one repeat count. Clash needs two radii."""
    body: dict[str, Any] = {"n_repeats": int(n_repeats)}
    if radii_A is not None:
        body["radii_A"] = radii_A
    if kinetics is not None:
        body["kinetics"] = kinetics
    if lab_tm_C is not None:
        body["lab_tm_C"] = lab_tm_C
    try:
        return evaluate_chassis(body)
    except ChassisError as exc:
        raise ValueError(str(exc)) from exc


def length_series(
    n_min: int = N_REPEATS_MIN,
    n_max: int = N_REPEATS_MAX,
    radii_A: list[float] | None = None,
) -> list[dict[str, Any]]:
    """Screw and Phillips melt for every n in the range. Clash only with radii."""
    if n_min < N_REPEATS_MIN or n_max > N_REPEATS_MAX or n_min > n_max:
        raise ValueError(
            f"n_min and n_max must satisfy {N_REPEATS_MIN} ≤ n_min ≤ n_max ≤ {N_REPEATS_MAX}"
        )
    rows: list[dict[str, Any]] = []
    for n_repeats in range(int(n_min), int(n_max) + 1):
        report = score_length(n_repeats, radii_A=radii_A)
        docking = report["docking"]
        stability = report["stability"]
        structure = report["structure"]
        rows.append(
            {
                "n_repeats": n_repeats,
                "contour_nm": structure["contour_nm"],
                "axial_span_A": structure["axial_span_A"],
                "rigid_screw": structure["rigid_screw"],
                "tm_C": stability["tm_C"],
                "tm_95_lower_C": stability["tm_95_lower_C"],
                "tm_95_upper_C": stability["tm_95_upper_C"],
                "delta_g": stability["delta_g"],
                "past_longest_cited_length": stability["past_longest_cited_length"],
                "chord_A": docking["chord_A"],
                "indices": docking["indices"],
                "clash_computable": docking["clash_computable"],
                "p_clash": docking.get("p_clash"),
                "c_eff_M": docking.get("c_eff_M"),
            }
        )
    return rows


def run_binding(mode: str, **fields: Any) -> dict[str, Any]:
    """Run one binding calculation. Concentrations are moles per litre."""
    body: dict[str, Any] = {"mode": mode, **fields}
    try:
        return simulate_kinetics(body)
    except KineticsSimError as exc:
        raise ValueError(str(exc)) from exc


def suggest_next_length(
    n_min: int,
    n_max: int,
    observations: list[dict[str, Any]] | None = None,
    radii_A: list[float] | None = None,
    acquisition: str = "ucb",
) -> dict[str, Any]:
    """Suggest the next repeat count. A pass cutoff is not a measured result."""
    body: dict[str, Any] = {
        "n_min": int(n_min),
        "n_max": int(n_max),
        "acquisition": acquisition,
        "observations": observations or [],
    }
    if radii_A is not None:
        body["payload_radii_A"] = radii_A
    try:
        return learn_ssdk(body)
    except SsdkLearnError as exc:
        raise ValueError(str(exc)) from exc
