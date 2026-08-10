"""
SCALE Stage A dose–response metrics (CLASP Docs § SCALE / Dry Lab Megadoc §2.1).

Fits the phenomenological Hill model used for wet-lab Ca²⁺ curves:

    R(C) = R₀ + R_amp · Cⁿ / (EC50ⁿ + Cⁿ)

and reports EC50, Hill n, dynamic range, with approximate 95% intervals from
the fit covariance (not a substitute for inter-day experimental CIs).

AES conversion requires explicit NanoLuc and OD calibration factors —
never invent those constants here.
"""

from __future__ import annotations

import warnings
from typing import Any, Optional

import numpy as np
from pydantic import BaseModel, Field
from scipy.optimize import curve_fit


class HillFitResult(BaseModel):
    """Phenomenological Hill summary of a Ca²⁺ dose–response curve."""

    r0: float
    r_amp: float
    ec50_M: float
    hill_n: float
    r0_ci95: tuple[float, float]
    r_amp_ci95: tuple[float, float]
    ec50_M_ci95: tuple[float, float]
    hill_n_ci95: tuple[float, float]
    dynamic_range: float
    dynamic_range_ci95: tuple[float, float] | None = None
    rmse: float
    success: bool
    confidence_tier: str = "hypothesis_only"
    is_extrapolation: bool = False
    notes: list[str] = Field(default_factory=list)
    human_review_required: bool = True


class AESResult(BaseModel):
    """Absolute assembled NanoLuc estimate (molecules per cell or per OD)."""

    aes_molecules_per_cell: float | None = None
    aes_molecules_per_od: float | None = None
    rlu_net: float
    fmol_nanoluc: float | None = None
    units: str = "molecules_per_cell"
    uncertainty_95_lower: float | None = None
    uncertainty_95_upper: float | None = None
    confidence_tier: str = "hypothesis_only"
    is_extrapolation: bool = True
    calibration_sources: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    warnings: list[str] = Field(default_factory=list)


def hill_response(
    calcium_M: np.ndarray,
    r0: float,
    r_amp: float,
    ec50_M: float,
    hill_n: float,
) -> np.ndarray:
    """Evaluate R(C) = R0 + R_amp * C^n / (EC50^n + C^n)."""
    ca = np.asarray(calcium_M, dtype=float)
    ca = np.maximum(ca, 0.0)
    n = float(hill_n)
    k = float(ec50_M)
    if k <= 0 or n <= 0:
        return np.full_like(ca, float(r0), dtype=float)
    return float(r0) + float(r_amp) * (ca**n) / (k**n + ca**n)


def _ci95(value: float, stderr: float) -> tuple[float, float]:
    if not np.isfinite(stderr) or stderr < 0:
        return (float("nan"), float("nan"))
    half = 1.96 * float(stderr)
    return (float(value - half), float(value + half))


def fit_hill_dose_response(
    calcium_M: np.ndarray,
    response: np.ndarray,
    *,
    confidence_tier: str = "hypothesis_only",
) -> HillFitResult:
    """
    Fit Hill parameters to a Ca²⁺ / response series.

    Uncertainty intervals are from the local covariance of the least-squares
    fit (approximate). They are not wet-lab replicate 95% CIs unless the
    caller supplies replicate-averaged points with known SEM as weights later.
    """
    ca = np.asarray(calcium_M, dtype=float).ravel()
    y = np.asarray(response, dtype=float).ravel()
    notes = [
        "Phenomenological Hill fit (SCALE Stage A). "
        "CI from fit covariance, not inter-day experimental CI.",
    ]
    if ca.size < 4 or y.size != ca.size:
        return HillFitResult(
            r0=float(np.min(y)) if y.size else 0.0,
            r_amp=0.0,
            ec50_M=float("nan"),
            hill_n=float("nan"),
            r0_ci95=(float("nan"), float("nan")),
            r_amp_ci95=(float("nan"), float("nan")),
            ec50_M_ci95=(float("nan"), float("nan")),
            hill_n_ci95=(float("nan"), float("nan")),
            dynamic_range=0.0,
            rmse=float("nan"),
            success=False,
            confidence_tier=confidence_tier,
            notes=notes + ["Need ≥4 matched points to fit Hill parameters."],
        )

    order = np.argsort(ca)
    ca = ca[order]
    y = y[order]
    y_min = float(np.min(y))
    y_max = float(np.max(y))
    span = max(y_max - y_min, 1e-12)
    # Initial guesses from the curve shape
    p0 = (
        y_min,
        span,
        float(np.median(ca)),
        2.0,
    )
    lower = (0.0, 0.0, float(ca[0]) * 0.1, 0.3)
    upper = (y_max * 1.5 + 1.0, span * 5.0 + 1.0, float(ca[-1]) * 10.0, 12.0)

    try:
        popt, pcov = curve_fit(
            hill_response,
            ca,
            y,
            p0=p0,
            bounds=(lower, upper),
            maxfev=20000,
        )
        r0, r_amp, ec50, n_h = (float(x) for x in popt)
        perr = np.sqrt(np.maximum(np.diag(pcov), 0.0))
        y_hat = hill_response(ca, r0, r_amp, ec50, n_h)
        rmse = float(np.sqrt(np.mean((y_hat - y) ** 2)))
        dr = (r_amp / r0) if r0 > 0 else float("inf")
        # Propagate DR ≈ r_amp/r0 roughly via delta method
        if r0 > 0 and np.isfinite(perr[0]) and np.isfinite(perr[1]):
            dr_var = (perr[1] / r0) ** 2 + (r_amp * perr[0] / r0**2) ** 2
            dr_ci = _ci95(dr, float(np.sqrt(dr_var)))
        else:
            dr_ci = None
        return HillFitResult(
            r0=r0,
            r_amp=r_amp,
            ec50_M=ec50,
            hill_n=n_h,
            r0_ci95=_ci95(r0, float(perr[0])),
            r_amp_ci95=_ci95(r_amp, float(perr[1])),
            ec50_M_ci95=_ci95(ec50, float(perr[2])),
            hill_n_ci95=_ci95(n_h, float(perr[3])),
            dynamic_range=float(dr),
            dynamic_range_ci95=dr_ci,
            rmse=rmse,
            success=True,
            confidence_tier=confidence_tier,
            notes=notes,
            human_review_required=True,
        )
    except Exception as exc:  # noqa: BLE001 — surface fit failure honestly
        return HillFitResult(
            r0=y_min,
            r_amp=span,
            ec50_M=float("nan"),
            hill_n=float("nan"),
            r0_ci95=(float("nan"), float("nan")),
            r_amp_ci95=(float("nan"), float("nan")),
            ec50_M_ci95=(float("nan"), float("nan")),
            hill_n_ci95=(float("nan"), float("nan")),
            dynamic_range=0.0,
            rmse=float("nan"),
            success=False,
            confidence_tier=confidence_tier,
            notes=notes + [f"Hill fit failed: {exc}"],
        )


