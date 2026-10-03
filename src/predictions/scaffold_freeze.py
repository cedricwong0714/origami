"""Prospective freeze for one CTPR repeat count.

Contour and axial span come from the canonical screw. Phillips Tm and
unfolding ΔG come from the length curve on ``phillips2012_ctpra_dsc``.
Both change with repeat count.

``predict_luminescence`` does not take a repeat count. The calcium
curve stored here is the same on every scaffold file. Its interval is
the fixed ±30% placeholder, not a propagated 95% interval.

``calibrated`` stays false. A checksummed file is not a wet-lab result.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np

from origami.physical.geometry import build_ctpr
from origami.physical.structure import structural_report
from origami.priors import CTPR_RISE_A
from origami.stability.length_fit import (
    MODEL_NAME,
    MODEL_VERSION,
    LengthPrediction,
    fit_named_delta_g,
    fit_named_tm,
    fit_public_dict,
)
from origami.stability.series import PHILLIPS_2012_CTPRA_DSC
from origami.stability.thermo import thermo_prefill
from src.core.clasp_assembly import CLASPParameters, predict_luminescence
from src.predictions.freeze import freeze_prediction

# Software identity of this freeze layout. Not a biological constant.
SCAFFOLD_FREEZE_VERSION = "scaffold_freeze_v1"

# Planned series. Computable lengths outside this tuple are still
# allowed. Membership is not a calibration.
PLANNED_REPEAT_COUNTS = (3, 8, 14)

# Standard-normal 97.5 percentile. The rise band is value ± this factor
# times the deposited sample standard deviation. It is not a biological
# parameter and it is not a wet-lab confidence interval.
STANDARD_NORMAL_97_5 = 1.96

# 1 nm = 10 Å. Same conversion as origami.physical.geometry.
_NM_TO_A = 10.0

# Same defaults as `origami freeze` when the caller does not pass a grid.
# They are command defaults, not a measured calcium dose.
DEFAULT_CALCIUM_UM = (0.1, 0.5, 1.0, 2.0, 5.0, 10.0)
DEFAULT_E_T_M = 1e-6
DEFAULT_M_T_M = 1e-6
DEFAULT_T_END_S = 3600.0

_LUMINESCENCE_METHOD = "fixed_relative_placeholder_pm_30_percent"
_RISE_METHOD = "delta_method_deposited_rise_sample_std"
_LENGTH_METHOD = "length_curve_linearized_covariance"
_LUMINESCENCE_MODEL = "clasp_assembly_1.0.0"

_K_LOCK_SOURCE = (
    "k_lock=0.003 s^-1 is the existing ODE prior. "
    "origami.priors records that this value is not printed "
    "in Zakeri et al. 2012."
)


def _require_repeat_count(n_repeats: int) -> int:
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise TypeError("n_repeats must be an integer")
    if n_repeats < 1:
        raise ValueError("n_repeats must be an integer >= 1")
    return n_repeats


def _require_calcium_uM(calcium_uM: Sequence[float]) -> list[float]:
    values = [float(item) for item in calcium_uM]
    if not values:
        raise ValueError("calcium_uM must contain at least one concentration")
    for value in values:
        if not np.isfinite(value) or value < 0.0:
            raise ValueError("calcium_uM values must be finite and >= 0")
    return values


def _rise_interval(repeat_factor: int, *, to_nm: bool) -> dict[str, Any]:
    """Linear band for ``repeat_factor * rise``.

    Rise sigma is the sample standard deviation already stored on
    ``CTPR_RISE_A``. Multiplying by the repeat factor is the delta
    method for a product with a fixed integer. It does not add a new
    measured uncertainty.
    """
    if repeat_factor < 0:
        raise ValueError("repeat_factor must be >= 0")
    if CTPR_RISE_A.sigma is None:
        raise RuntimeError("CTPR_RISE_A.sigma is missing; no rise band was invented")
    scale = 1.0 / _NM_TO_A if to_nm else 1.0
    value = repeat_factor * float(CTPR_RISE_A.value) * scale
    sigma = repeat_factor * float(CTPR_RISE_A.sigma) * scale
    half = STANDARD_NORMAL_97_5 * sigma
    return {
        "predicted_value": value,
        "uncertainty_95_lower": value - half,
        "uncertainty_95_upper": value + half,
        "sigma": sigma,
        "rise_value_A": float(CTPR_RISE_A.value),
        "rise_sigma_A": float(CTPR_RISE_A.sigma),
        "repeat_factor": repeat_factor,
        "uncertainty_method": _RISE_METHOD,
        "confidence_tier": "hypothesis_only",
        "calibrated": False,
        "depends_on_n_repeats": True,
        "human_review_required": True,
        "units": "nm" if to_nm else "Å",
    }


def _length_entry(prediction: LengthPrediction) -> dict[str, Any] | None:
    """Copy a length-curve point. Return None when the fit has no band."""
    if (
        prediction.value is None
        or prediction.band_95_low is None
        or prediction.band_95_high is None
    ):
        return None
    return {
        "predicted_value": float(prediction.value),
        "uncertainty_95_lower": float(prediction.band_95_low),
        "uncertainty_95_upper": float(prediction.band_95_high),
        "sigma": None if prediction.sigma is None else float(prediction.sigma),
        "uncertainty_method": _LENGTH_METHOD,
        "band_label": prediction.band_label,
        "confidence_tier": prediction.confidence_tier,
        "calibrated": False,
        "depends_on_n_repeats": True,
        "human_review_required": True,
        "units": prediction.units,
        "form": prediction.form,
        "past_longest_cited_length": prediction.past_longest_cited_length,
        "length_note": prediction.length_note,
        "model_name": prediction.model_name,
        "model_version": prediction.model_version,
    }


def luminescence_predictions(
    calcium_uM: Sequence[float] = DEFAULT_CALCIUM_UM,
    *,
    e_t: float = DEFAULT_E_T_M,
    m_t: float = DEFAULT_M_T_M,
    t_end: float = DEFAULT_T_END_S,
) -> dict[str, dict[str, Any]]:
    """Endpoint luminescence on a calcium grid.

    The function called here does not take ``n_repeats``. Every entry
    is marked ``depends_on_n_repeats`` false, and the interval is
    ``predicted_value`` times 0.7 and 1.3.
    """
    grid = _require_calcium_uM(calcium_uM)
    values = predict_luminescence(
        np.asarray([item * 1e-6 for item in grid], dtype=float),
        params=CLASPParameters(),
        E_T=e_t,
        M_T=m_t,
        t_end=t_end,
    )
    predictions: dict[str, dict[str, Any]] = {}
    for concentration, raw in zip(grid, values, strict=True):
        value = float(raw)
        predictions[f"ca_{concentration:g}uM"] = {
            "predicted_value": value,
            "uncertainty_95_lower": value * 0.7,
            "uncertainty_95_upper": value * 1.3,
            "uncertainty_method": _LUMINESCENCE_METHOD,
            "confidence_tier": "hypothesis_only",
            "calibrated": False,
            "depends_on_n_repeats": False,
            "human_review_required": True,
            "units": "RLU",
        }
    return predictions


def build_scaffold_freeze_parts(
    n_repeats: int,
    *,
    calcium_uM: Sequence[float] = DEFAULT_CALCIUM_UM,
    e_t: float = DEFAULT_E_T_M,
    m_t: float = DEFAULT_M_T_M,
    t_end: float = DEFAULT_T_END_S,
    luminescence: dict[str, dict[str, Any]] | None = None,
) -> tuple[dict[str, Any], dict[str, dict[str, Any]], list[str], list[str]]:
    """Assemble design spec, predictions, sources, and assumptions.

    ``luminescence`` may be passed in when several lengths share one
    calcium curve. The curve is still stored on this length's file.
    """
    n_repeats = _require_repeat_count(n_repeats)
    grid = _require_calcium_uM(calcium_uM)
    report = structural_report(build_ctpr(n_repeats))
    contour = _rise_interval(n_repeats, to_nm=True)
    axial = _rise_interval(n_repeats - 1, to_nm=False)
    if not np.isclose(report.contour_nm, contour["predicted_value"], rtol=0.0, atol=1e-9):
        raise RuntimeError("contour_nm does not match n_repeats * deposited rise")
    if not np.isclose(report.axial_span_A, axial["predicted_value"], rtol=0.0, atol=1e-6):
        raise RuntimeError("axial_span_A does not match (n_repeats - 1) * deposited rise")

    tm_fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    dg_fit = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    tm_entry = _length_entry(tm_fit.predict(n_repeats))
    dg_entry = _length_entry(dg_fit.predict(n_repeats))
    lookup = thermo_prefill(PHILLIPS_2012_CTPRA_DSC, n_repeats)
    if luminescence is None:
        luminescence = luminescence_predictions(
            grid, e_t=e_t, m_t=m_t, t_end=t_end
        )

    predictions: dict[str, dict[str, Any]] = {
        "contour_nm": contour,
        "axial_span_A": axial,
    }
    missing_bands: list[str] = []
    if tm_entry is None:
        missing_bands.append("phillips_tm_length_curve")
    else:
        predictions["phillips_tm_length_curve"] = tm_entry
    if dg_entry is None:
        missing_bands.append("phillips_delta_g_length_curve")
    else:
        predictions["phillips_delta_g_length_curve"] = dg_entry
    predictions.update(luminescence)

    citation = lookup.get("citation")
    if citation:
        phillips_source = (
            f"Length curve and cited-row lookup use series {PHILLIPS_2012_CTPRA_DSC}. "
            f"thermo_prefill citation: {citation}."
        )
    else:
        phillips_source = (
            f"Length curve uses series {PHILLIPS_2012_CTPRA_DSC}. "
            "thermo_prefill returned no citation string."
        )

    design_spec: dict[str, Any] = {
        "n_repeats": n_repeats,
        "calibrated": False,
        "planned_series_member": n_repeats in PLANNED_REPEAT_COUNTS,
        "planned_repeat_counts": list(PLANNED_REPEAT_COUNTS),
        "component_versions": {
            "scaffold_freeze": SCAFFOLD_FREEZE_VERSION,
            "length_curve": f"{MODEL_NAME}/{MODEL_VERSION}",
            "luminescence": _LUMINESCENCE_MODEL,
        },
        "recorded_without_interval": {
            "wlc_end_to_end_rms_nm": float(report.wlc_end_to_end_rms_nm),
            "rigid_screw": bool(report.rigid_screw),
            "persistence_length_nm": float(report.persistence_length_nm),
            "pitch_A": float(report.pitch_A),
            "scaffold_radius_A": float(report.scaffold_radius_A),
            "rise_A": float(report.rise_A),
            "twist_rad": float(report.twist_rad),
        },
        "stability_series": PHILLIPS_2012_CTPRA_DSC,
        "tm_length_fit": fit_public_dict(tm_fit),
        "delta_g_length_fit": fit_public_dict(dg_fit),
        "literature_lookup": lookup,
        "luminescence": {
            "function": "predict_luminescence",
            "depends_on_n_repeats": False,
            "E_T_M": e_t,
            "M_T_M": m_t,
            "t_end_s": t_end,
            "calcium_uM": grid,
            "uncertainty_method": _LUMINESCENCE_METHOD,
        },
    }
    assumptions = [
        (
            "Contour length is n_repeats times the deposited rise. "
            "Axial span is (n_repeats - 1) times that rise. "
            "The 95% band is the value plus or minus 1.96 times the repeat "
            "factor times the deposited rise sample standard deviation. "
            "That sigma is the sample standard deviation of the deposited "
            "screw steps, not a wet-lab confidence interval."
        ),
        (
            "phillips_tm_length_curve and phillips_delta_g_length_curve are "
            "origami.stability.length_fit evaluated at this n on series "
            f"{PHILLIPS_2012_CTPRA_DSC}. They are not a copied table cell. "
            "The band is the fit's linearized covariance, labelled "
            "linear approximation. calibrated is false."
        ),
        (
            "phillips_delta_g_length_curve is the fit to the printed Phillips "
            "DSC column. It is not the Gibbs–Helmholtz calculator output. "
            "This file does not reconcile those two numbers."
        ),
        (
            "predict_luminescence does not take n_repeats. The calcium curve "
            "in this file is the same for every scaffold length. Its interval "
            "is predicted_value multiplied by 0.7 and 1.3. The method is "
            "fixed_relative_placeholder_pm_30_percent. It is not a propagated "
            "95% interval. confidence_tier is hypothesis_only."
        ),
        (
            "WLC end-to-end RMS, pitch, and the rigid-screw flag are recorded "
            "on the design spec without a propagated interval."
        ),
        "This freeze is not a wet-lab calibration. A passing checksum is not validation.",
    ]
    if missing_bands:
        assumptions.append(
            "No point value was frozen for: "
            + ", ".join(missing_bands)
            + ". The length fit did not return a finite band, and none was invented."
        )
    sources = [CTPR_RISE_A.source, phillips_source, _K_LOCK_SOURCE]
    return design_spec, predictions, sources, assumptions


def write_scaffold_freeze(
    n_repeats: int,
    prediction_id: str,
    *,
    output_dir: Path | None = None,
    overwrite: bool = False,
    calcium_uM: Sequence[float] = DEFAULT_CALCIUM_UM,
    e_t: float = DEFAULT_E_T_M,
    m_t: float = DEFAULT_M_T_M,
    t_end: float = DEFAULT_T_END_S,
    luminescence: dict[str, dict[str, Any]] | None = None,
) -> Path:
    """Write one checksummed scaffold freeze. Refuses to overwrite."""
    design_spec, predictions, sources, assumptions = build_scaffold_freeze_parts(
        n_repeats,
        calcium_uM=calcium_uM,
        e_t=e_t,
        m_t=m_t,
        t_end=t_end,
        luminescence=luminescence,
    )
    return freeze_prediction(
        prediction_id,
        design_spec,
        predictions,
        model_version=SCAFFOLD_FREEZE_VERSION,
        dataset_version="literature_only_v1",
        parameter_sources=sources,
        assumptions=assumptions,
        output_dir=output_dir,
        overwrite=overwrite,
    )


def write_planned_scaffold_freezes(
    *,
    output_dir: Path | None = None,
    overwrite: bool = False,
    calcium_uM: Sequence[float] = DEFAULT_CALCIUM_UM,
    e_t: float = DEFAULT_E_T_M,
    m_t: float = DEFAULT_M_T_M,
    t_end: float = DEFAULT_T_END_S,
) -> list[Path]:
    """Write scaffold-n3, scaffold-n8, and scaffold-n14.

    The calcium curve is computed once and copied onto each file.
    """
    shared = luminescence_predictions(
        calcium_uM, e_t=e_t, m_t=m_t, t_end=t_end
    )
    paths: list[Path] = []
    for n_repeats in PLANNED_REPEAT_COUNTS:
        paths.append(
            write_scaffold_freeze(
                n_repeats,
                f"scaffold-n{n_repeats}",
                output_dir=output_dir,
                overwrite=overwrite,
                calcium_uM=calcium_uM,
                e_t=e_t,
                m_t=m_t,
                t_end=t_end,
                luminescence=shared,
            )
        )
    return paths
