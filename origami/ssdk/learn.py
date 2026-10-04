"""SSDK run plus residual active learning on surrogate observations.

Structure, stability, docking, and kinetics stay separate models.
Surrogate rows correct the docking physics score through the residual
Gaussian process already in ``origami.design_engine``. They do not
overwrite a melting temperature, a chord, or a literature rate.

With fewer than three distinct lengths, the slope on the physics score
stays 1 and the kernel hyperparameters are not optimized. The posterior
still moves by the observed residual. With three or more distinct
lengths, hyperparameters may be optimized. ``gp_fitted`` is true only
in that case. ``calibrated`` stays false.

Stability is reported from the Phillips 2012 CTPRa DSC length model.
It does not remove a length from the surrogate search. Docking uses
caller radii when both are supplied. Otherwise the existing 25 Å
placeholder is named as a placeholder.

``literature_training`` is computed from that DSC table alone. Surrogate
rows are not an input to it.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from origami.engine import ClaspDesignEngine, Observation
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.physical.geometry import build_ctpr
from origami.physical.payload_radii import radii_for
from origami.physical.structure import structural_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, SPY_K_ON_PER_M_S
from origami.ssdk.batch_acquire import select_batch
from origami.ssdk.canonical_learner import (
    construct_flags,
    fit_sklearn_luminescence,
    geometry_feature_matrix,
)
from origami.ssdk.chassis import ChassisError, evaluate_chassis
from origami.ssdk.literature_train import train_literature
from origami.ssdk.multioutput import multioutput_block
from origami.ssdk.multifidelity_luminescence import multifidelity_luminescence_block
from origami.ssdk.quantify import QuantificationError, curve_request_from_body, quantify_luminescence_rows
from origami.stability.length_fit import fit_named_delta_g, fit_named_tm
from origami.stability.series import PHILLIPS_2012_CTPRA_DSC

_Z95 = 1.96


class SsdkLearnError(ValueError):
    """The surrogate request cannot be scored."""


def _sequence_block(body: dict[str, Any]) -> tuple[np.ndarray | None, str]:
    """Composition by default. ESM-2 only when requested, and only if the libraries import."""
    seq = body.get("sequence")
    if seq is None or seq == "":
        return None, "none"
    if not isinstance(seq, str):
        raise SsdkLearnError("sequence must be a string of amino acids")
    method = body.get("sequence_encoding", "composition")
    if method not in ("composition", "onehot", "esm2"):
        raise SsdkLearnError("sequence_encoding must be composition, onehot, or esm2")
    from src.gp_model.sequence_encoding import (  # noqa: PLC0415
        composition_features,
        encode_sequence,
        onehot_encoding,
    )

    try:
        if method == "composition":
            return composition_features(seq), "composition"
        if method == "onehot":
            return onehot_encoding(seq), "onehot"
        vector, used = encode_sequence(seq, method="esm2")
        return vector, used
    except ValueError as exc:
        raise SsdkLearnError(str(exc)) from exc


def learn_ssdk(body: dict[str, Any]) -> dict[str, Any]:
    """Score the library and recommend the next surrogate length."""
    if not isinstance(body, dict):
        raise SsdkLearnError("JSON object required")
    n_min = _int_field(body.get("n_min", 3), "n_min", minimum=3)
    n_max = _int_field(body.get("n_max", 24), "n_max", minimum=n_min)
    acquisition = body.get("acquisition", "ucb")
    if acquisition not in ("ucb", "ei", "entropy"):
        raise SsdkLearnError("acquisition must be ucb, ei, or entropy")
    learner = body.get("learner", "sklearn")
    if learner not in ("sklearn", "design_engine"):
        raise SsdkLearnError("learner must be sklearn or design_engine")
    batch_size = body.get("batch_size", 6)
    if isinstance(batch_size, bool) or not isinstance(batch_size, int):
        raise SsdkLearnError("batch_size must be an integer from 1 to 12")
    if batch_size < 1 or batch_size > 12:
        raise SsdkLearnError("batch_size must be an integer from 1 to 12")
    radii, radius_origin = _radii(body.get("payload_radii_A"), body.get("payload_names"))
    raw_observations = body.get("observations") or []
    quantification = _quantification(body, raw_observations)
    if quantification["applied"]:
        raw_observations = quantification["rows"]
    observations, mf_obs_rows = _observations(raw_observations, n_min, n_max)
    engine = ClaspDesignEngine(
        payload_radii_A=radii,
        n_min=n_min,
        n_max=n_max,
        acquisition=str(acquisition),
    )
    for obs in observations:
        engine.add_observation(obs)
    result = engine.run(thermal_prior=False)
    if result.next_experiment is None:
        raise SsdkLearnError("the library produced no next length")
    engine_next = result.next_experiment.n_repeats
    flags = construct_flags(body.get("construct") if isinstance(body.get("construct"), dict) else None)
    sequence_vector, sequence_method = _sequence_block(body)
    X_all = geometry_feature_matrix(result, n_max, flags, sequence_vector)
    use_scatter = bool(body.get("use_heteroscedastic_std", False))
    try:
        canonical = fit_sklearn_luminescence(
            result,
            mf_obs_rows,
            n_max,
            flags,
            sequence_vector=sequence_vector,
            sequence_method=sequence_method,
            use_heteroscedastic_std=use_scatter,
            X_all=X_all,
        )
        outputs = multioutput_block(
            result,
            mf_obs_rows,
            n_max,
            body.get("construct") if isinstance(body.get("construct"), dict) else None,
            sequence_vector=sequence_vector,
            sequence_method=sequence_method,
            X_all=X_all,
        )
        batch = select_batch(canonical, outputs, batch_size)
    except ValueError as exc:
        raise SsdkLearnError(str(exc)) from exc
    if learner == "sklearn" and canonical.get("fitted"):
        next_n = int(canonical["next_n"])
        next_reason = str(canonical["reason"])
        family = "sklearn_matern_residual"
    elif learner == "design_engine":
        next_n = engine_next
        next_reason = result.next_experiment.reason
        family = "design_engine"
    else:
        next_n = engine_next
        next_reason = result.next_experiment.reason
        family = "design_engine_fallback"
    distinct = sorted({obs.n_repeats for obs in observations})
    gp_fitted = len(distinct) >= 3
    highlighted = _highlighted(distinct, next_n)
    multifidelity = _multifidelity_block(
        result,
        mf_obs_rows,
        n_max,
        flags,
        sequence_vector,
        sequence_method,
        X_all,
    )
    recommendation = _recommendation(family, next_n, engine_next, batch, multifidelity)
    chassis_at_next_n = _chassis_at_next_n(body, next_n, radii, radius_origin)
    return {
        "calibrated": False,
        "confidence_tier": "hypothesis_only",
        "human_review_required": True,
        "gp_fitted": gp_fitted,
        "hyperparameters_optimized": gp_fitted,
        "alpha": result.posterior.alpha,
        "beta": result.posterior.beta,
        "alpha_fixed_at_one": len(distinct) < 3,
        "n_observations": len(observations),
        "distinct_lengths": distinct,
        "acquisition": result.next_experiment.acquisition_name,
        "learner_requested": learner,
        "learner_family": family,
        "design_engine_next_n": engine_next,
        "next_n": next_n,
        "next_reason": next_reason,
        "radius_origin": radius_origin,
        "payload_radii_A": radii,
        "evidence_level": result.evidence_level,
        "warnings": list(result.warnings)
        + [
            "Stability is reported beside this search and does not veto a length.",
            "A passing test of this loop is not scientific validation.",
        ],
        "candidates": _candidates(result),
        "slices": {
            "structure": _structure(highlighted),
            "stability": _stability(highlighted),
            "docking": _docking(result, highlighted, radius_origin),
            "kinetics": _kinetics(body.get("kinetics")),
        },
        "literature_training": train_literature(),
        "quantification": quantification,
        "canonical": canonical,
        "multioutput": outputs,
        "batch": batch,
        "multifidelity_luminescence": multifidelity,
        "recommendation": recommendation,
        "chassis_at_next_n": chassis_at_next_n,
    }


def _recommendation(
    family: str,
    next_n: int,
    design_engine_next_n: int,
    batch: dict[str, Any],
    multifidelity: dict[str, Any],
) -> dict[str, Any]:
    """Name which next length is primary. Do not average the models."""
    recommended = multifidelity.get("recommended_evaluation") or {}
    mf_n = recommended.get("n_repeats")
    return {
        "primary_family": family,
        "next_n": next_n,
        "design_engine_next_n": design_engine_next_n,
        "multifidelity_luminescence_n": None if mf_n is None else int(mf_n),
        "batch_n": [int(row["n_repeats"]) for row in batch.get("selected") or []],
        "calibrated": False,
        "note": (
            "primary next_n is the sklearn residual when that fit exists. "
            "design_engine_next_n is the older residual GP. "
            "multifidelity_luminescence_n is the luminescence multi-fidelity acquisition. "
            "batch_n is the greedy panel on the sklearn posterior. "
            "These models are not required to name the same length."
        ),
    }


def _chassis_at_next_n(
    body: dict[str, Any],
    next_n: int,
    radii: list[float],
    radius_origin: str,
) -> dict[str, Any]:
    """Score the primary next length with the chassis command's evaluation.

    Caller radii are forwarded. The default placeholder radius is not
    treated as a measured radius, so clash and C_eff stay uncomputed.
    Kinetics runs only when the posted block is the chassis block,
    including ``mode``. A learn-style kinetics dict without ``mode``
    is not filled with default concentrations. ``slices`` stay as they
    were.
    """
    chassis_body: dict[str, Any] = {"n_repeats": next_n}
    if radius_origin != "placeholder":
        chassis_body["radii_A"] = radii
    kinetics = body.get("kinetics")
    if isinstance(kinetics, dict) and "mode" in kinetics:
        chassis_body["kinetics"] = kinetics
    for key in ("indices", "linker_sigma_A", "lab_tm_C", "t_assay_C"):
        if body.get(key) is not None:
            chassis_body[key] = body[key]
    try:
        snapshot = evaluate_chassis(chassis_body)
    except ChassisError as exc:
        return {
            "computable": False,
            "calibrated": False,
            "n_repeats": next_n,
            "error": str(exc),
            "replaces_slices": False,
            "note": (
                "The chassis evaluation at the primary next length was not computed. "
                "slices are unchanged."
            ),
        }
    if radius_origin == "pdb_derived" and isinstance(snapshot.get("docking"), dict):
        snapshot["docking"]["radius_origin"] = "pdb_derived"
    snapshot["radius_origin_on_learn"] = radius_origin
    snapshot["replaces_slices"] = False
    snapshot["note"] = (
        "Same evaluation as origami ssdk chassis, at recommendation.next_n. "
        "slices.structure, slices.stability, slices.docking, and slices.kinetics "
        "are the library rows and are not replaced. "
        "calibrated stays false. A kinetics block without mode is not filled in."
    )
    return snapshot


def _quantification(body: dict[str, Any], rows: list[Any]) -> dict[str, Any]:
    """Leave caller y unchanged unless quantify_luminescence is true."""
    quantify = bool(body.get("quantify_luminescence", False))
    if not quantify:
        return {
            "applied": False,
            "calibrated": False,
            "learner_target": "caller_y",
            "note": (
                "Luminescence stayed on the scale of observations[].y. "
                "Set quantify_luminescence true and supply a standard curve "
                "to convert RLU to amount."
            ),
        }
    try:
        curve = curve_request_from_body(body)
        if curve is None:
            raise QuantificationError(
                "quantify_luminescence requires standard_curve with amount and rlu"
            )
        if not isinstance(rows, list):
            raise QuantificationError("observations must be a list")
        return quantify_luminescence_rows(
            rows,
            curve,
            str(body.get("amount_units") or ""),
        )
    except QuantificationError as exc:
        raise SsdkLearnError(str(exc)) from exc


def _multifidelity_block(
    result: Any,
    rows: list[dict[str, Any]],
    n_max: int,
    flags: dict[str, float],
    sequence_vector: np.ndarray | None,
    sequence_method: str,
    X_all: np.ndarray,
) -> dict[str, Any]:
    try:
        return multifidelity_luminescence_block(
            result,
            rows,
            n_max,
            flags,
            sequence_vector,
            sequence_method,
            X_all,
        )
    except ValueError as exc:
        raise SsdkLearnError(str(exc)) from exc


def _candidates(result: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    mean = result.posterior.mean
    std = result.posterior.std
    for index, n_repeats in enumerate(result.candidates):
        sigma = float(std[index])
        center = float(mean[index])
        rows.append(
            {
                "n_repeats": int(n_repeats),
                "physics_score": float(result.physics_scores[index]),
                "posterior_mean": center,
                "posterior_std": sigma,
                "posterior_95_lower": center - _Z95 * sigma,
                "posterior_95_upper": center + _Z95 * sigma,
                "p_instability": float(result.p_instability[index]),
                "interpolated": bool(result.posterior.interpolated[index]),
            }
        )
    return rows


def _highlighted(observed: list[int], next_n: int) -> list[int]:
    lengths = list(observed)
    if next_n not in lengths:
        lengths.append(next_n)
    return sorted(lengths)


def _structure(lengths: list[int]) -> dict[str, Any]:
    rows = []
    for n_repeats in lengths:
        report = structural_report(build_ctpr(n_repeats))
        rows.append(
            {
                "n_repeats": n_repeats,
                "contour_nm": report.contour_nm,
                "axial_span_A": report.axial_span_A,
                "rigid_screw": report.rigid_screw,
                "calibrated": False,
            }
        )
    return {
        "calibrated": False,
        "model": "deposited CTPR screw",
        "rows": rows,
        "note": "Contour is the screw model. A surrogate luminescence does not edit it.",
    }


def _stability(lengths: list[int]) -> dict[str, Any]:
    tm_fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    dg_fit = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    rows = []
    for n_repeats in lengths:
        tm = tm_fit.predict(n_repeats)
        dg = dg_fit.predict(n_repeats)
        rows.append(
            {
                "n_repeats": n_repeats,
                "tm_C": tm.value,
                "tm_sigma_C": tm.sigma,
                "tm_95_lower_C": tm.band_95_low,
                "tm_95_upper_C": tm.band_95_high,
                "past_longest_cited_length": tm.past_longest_cited_length,
                "delta_g": dg.value,
                "delta_g_sigma": dg.sigma,
                "calibrated": False,
            }
        )
    return {
        "calibrated": False,
        "series_id": PHILLIPS_2012_CTPRA_DSC,
        "rows": rows,
        "note": (
            "Melting temperature and unfolding ΔG are the Phillips 2012 "
            "CTPRa DSC length models. Surrogate luminescence does not replace them."
        ),
    }


def _docking(result: Any, lengths: list[int], radius_origin: str) -> dict[str, Any]:
    by_n = {int(n): index for index, n in enumerate(result.candidates)}
    rows = []
    for n_repeats in lengths:
        index = by_n[n_repeats]
        report = result.reports[n_repeats]
        rows.append(
            {
                "n_repeats": n_repeats,
                "physics_score": float(result.physics_scores[index]),
                "p_instability": float(result.p_instability[index]),
                "feasible": bool(report.feasible),
            }
        )
    note = (
        "Caller radii were used for clash and effective concentration."
        if radius_origin == "caller"
        else (
            "Both payload radii were omitted. Clash uses the CaM-M13 default (PDB 2BBM-derived) "
            "in origami.priors.DEFAULT_PAYLOAD_RADIUS_A. It is a structure-derived size scale, not a measured radius."
        )
    )
    return {
        "calibrated": False,
        "radius_origin": radius_origin,
        "equation": "score = (1 - P_instability) * log10(1 + C_eff / 1e-3 M)",
        "rows": rows,
        "note": note,
    }


def _kinetics(body: object) -> dict[str, Any]:
    if not isinstance(body, dict) or not body:
        return {
            "computable": False,
            "calibrated": False,
            "missing": ["kinetics block was not submitted"],
            "literature_k_on_per_M_s": SPY_K_ON_PER_M_S.value,
            "note": "Spy k_on stays the Zakeri 2012 prior until a lab rate is posted.",
        }
    payload = {
        "mode": "covalent_timecourse",
        "use_literature_priors": body.get("k_lock_per_M_s") is None,
        "tag0_M": body.get("tag0_M", 10e-6),
        "catcher0_M": body.get("catcher0_M", 10e-6),
    }
    if body.get("k_lock_per_M_s") is not None:
        payload["use_literature_priors"] = False
        payload["spy_k_on_per_M_s"] = body["k_lock_per_M_s"]
    try:
        simulated = simulate_kinetics(payload)
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
        "used_literature_prior": payload["use_literature_priors"],
        "literature_k_on_per_M_s": SPY_K_ON_PER_M_S.value,
        "simulation": simulated,
        "note": "The time course uses the lumped irreversible law. It is not trained on the surrogate y.",
    }


def _observations(
    rows: object, n_min: int, n_max: int
) -> tuple[list[Observation], list[dict[str, Any]]]:
    if not isinstance(rows, list):
        raise SsdkLearnError("observations must be a list")
    parsed: list[Observation] = []
    mf_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise SsdkLearnError(f"observations[{index}] must be an object")
        n_raw = row.get("n_repeats") if "n_repeats" in row else row.get("n")
        n_repeats = _int_field(n_raw, f"observations[{index}].n_repeats")
        if n_repeats < n_min or n_repeats > n_max:
            raise SsdkLearnError(
                f"observations[{index}].n_repeats is outside {n_min}–{n_max}"
            )
        y = _float_field(row.get("y"), f"observations[{index}].y")
        sigma = row.get("sigma", row.get("y_sigma"))
        sigma_value = (
            None
            if sigma is None
            else _float_field(sigma, f"observations[{index}].sigma")
        )
        if sigma_value is not None and sigma_value <= 0:
            raise SsdkLearnError(f"observations[{index}].sigma must be > 0 or omitted")
        fidelity = row.get("fidelity", 1)
        if fidelity not in (0, 1):
            raise SsdkLearnError(
                f"observations[{index}].fidelity must be 0 (dry) or 1 (wet)"
            )
        source = row.get("source", "surrogate")
        if not isinstance(source, str) or source.strip() == "":
            raise SsdkLearnError(
                f"observations[{index}].source must be a non-empty string"
            )
        output = row.get("output", "luminescence")
        if output not in (
            "luminescence",
            "locking_fraction",
            "expression",
            "solubility",
            "purity",
        ):
            raise SsdkLearnError(
                f"observations[{index}].output is not one of the five wet assays"
            )
        parsed.append(
            Observation(
                n_repeats=n_repeats,
                y=y,
                sigma=sigma_value,
                source=source.strip(),
                units=str(row.get("units") or "surrogate_readout"),
                notes="Caller-supplied surrogate. Not invented by the chassis.",
            )
        )
        mf_rows.append(
            {
                "n_repeats": n_repeats,
                "y": y,
                "sigma": sigma_value,
                "fidelity": int(fidelity),
                "output": output,
                "source": source.strip(),
            }
        )
    return parsed, mf_rows


def _radii(value: object, names: object = None) -> tuple[list[float], str]:
    if names is not None:
        if value is not None:
            raise SsdkLearnError("give payload_radii_A or payload_names, not both")
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise SsdkLearnError("payload_names must be a list of two strings")
        try:
            return radii_for(names), "pdb_derived"
        except (KeyError, ValueError) as exc:
            raise SsdkLearnError(str(exc)) from exc
    if value is None:
        radius = DEFAULT_PAYLOAD_RADIUS_A.value
        return [radius, radius], "placeholder"
    if not isinstance(value, list) or len(value) != 2:
        raise SsdkLearnError("payload_radii_A must be two angstrom values or omitted")
    radii = [
        _float_field(value[0], "payload_radii_A[0]"),
        _float_field(value[1], "payload_radii_A[1]"),
    ]
    if any(radius <= 0 for radius in radii):
        raise SsdkLearnError("payload radii must be > 0")
    return radii, "caller"


def _int_field(value: object, name: str, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise SsdkLearnError(f"{name} must be an integer")
    if minimum is not None and value < minimum:
        raise SsdkLearnError(f"{name} must be >= {minimum}")
    return value


def _float_field(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SsdkLearnError(f"{name} must be a finite number")
    number = float(value)
    if not math.isfinite(number):
        raise SsdkLearnError(f"{name} must be a finite number")
    return number
