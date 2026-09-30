"""Dry-lab measurements from models that already run.

A row here is a number the screw, the Cα cloud, or a cited thermal
series produced. It is a measurement record. It is not a use-case
optimum and it is not a wet-lab assay. ``calibrated`` stays false.
The residual GP is not fit on these scores: they are already the
model output, so a residual against themselves would be zero.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.gate import ThermalRow, thermal_gate
from origami.stability.series import (
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPR_DSC,
    PHILLIPS_2012_CTPRA_CD,
    PHILLIPS_2012_CTPRA_DSC,
    delta_g_at_n,
    load_named_series,
)

# One series at a time. These are not averaged.
STABILITY_SERIES = (
    PHILLIPS_2012_CTPRA_DSC,
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPRA_CD,
    PHILLIPS_2012_CTPR_DSC,
)

_SOURCE = "dry_lab"


def stability_panel(t_assay_C: float) -> list[dict[str, Any]]:
    """Tm gate and printed ΔG for every named series, at every library n.

    Series stay separate. A missing Tm stays extrapolated or omitted.
    Nothing is interpolated.
    """
    if isinstance(t_assay_C, bool) or not isinstance(t_assay_C, (int, float)):
        raise TypeError("t_assay_C must be a number")
    assay = float(t_assay_C)
    if not math.isfinite(assay):
        raise ValueError("t_assay_C must be finite")
    rows: list[dict[str, Any]] = []
    for series_id in STABILITY_SERIES:
        loaded = load_named_series(series_id)
        thermal_rows = [
            ThermalRow(
                n_repeats=obs.n_repeats,
                observable=obs.observable,
                value=float(obs.value),
                units=obs.units,
                uncertainty=None if obs.uncertainty is None else float(obs.uncertainty),
                data_class="literature",
            )
            for obs in loaded
            if obs.observable == "Tm_C"
        ]
        for n_repeats in range(N_REPEATS_MIN, N_REPEATS_MAX + 1):
            gate = thermal_gate(n_repeats, assay, thermal_rows)
            dg = delta_g_at_n(series_id, n_repeats)
            # Copy the printed Tm uncertainty. The gate envelope uses
            # zero width when a row prints none, and subtracting that
            # width from Tm would report a sigma of 0. Null stays null.
            matched_tm = [obs for obs in loaded if obs.n_repeats == n_repeats]
            if len(matched_tm) == 1 and matched_tm[0].uncertainty is not None:
                tm_uncertainty_C: float | None = float(matched_tm[0].uncertainty)
            else:
                tm_uncertainty_C = None
            # ``thermal_gate`` keeps a zero-width envelope when a row
            # prints no uncertainty (low = high = Tm). That width is not
            # a printed sigma. The gate's pass/fail result is unchanged.
            # This panel is what the confirmation page reads, so a missing
            # printed uncertainty is omitted here: both interval ends are
            # null, and ``tm_uncertainty_C`` stays null. Null is not 0.
            if tm_uncertainty_C is None:
                tm_interval_low: float | None = None
                tm_interval_high: float | None = None
            else:
                tm_interval_low = (
                    None if gate.interval_low is None else float(gate.interval_low)
                )
                tm_interval_high = (
                    None if gate.interval_high is None else float(gate.interval_high)
                )
            rows.append(
                {
                    "source": "literature_lookup",
                    "calibrated": False,
                    "series_id": series_id,
                    "n_repeats": int(n_repeats),
                    "t_assay_C": assay,
                    "thermal_state": gate.state,
                    "tm_C": None if gate.tm_C is None else float(gate.tm_C),
                    "tm_uncertainty_C": tm_uncertainty_C,
                    "tm_interval_low": tm_interval_low,
                    "tm_interval_high": tm_interval_high,
                    "thermal_reason": gate.reason,
                    "delta_g": None if dg is None else float(dg.value),
                    "delta_g_units": None if dg is None else dg.units,
                    "delta_g_uncertainty": (
                        None if dg is None or dg.uncertainty is None else float(dg.uncertainty)
                    ),
                }
            )
    return rows


def cloud_radial_measurements(scene: dict[str, Any]) -> list[dict[str, Any]]:
    """Radial extent of the placed Cα cloud, one row per repeat.

    This measures the coordinates already placed. It does not add a radius
    constant. Side chains are not in the cloud.
    """
    cloud = np.asarray(scene["ca_A"], dtype=float)
    n_repeats = int(scene["n_repeats"])
    per = int(scene["residues_per_repeat"])
    if cloud.shape != (n_repeats * per, 3):
        raise ValueError("Cα cloud shape does not match n_repeats * 34")
    rows: list[dict[str, Any]] = []
    for index in range(n_repeats):
        block = cloud[index * per : (index + 1) * per]
        radial = np.sqrt(block[:, 0] ** 2 + block[:, 1] ** 2)
        rows.append(
            {
                "source": _SOURCE,
                "calibrated": False,
                "observable": "ca_radial_A",
                "n_repeats": n_repeats,
                "repeat_index": index,
                "value_mean_A": float(radial.mean()),
                "value_min_A": float(radial.min()),
                "value_max_A": float(radial.max()),
                "units": "Å",
                "method": "placed consensus C-alpha cloud",
                "uncertainty": None,
            }
        )
    return rows


def drylab_dataset(
    report: dict[str, Any],
    confirmation: dict[str, Any] | None,
    scene: dict[str, Any],
    *,
    t_assay_C: float,
) -> dict[str, Any]:
    """Long-form measurements plus the next coordinate to measure.

    ``next_n`` and ``next_delta_i`` are acquisition coordinates. They
    name the next point to measure. They are not use-case optima.
    """
    measurements: list[dict[str, Any]] = []
    if confirmation is not None:
        for row in confirmation["rows"]:
            measurements.extend(_length_measurements(row))
    separation = report.get("separation") or {}
    for candidate in separation.get("candidates") or []:
        measurements.extend(_separation_measurements(int(report["n_repeats"]), candidate))
    cloud_rows = cloud_radial_measurements(scene)
    measurements.extend(cloud_rows)
    panel = stability_panel(t_assay_C)
    return {
        "calibrated": False,
        "gp_fitted": False,
        "source": _SOURCE,
        "purpose": "measurements of the models. Not use-case optima.",
        "measurements": measurements,
        "stability_panel": panel,
        "active_learning": {
            "gp_fitted": False,
            "calibrated": False,
            "next_n": report.get("next_n"),
            "next_delta_i": separation.get("next_delta_i"),
            "acquisition_name": separation.get("acquisition_name"),
            "notes": [
                "next_n and next_delta_i are the next measurement coordinates.",
                "They are not agriculture, biomarker, or general-use optima.",
                "The residual GP is not fit. These dry-lab scores are the model output, not an assay residual.",
                "A typed assay y can be added later. It is not invented here.",
            ],
        },
    }


def _length_measurements(row: dict[str, Any]) -> list[dict[str, Any]]:
    n_repeats = int(row["n_repeats"])
    specs = (
        ("contour_nm", row["contour_nm"], "nm", "n * deposited rise", None),
        ("end_pair_chord_A", row["end_pair_chord_A"], "Å", "structural_report", row["end_pair_chord_sigma_A"]),
        ("end_pair_facing_cosine", row["end_pair_facing_cosine"], "1", "cos(delta * twist)", None),
        ("p_instability", row["p_instability"], "1", "delta_method_ca_envelope", None),
        ("end_pair_c_eff_M", row["end_pair_c_eff_M"], "M", "kratky_porod_pair", None),
        ("physics_score", row["physics_score"], "1", "physics_report", None),
    )
    out: list[dict[str, Any]] = []
    for observable, value, units, method, uncertainty in specs:
        if value is None:
            continue
        out.append(
            {
                "source": _SOURCE,
                "calibrated": False,
                "domain": "structure" if observable != "physics_score" else "score",
                "observable": observable,
                "n_repeats": n_repeats,
                "delta_i": n_repeats - 1,
                "value": float(value),
                "uncertainty": None if uncertainty is None else float(uncertainty),
                "units": units,
                "method": method,
            }
        )
    out.append(
        {
            "source": _SOURCE,
            "calibrated": False,
            "domain": "structure",
            "observable": "rigid_screw",
            "n_repeats": n_repeats,
            "delta_i": None,
            "value": 1.0 if row["rigid_screw"] else 0.0,
            "uncertainty": None,
            "units": "bool",
            "method": "contour <= persistence length 15 nm",
        }
    )
    return out


def _separation_measurements(n_repeats: int, candidate: dict[str, Any]) -> list[dict[str, Any]]:
    delta = int(candidate["delta_i"])
    specs = (
        ("chord_A", candidate["chord_A"], candidate.get("chord_sigma_A"), "Å"),
        ("facing_cosine", candidate["facing_cosine"], None, "1"),
        ("p_clash", candidate["p_clash"], None, "1"),
        ("c_eff_M", candidate["c_eff_M"], None, "M"),
        ("physics_score", candidate["physics_score"], None, "1"),
    )
    rows: list[dict[str, Any]] = []
    for observable, value, uncertainty, units in specs:
        rows.append(
            {
                "source": _SOURCE,
                "calibrated": False,
                "domain": "separation",
                "observable": observable,
                "n_repeats": n_repeats,
                "delta_i": delta,
                "value": float(value),
                "uncertainty": None if uncertainty is None else float(uncertainty),
                "units": units,
                "method": "separation_library",
            }
        )
    return rows
