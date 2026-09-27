"""Scientific invariants for Stream 1 CLASP assembly ODE and geometry."""

from __future__ import annotations

import numpy as np
import pytest

from src.core.clasp_assembly import (
    CLASPParameters,
    cam_activation_fraction,
    predict_luminescence,
    simulate_assembly,
)
from src.core.ctpr_geometry import (
    PERSISTENCE_LENGTH_NM,
    generate_scaffold_geometry,
    wlc_mean_square_end_to_end,
)
from src.core.schema import MechanismType, ScaffoldSpec
from src.ode_model.solver import run_system_simulation


def test_clasp_assembly_non_negative_and_bounded():
    """
    Scientific basis: concentrations B, L ≥ 0 and B+L ≤ min(E_T, M_T).
    Failure mode: mass leak or negative populations indicate ODE bug.
    """
    E_T = M_T = 1e-6
    t, concs = simulate_assembly(calcium_M=1e-5, E_T=E_T, M_T=M_T, t_end=600.0, num_points=80)
    assert np.all(concs["B"] >= -1e-15)
    assert np.all(concs["L"] >= -1e-15)
    inventory = concs["B"] + concs["L"]
    assert np.all(inventory <= min(E_T, M_T) + 1e-12)


def test_clasp_locked_inventory_nondecreasing_under_pure_lock():
    """
    When k_off ≈ 0 and calcium saturating, locking should transfer B→L
    without decreasing total assembled inventory after initial rise.
    """
    params = CLASPParameters(k_off=1e-6, k_lock=0.01)
    t, concs = simulate_assembly(
        calcium_M=1e-4, params=params, E_T=1e-6, M_T=1e-6, t_end=1200.0, num_points=100
    )
    inventory = concs["B"] + concs["L"]
    # After initial transient (first 10%), inventory should be non-decreasing
    late = inventory[len(inventory) // 10 :]
    assert np.all(np.diff(late) >= -1e-14)


def test_cam_activation_monotonic_and_bounds():
    params = CLASPParameters()
    ca = np.logspace(-9, -4, 20)
    f = [cam_activation_fraction(float(c), params) for c in ca]
    assert f[0] < 0.05
    assert f[-1] > 0.95
    assert all(0.0 <= x <= 1.0 for x in f)
    assert all(f[i] <= f[i + 1] + 1e-12 for i in range(len(f) - 1))


def test_luminescence_dose_response_increases_with_calcium():
    ca = np.array([1e-8, 1e-7, 1e-6, 1e-5, 1e-4])
    R = predict_luminescence(ca, t_end=1800.0)
    assert np.all(np.diff(R) >= -1e-6)


def test_apparent_ec50_from_assembly_dose_response():
    """
    Scientific basis: half-maximal Ca²⁺ on the assembly luminescence curve should
    fall near the CaM parameter EC50 (~2 µM) for default literature params.
    Failure mode: EC50 estimator bug or silent parameter drift.
    """
    from src.core.calcium_kinetics import CAM_CA_EC50_M
    from src.core.clasp_assembly import estimate_ec50_from_curve

    ca = np.logspace(-8, -4, 41)
    R = predict_luminescence(ca, t_end=1800.0)
    out = estimate_ec50_from_curve(ca, R)
    assert out["ec50_M"] is not None
    assert out["uncertainty_lower_M"] <= out["ec50_M"] <= out["uncertainty_upper_M"]
    # Apparent EC50 within ~10× of CaM EC50 (assembly kinetics can shift it).
    assert 0.1 * CAM_CA_EC50_M <= out["ec50_M"] <= 10.0 * CAM_CA_EC50_M


def test_intermediate_transfer_mass_conservation():
    """
    Scientific basis: S + I_bulk + I_chan + P is conserved (catalysts fixed).
    Failure mode: mass leak in channeling ODE.
    """
    t, concs = run_system_simulation(
        {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0},
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        num_points=50,
    )
    # Public API maps I_bulk+I_chan → ES; inventory ≈ S + ES + P
    inventory = np.asarray(concs["S"]) + np.asarray(concs["ES"]) + np.asarray(concs["P"])
    assert np.allclose(inventory, inventory[0], atol=1e-5)


def test_geometry_uncertainty_positive_and_grows_with_repeat_index():
    geom = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR8", repeat_count=8, docking_positions=[1, 8])
    )
    assert geom.docking_sites[0].position_uncertainty_norm_nm >= 0.0
    assert (
        geom.docking_sites[-1].position_uncertainty_norm_nm
        >= geom.docking_sites[0].position_uncertainty_norm_nm
    )
    unc = geom.get_inter_site_distance_uncertainty_nm(0, 1)
    assert unc >= 0.0


def test_wlc_warns_when_beyond_persistence_length():
    # 20 repeats * deposited mean rise (~0.842 nm) = ~16.8 nm > 15 nm persistence
    with pytest.warns(UserWarning, match="persistence length"):
        geom = generate_scaffold_geometry(
            ScaffoldSpec(scaffold_id="CTPR20", repeat_count=20, docking_positions=[1, 20])
        )
    assert geom.is_rigid is False
    assert geom.wlc_end_to_end_rms_nm is not None
    assert geom.rigid_rod_warning is not None


def test_wlc_mean_square_limits():
    # Rigid limit L << Lp → ⟨R²⟩ → L²
    L, Lp = 1.0, 100.0
    ms = wlc_mean_square_end_to_end(L, Lp)
    assert abs(ms - L**2) / L**2 < 0.05
    # Flexible limit L >> Lp → ⟨R²⟩ → 2 Lp L
    L2, Lp2 = 100.0, 1.0
    ms2 = wlc_mean_square_end_to_end(L2, Lp2)
    assert abs(ms2 - 2 * Lp2 * L2) / (2 * Lp2 * L2) < 0.05


def test_short_scaffold_still_rigid():
    geom = generate_scaffold_geometry(
        ScaffoldSpec(scaffold_id="CTPR5", repeat_count=5, docking_positions=[1, 3])
    )
    assert geom.total_length_nm <= PERSISTENCE_LENGTH_NM
    assert geom.is_rigid is True
