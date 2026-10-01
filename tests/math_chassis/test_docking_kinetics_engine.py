"""Docking effective concentration drives sourced kinetic scalars.

Synthetic radii are caller inputs. They are not measured payload radii.
A passing test is not scientific validation.
"""

from __future__ import annotations

import pytest

from origami.docking.evaluate import evaluate_docking
from origami.docking.local_kinetics import local_kinetics
from origami.kinetics.nanobit import equilibrium_complex_M
from origami.kinetics.simulate import KineticsSimError, simulate_kinetics
from origami.priors import NANOBIT_KD_M, SPY_K_ON_PER_M_S


def test_chord_without_radii_does_not_invent_local_kinetics():
    docking = evaluate_docking(8)
    assert docking["clash_computable"] is False
    assert "c_eff_M" not in docking
    assert docking["local_kinetics"]["computable"] is False
    assert docking["local_kinetics"]["spy_k_rev_per_s"] is None
    assert docking["local_kinetics"]["spy_k_bond_per_s"] is None


def test_tethered_spy_rate_is_kon_times_ceff():
    docking = evaluate_docking(8, radii_A=[20.0, 22.0])
    local = docking["local_kinetics"]
    assert local["computable"] is True
    assert local["calibrated"] is False
    spy = local["spy"]
    assert spy["k_on_origin"] == "literature_prior"
    assert spy["k_on_per_M_s"] == pytest.approx(SPY_K_ON_PER_M_S.value)
    assert spy["k_obs_per_s"] == pytest.approx(
        SPY_K_ON_PER_M_S.value * docking["c_eff_M"]
    )
    assert local["spy_k_rev_per_s"] is None
    assert local["spy_k_bond_per_s"] is None
    assert "10 μM" in spy["note"] or "10" in spy["note"]


def test_nanobit_occupancy_uses_the_printed_kd():
    kd = float(NANOBIT_KD_M.value)
    report = local_kinetics(kd, None)
    assert report["nanobit"]["theta_ss"] == pytest.approx(0.5)
    assert report["nanobit"]["kinetic_kd_M"] == pytest.approx(0.2 / 500.0)
    assert report["nanobit"]["kinetic_kd_M"] != pytest.approx(kd)
    assert report["nanobit"]["printed_kd_sigma_M"] is None


def test_half_life_is_omitted_when_the_rate_band_reaches_zero():
    report = local_kinetics(1e-6, 1e-6, spy_k_on_per_M_s=1.0, spy_k_on_sigma=10.0)
    assert report["spy"]["t_half_s"] is None
    assert "reaches zero" in report["spy"]["t_half_note"]


def test_nanobit_ode_equilibrates_at_koff_over_kon():
    lg0 = 1e-6
    sm0 = 2e-6
    out = simulate_kinetics(
        {
            "mode": "nanobit_complementation",
            "lg0_M": lg0,
            "sm0_M": sm0,
            "num_points": 50,
        }
    )
    kinetic = 0.2 / 500.0
    assert out["calibrated"] is False
    assert out["rates_used"]["kinetic_kd_M"] == pytest.approx(kinetic)
    assert out["rates_used"]["printed_kd_M"] == pytest.approx(NANOBIT_KD_M.value)
    assert out["equilibrium_uses"] == "k_off / k_on"
    expected = equilibrium_complex_M(lg0, sm0, kinetic)
    assert out["equilibrium_complex_M"] == pytest.approx(expected)
    final = out["series"]["complex_M"][-1]
    assert final == pytest.approx(expected, rel=1e-3, abs=1e-12)
    assert out["series"]["lg_M"][-1] + final == pytest.approx(lg0, rel=1e-4)
    assert out["series"]["sm_M"][-1] + final == pytest.approx(sm0, rel=1e-4)
    assert any("not substituted" in warning for warning in out["warnings"])


def test_nanobit_requires_both_starting_concentrations():
    with pytest.raises(KineticsSimError, match="lg0_M"):
        simulate_kinetics({"mode": "nanobit_complementation"})
