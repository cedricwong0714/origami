"""One length sweep: melt, holding, reporter, Spy, and clash.

Each repeat count from 3 to 24 is the same two calculations already
used on their own pages. The melting temperature and unfolding ΔG come
from one Phillips length fit. The association, LgBiT–SmBiT occupancy,
SpyCatcher–SpyTag half-life, and clash come from ``evaluate_affinity``
at that length.

A graft index, when supplied, is the second docking site (the first is
repeat index 0). Lengths that cannot hold that index keep the thermal
row and skip docking. When the graft is omitted, each length uses the
named M13 graft, or the C-terminal repeat when that length has no named
graft.

The marked length is a ranking rule, not a new biological constant:
among lengths whose calculated melting temperature is above the assay
temperature and whose association holds, pick the highest LgBiT–SmBiT
occupancy. Ties take the shorter scaffold. ``calibrated`` stays false.
"""

from __future__ import annotations

import math
from typing import Any

from origami.api.stability import stability_curve
from origami.docking.affinity import AffinityError, evaluate_affinity
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.series import DEFAULT_OPERATING_TEMPERATURE_C

_RANKING_RULE = (
    "A length is marked when it stays folded at the assay temperature, "
    "the two ends stay together, and the reporter occupancy is the highest in that group. "
    "A tie keeps the shorter scaffold. "
    "It is not a validated optimum."
)


class SweepError(ValueError):
    """The length sweep is not usable."""


def sweep_lengths(
    *,
    affinity: str,
    value: float,
    unit: str,
    graft_index: int | None = None,
    t_assay_C: float | None = None,
) -> dict[str, Any]:
    """Join the length-model melt with the affinity check at every n."""
    graft = _graft_index(graft_index)
    assay = DEFAULT_OPERATING_TEMPERATURE_C if t_assay_C is None else t_assay_C
    if isinstance(assay, bool) or not isinstance(assay, (int, float)):
        raise SweepError("t_assay_C must be a number")
    try:
        curve = stability_curve(float(assay))
    except (TypeError, ValueError) as exc:
        raise SweepError(str(exc)) from exc
    thermal = {int(point["n_repeats"]): point for point in curve["points"]}
    points: list[dict[str, Any]] = []
    for n_repeats in range(N_REPEATS_MIN, N_REPEATS_MAX + 1):
        row = thermal[n_repeats]
        points.append(_point(n_repeats, row, affinity, value, unit, graft))
    marked = _marked_length(points)
    reporter = [
        point["n_repeats"]
        for point in points
        if point["call"] == "reporter"
    ]
    computed = next((point for point in points if point["docking_computed"]), None)
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "t_assay_C": curve["t_assay_C"],
        "literature_series_id": curve["literature_series_id"],
        "model_name": curve["model_name"],
        "model_version": curve["model_version"],
        "affinity": affinity.strip().lower(),
        "input_value": None if computed is None else computed["input_value"],
        "input_unit": None if computed is None else computed["input_unit"],
        "kd_M": next((point["kd_M"] for point in points if point["kd_M"] is not None), None),
        "graft_index": graft,
        "graft_rule": (
            "Second docking site is the supplied graft index. "
            "Lengths shorter than or equal to that index skip docking."
            if graft is not None
            else (
                "Each length uses its named M13 graft. "
                "A length without a named graft uses the C-terminal repeat."
            )
        ),
        "ranking_rule": _RANKING_RULE,
        "marked_n": None if marked is None else marked["n_repeats"],
        "reporter_lengths": reporter,
        "any_length_drives_reporter": len(reporter) > 0,
        "points": points,
        "note": (
            "Thermal numbers are one length fit evaluated at each n. "
            "Docking numbers are the affinity check at that n. "
            "A length past the longest cited melt is an extrapolation of the fit. "
            "Payload occupancy is reported only when the association holds."
        ),
    }


def _point(
    n_repeats: int,
    row: dict[str, Any],
    affinity: str,
    value: float,
    unit: str,
    graft: int | None,
) -> dict[str, Any]:
    base = {
        "n_repeats": n_repeats,
        "tm_C": row["tm_C"],
        "tm_interval_low": row["tm_interval_low"],
        "tm_interval_high": row["tm_interval_high"],
        "delta_g": row["delta_g"],
        "thermal_state": row["thermal_state"],
        "past_longest_cited_length": row["past_longest_cited_length"],
    }
    if graft is not None and (graft <= 0 or graft >= n_repeats):
        return {
            **base,
            "docking_computed": False,
            "docking_skip_reason": (
                f"Graft index {graft} is outside n={n_repeats}, so docking is skipped."
            ),
            "indices": None,
            "chord_A": None,
            "c_eff_M": None,
            "p_clash": None,
            "kd_M": None,
            "input_value": None,
            "input_unit": None,
            "association_theta": None,
            "association_holds": None,
            "nanobit_theta": None,
            "drives_lgbit_smbit": False,
            "spy_half_life_s": None,
            "drives_spycatcher_spytag": False,
            "call": "docking_skipped",
        }
    try:
        report = evaluate_affinity(
            n_repeats,
            affinity=affinity,
            value=value,
            unit=unit,
            indices=None if graft is None else [0, graft],
        )
    except AffinityError as exc:
        raise SweepError(str(exc)) from exc
    point = {
        **base,
        "docking_computed": True,
        "docking_skip_reason": None,
        "indices": report["indices"],
        "chord_A": report["chord_A"],
        "c_eff_M": report["c_eff_M"],
        "p_clash": report["p_clash"],
        "kd_M": report["kd_M"],
        "input_value": report["input_value"],
        "input_unit": report["input_unit"],
        "association_theta": report["association_theta"],
        "association_holds": report["association_holds"],
        "nanobit_theta": report["nanobit_theta"],
        "drives_lgbit_smbit": report["drives_lgbit_smbit"],
        "spy_half_life_s": report["spy_half_life_s"],
        "drives_spycatcher_spytag": report["drives_spycatcher_spytag"],
    }
    point["call"] = _call(point)
    return point


def _call(point: dict[str, Any]) -> str:
    if point["thermal_state"] == "not_fit":
        return "not_fit"
    if point["thermal_state"] != "pass":
        return "below_assay"
    if not point["association_holds"]:
        return "folded_not_held"
    if point["drives_lgbit_smbit"]:
        return "reporter"
    return "held_reporter_dark"


def _marked_length(points: list[dict[str, Any]]) -> dict[str, Any] | None:
    eligible = [
        point
        for point in points
        if point["docking_computed"]
        and point["thermal_state"] == "pass"
        and point["association_holds"] is True
        and isinstance(point["nanobit_theta"], (int, float))
        and math.isfinite(float(point["nanobit_theta"]))
    ]
    if not eligible:
        return None
    return min(eligible, key=lambda point: (-float(point["nanobit_theta"]), point["n_repeats"]))


def _graft_index(graft_index: int | None) -> int | None:
    if graft_index is None:
        return None
    if isinstance(graft_index, bool) or not isinstance(graft_index, int):
        raise SweepError("graft_index must be an integer or omitted")
    if graft_index < 1 or graft_index > N_REPEATS_MAX - 1:
        raise SweepError(
            f"graft_index must be in [1, {N_REPEATS_MAX - 1}] so it can differ from repeat 0"
        )
    return graft_index
