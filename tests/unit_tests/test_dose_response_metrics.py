"""SCALE Stage A: Hill dose-response fit and AES conversion."""

from __future__ import annotations

import warnings

import numpy as np
import pytest

from src.calibration.dose_response_metrics import (
    AVOGADRO,
    compute_aes,
    fit_hill_dose_response,
    hill_response,
)


def test_hill_fit_recovers_synthetic_parameters():
    """
    Scientific basis: SCALE Stage A fits R = R0 + R_amp C^n/(EC50^n+C^n).
    Failure mode: biased EC50/n would corrupt M1 reporting.
    """
    ca = np.logspace(-7, -4, 25)
    true = dict(r0=100.0, r_amp=900.0, ec50_M=2e-6, hill_n=4.0)
    y = hill_response(ca, **true)
    fit = fit_hill_dose_response(ca, y)
    assert fit.success
    assert abs(fit.ec50_M - true["ec50_M"]) / true["ec50_M"] < 0.05
    assert abs(fit.hill_n - true["hill_n"]) < 0.25
    assert fit.ec50_M_ci95[0] <= fit.ec50_M <= fit.ec50_M_ci95[1]
    assert fit.dynamic_range == pytest.approx(true["r_amp"] / true["r0"], rel=0.05)


def test_hill_fit_rejects_too_few_points():
    fit = fit_hill_dose_response(np.array([1e-6, 1e-5]), np.array([1.0, 2.0]))
    assert fit.success is False


def test_aes_requires_calibration_factors():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        aes = compute_aes(1000.0, 100.0)
    assert aes.aes_molecules_per_cell is None
    assert any("rlu_per_fmol" in str(x.message) for x in w)


def test_aes_molecules_per_cell_with_explicit_calibration():
    """
    AES = ((RLU-blank)/slope)_fmol * 1e-15 * N_A / cells.
    Uses caller-supplied factors only — no invented biology constants.
    """
    rlu_per_fmol = 1e5
    cells_per_ml = 1e9
    aes = compute_aes(
        1.1e5,
        1e4,
        rlu_per_fmol=rlu_per_fmol,
        cells_per_ml=cells_per_ml,
        sample_volume_ml=1.0,
        calibration_sources=["unit_test_fixture"],
    )
    # net RLU = 1e5 → 1 fmol → 1e-15 mol → N_A molecules / 1e9 cells
    expected = (1.0 * 1e-15 * AVOGADRO) / 1e9
    assert aes.aes_molecules_per_cell == pytest.approx(expected, rel=1e-9)
    assert aes.fmol_nanoluc == pytest.approx(1.0)
