"""Run every lab section the caller actually filled in.

A missing section is returned as not computable, with the missing
fields named. It is not filled from a literature prior. Screw
coordinates, when a repeat count is present, are the existing geometry
model. Expression on a gel does not change them.
"""

from __future__ import annotations

import math
from typing import Any

from origami.assay.calcium import (
    fit_calcium_response,
    scrambled_ratio,
    temperature_luminosities,
)
from origami.assay.window import (
    admissibility,
    coefficient_of_variation,
    fit_half_life,
    fit_standard_curve,
)
from origami.bridging.ratios import bridging_ratios
from origami.kinetics.lock_fit import fit_lock
from origami.lab.schema import lab_schema
from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report

_PREP_FLAGS = (
    "expresses",
    "mass_within_10_percent",
    "native_page_shift",
    "expressed_n3",
    "expressed_n8",
    "expressed_n14",
    "expressed_n17",
)


def run_lab(body: dict[str, Any]) -> dict[str, Any]:
    """Evaluate prep, assay window, calcium, lock, and bridging."""
    if not isinstance(body, dict):
        raise LabRunError("JSON object required")
    _reject_nonfinite(body)
    prep = body.get("prep") or {}
    if prep is not None and not isinstance(prep, dict):
        raise LabRunError("prep must be an object")
    window = body.get("assay_window") or {}
    if not isinstance(window, dict):
        raise LabRunError("assay_window must be an object")
    calcium = body.get("calcium") or {}
    if not isinstance(calcium, dict):
        raise LabRunError("calcium must be an object")
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "schema_version": lab_schema()["schema_version"],
        "prep": _prep(prep),
        "assay_window": _window(window),
        "calcium": _calcium(calcium),
        "lock": fit_lock(body["lock"])
        if isinstance(body.get("lock"), dict)
        else _absent("lock"),
        "bridging": bridging_ratios(body["bridging"])
        if isinstance(body.get("bridging"), dict)
        else _absent("bridging"),
        "residual_gp": _residual_gp(body),
    }


def _residual_gp(body: dict[str, Any]) -> dict[str, Any]:
    n_rows = _observation_count(body.get("observations"))
    if not body.get("fit_residual_gp", False):
        return {
            "fitted": False,
            "n_rows": n_rows,
            "reason": (
                "The residual Gaussian process stays unfitted. "
                "This chassis has no physics score on the luminescence scale."
            ),
        }
    if n_rows == 0:
        return {
            "fitted": False,
            "n_rows": 0,
            "calibrated": False,
            "reason": "fit_residual_gp is True but no observations were supplied.",
        }
    try:
        from origami.ssdk.learn import learn_ssdk

        learn_body: dict[str, Any] = {
            "observations": body.get("observations"),
            "acquisition": body.get("acquisition", "ucb"),
        }
        if "payload_radii_A" in body:
            learn_body["payload_radii_A"] = body["payload_radii_A"]
        res = learn_ssdk(learn_body)
        return {
            "fitted": res["gp_fitted"],
            "calibrated": False,
            "n_rows": res["n_observations"],
            "alpha": res["alpha"],
            "beta": res["beta"],
            "distinct_lengths": res["distinct_lengths"],
            "next_n": res["next_n"],
            "next_reason": res["next_reason"],
            "acquisition": res["acquisition"],
            "candidates": res["candidates"],
            "warnings": [
                "Residual GP fitted using lab observations against SSDK physics scores.",
                "calibrated stays false. A passing GP fit is not wet-lab validation.",
            ],
        }
    except Exception as exc:
        return {
            "fitted": False,
            "n_rows": n_rows,
            "calibrated": False,
            "reason": f"Residual GP fitting failed: {exc}",
        }


class LabRunError(ValueError):
    """The request is not a usable lab body."""


def _absent(section: str) -> dict[str, Any]:
    return {
        "computable": False,
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "missing": [f"{section} was not submitted"],
        "warnings": [],
    }