AVOGADRO = 6.02214076e23  # exact SI definition (molecules/mol)


def compute_aes(
    rlu: float,
    rlu_blank: float,
    *,
    rlu_per_fmol: Optional[float] = None,
    cells_per_ml: Optional[float] = None,
    od600: Optional[float] = None,
    cells_per_od_ml: Optional[float] = None,
    sample_volume_ml: float = 1.0,
    calibration_sources: Optional[list[str]] = None,
) -> AESResult:
    """
    Convert net RLU to absolute assembled NanoLuc (AES).

    Required for molecules/cell:
      - rlu_per_fmol (from NanoLuc standard curve slope)
      - cells_per_ml OR (od600 AND cells_per_od_ml)

    Missing calibration → AES is None and a warning is raised (AGENTS.md §4.2).
    Do not invent NanoLuc or OD conversion factors.
    """
    notes: list[str] = []
    warn: list[str] = []
    sources = list(calibration_sources or [])
    rlu_net = float(rlu) - float(rlu_blank)

    if rlu_per_fmol is None or rlu_per_fmol <= 0:
        msg = (
            "Biological parameter 'rlu_per_fmol' (NanoLuc standard-curve slope) "
            "has no verified source. AES cannot be computed until a measured "
            "calibration factor is supplied."
        )
        warnings.warn(msg, UserWarning, stacklevel=2)
        warn.append(msg)
        return AESResult(
            rlu_net=rlu_net,
            notes=notes,
            warnings=warn,
            calibration_sources=sources,
        )

    fmol = rlu_net / float(rlu_per_fmol)
    molecules = fmol * 1e-15 * AVOGADRO  # fmol → mol → molecules

    cells: float | None = None
    if cells_per_ml is not None and cells_per_ml > 0:
        cells = float(cells_per_ml) * float(sample_volume_ml)
        notes.append("Cell count from cells_per_ml × sample_volume_ml.")
    elif (
        od600 is not None
        and cells_per_od_ml is not None
        and od600 > 0
        and cells_per_od_ml > 0
    ):
        cells = float(od600) * float(cells_per_od_ml) * float(sample_volume_ml)
        notes.append("Cell count from OD600 × cells_per_OD·mL × volume.")
    else:
        msg = (
            "AES molecules/cell requires cells_per_ml or "
            "(od600 and cells_per_od_ml). Returning fmol only."
        )
        warnings.warn(msg, UserWarning, stacklevel=2)
        warn.append(msg)
        aes_per_od = None
        if od600 is not None and od600 > 0:
            # molecules per OD unit in the assay volume (still needs OD→cells for per-cell)
            aes_per_od = molecules / (float(od600) * float(sample_volume_ml))
        return AESResult(
            aes_molecules_per_od=aes_per_od,
            rlu_net=rlu_net,
            fmol_nanoluc=float(fmol),
            units="fmol_NanoLuc",
            notes=notes,
            warnings=warn,
            calibration_sources=sources,
        )

    aes = molecules / cells if cells > 0 else None
    return AESResult(
        aes_molecules_per_cell=float(aes) if aes is not None else None,
        rlu_net=rlu_net,
        fmol_nanoluc=float(fmol),
        units="molecules_per_cell",
        notes=notes
        + [
            "AES uses caller-supplied calibration only; not a Tier-1 claim "
            "until those factors are experimentally measured."
        ],
        warnings=warn,
        calibration_sources=sources,
        human_review_required=True,
    )


def hill_fit_to_dict(fit: HillFitResult) -> dict[str, Any]:
    """JSON-friendly dump for Design Mode / passport."""
    return fit.model_dump()