def _prep(prep: dict[str, Any]) -> dict[str, Any]:
    record: dict[str, Any] = {
        "computable": True,
        "calibrated": False,
        "updates_screw": False,
        "converts_mass_to_radius": False,
        "construct_id": prep.get("construct_id"),
        "concentration_uM": prep.get("concentration_uM"),
        "concentration_sigma_uM": prep.get("concentration_sigma_uM"),
        "soluble_fraction": prep.get("soluble_fraction"),
        "purity_call": prep.get("purity_call"),
        "n_repeats": prep.get("n_repeats"),
        "warnings": [
            "Concentration is a prep quantity. It is not a payload radius.",
            "A gel call does not move the screw coordinates.",
        ],
    }
    for flag in _PREP_FLAGS:
        if flag in prep:
            record[flag] = prep[flag]
    n_repeats = prep.get("n_repeats")
    if isinstance(n_repeats, int) and not isinstance(n_repeats, bool):
        record["structure_context"] = _structure_context(n_repeats)
    else:
        record["structure_context"] = None
    return record


def _structure_context(n_repeats: int) -> dict[str, Any]:
    geometry = build_ctpr(n_repeats)
    report = structural_report(geometry)
    return {
        "n_repeats": n_repeats,
        "contour_nm": report.contour_nm,
        "rigid_screw": report.rigid_screw,
        "calibrated": False,
        "source": "existing CTPR screw model; not a distance measured in this lab",
    }


def _window(window: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"calibrated": False}
    standard = window.get("standard_curve")
    if isinstance(standard, dict):
        out["standard_curve"] = fit_standard_curve(
            standard.get("amount"), standard.get("rlu")
        )
    elif "amount" in window and "rlu" in window:
        out["standard_curve"] = fit_standard_curve(
            window.get("amount"), window.get("rlu")
        )
    else:
        out["standard_curve"] = _absent("standard_curve")
    decay = window.get("furimazine")
    if isinstance(decay, dict):
        out["furimazine"] = fit_half_life(decay.get("time_min"), decay.get("rlu"))
    else:
        out["furimazine"] = _absent("furimazine")
    if "cv_values" in window:
        out["cv"] = coefficient_of_variation(window.get("cv_values"))
    else:
        out["cv"] = _absent("cv")
    if "check_rlu" in window or "rlu_low" in window or "rlu_high" in window:
        out["linear_range"] = admissibility(
            window.get("check_rlu"),
            window.get("rlu_low"),
            window.get("rlu_high"),
        )
    else:
        out["linear_range"] = _absent("linear_range")
    return out


def _calcium(calcium: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"calibrated": False, "replaces_cam_m13_kd": False}
    if "ca_M" in calcium and "rlu" in calcium:
        out["dose_response"] = fit_calcium_response(
            calcium.get("ca_M"), calcium.get("rlu")
        )
    else:
        out["dose_response"] = _absent("calcium dose-response")
    if "wt_rlu" in calcium or "scrambled_rlu" in calcium:
        out["specificity"] = scrambled_ratio(
            calcium.get("wt_rlu"),
            calcium.get("scrambled_rlu"),
            calcium.get("wt_sigma"),
            calcium.get("scrambled_sigma"),
        )
    else:
        out["specificity"] = _absent("scrambled M13")
    if any(key in calcium for key in ("rlu_25_C", "rlu_30_C", "rlu_37_C")):
        out["temperature"] = temperature_luminosities(
            calcium.get("rlu_25_C"),
            calcium.get("rlu_30_C"),
            calcium.get("rlu_37_C"),
            calcium.get("sigma_25_C"),
            calcium.get("sigma_30_C"),
            calcium.get("sigma_37_C"),
        )
    else:
        out["temperature"] = _absent("temperature luminosities")
    return out


def _observation_count(observations: object) -> int:
    if not isinstance(observations, list):
        return 0
    return len(observations)


def _reject_nonfinite(value: object, path: str = "body") -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise LabRunError(f"{path} must be finite")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            _reject_nonfinite(item, f"{path}.{key}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _reject_nonfinite(item, f"{path}[{index}]")
