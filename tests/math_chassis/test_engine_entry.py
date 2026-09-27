"""run_design wires the canonical geometry and does not invent rates.

Numeric rates and concentrations in these tests are caller-supplied fixtures.
They are not measured enzyme constants.
"""

import inspect
from types import SimpleNamespace

import pytest

from origami.engine import Observation, run_design
from origami.physical.steric import steric_report
from origami.priors import CAM_M13_KD_M, DEFAULT_PAYLOAD_RADIUS_A
from src.core.calcium_kinetics import (
    CAM_CA_EC50_M,
    CAM_CA_HILL_N,
    CAM_M13_KD_CA_SAT_M,
    RESTING_CA_M,
)


def test_default_design_uses_canonical_priors_and_lists_missing_rates():
    result = run_design("design-a", 8)
    assert result.design_id == "design-a"
    assert result.prior_geometry_id == "src.core.ctpr_geometry"
    assert result.prior_kd_id == "cam_m13_peptide_0.19nM"
    assert result.n_repeats == 8
    assert result.calibrated is False
    assert result.omitted == ["kon", "k_cat", "K_m", "k_escape", "v_prod"]
    assert isinstance(result.warnings, list)
    assert result.warnings
    assert not any("exceeds persistence" in warning for warning in result.warnings)


def test_default_payloads_are_the_two_end_repeats(monkeypatch):
    seen: list[tuple[list[int], list[float]]] = []
    real = steric_report

    def wrapper(geom, indices, radii, standoff_A=None):
        seen.append((list(indices), list(radii)))
        return real(geom, indices, radii, standoff_A=standoff_A)

    monkeypatch.setattr("origami.engine.steric_report", wrapper)
    run_design("ends", 8)
    assert seen[0][0] == [0, 7]
    radius = DEFAULT_PAYLOAD_RADIUS_A.value
    assert seen[0][1] == [radius, radius]


def test_signal_pair_without_kon_is_steady_state_only(monkeypatch):
    seen: dict[str, object] = {}

    def fake(
        c_free_M,
        kon_per_M_s=None,
        kd_M=None,
        kd_sigma_M=None,
        t_end_s=None,
        signal_on=True,
    ):
        seen["kd_M"] = kd_M
        seen["kon"] = kon_per_M_s
        seen["signal_on"] = signal_on
        from origami.physical.recruitment import OccupancyResult

        return OccupancyResult(
            theta_ss=0.5,
            theta_95_lower=0.5,
            theta_95_upper=0.5,
            kd_M=float(kd_M),
            kd_sigma_M=float(kd_sigma_M or 0.0),
            c_free_M=c_free_M,
            kon_per_M_s=kon_per_M_s,
            time_s=None,
            theta_t=None,
            warnings=["steady state only"],
        )

    monkeypatch.setattr("origami.engine.recruitment_occupancy", fake)
    pair = SimpleNamespace(
        kd_M=3.5e-9,
        kd_source="caller fixture, not a paper",
        kon_per_M_s=None,
    )
    result = run_design("design-b", 6, signal_pair=pair, c_free_M=1e-8)
    assert seen["kd_M"] == 3.5e-9
    assert seen["kon"] is None
    assert seen["signal_on"] is True
    assert "kon" in result.omitted
    assert "k_cat" in result.omitted
    assert result.prior_kd_id == "cam_m13_peptide_0.19nM"
    assert any("caller fixture" in warning for warning in result.warnings)


def test_signal_pair_with_kon_is_not_omitted():
    pair = SimpleNamespace(
        kd_M=2e-9,
        kd_source="caller fixture, not a paper",
        kon_per_M_s=1e6,
    )
    result = run_design("design-c", 6, signal_pair=pair, c_free_M=2e-9)
    assert "kon" not in result.omitted
    assert result.omitted == ["k_cat", "K_m", "k_escape", "v_prod"]
    assert result.calibrated is False


def test_caller_rates_are_passed_to_transfer(monkeypatch):
    seen: dict[str, float] = {}

    def fake(v_prod_M_per_s, k_escape_per_s, kcat_over_km_per_M_s, c_eff_M, t_end_s=None):
        seen["v_prod"] = v_prod_M_per_s
        seen["k_escape"] = k_escape_per_s
        seen["specificity"] = kcat_over_km_per_M_s
        seen["c_eff"] = c_eff_M
        from origami.mechanisms.intermediate_transfer import TransferResult
        import numpy as np

        return TransferResult(
            da=1.0,
            p_capture=0.5,
            intermediate_ss_M=0.0,
            product_flux_M_per_s=0.0,
            k_capture_per_s=1.0,
            k_escape_per_s=k_escape_per_s,
            v_prod_M_per_s=v_prod_M_per_s,
            c_eff_M=c_eff_M,
            time_s=np.array([0.0]),
            intermediate_M=np.array([0.0]),
            product_M=np.array([0.0]),
            warnings=["synthetic fixture"],
        )

    monkeypatch.setattr("origami.engine.simulate_from_ceff", fake)
    result = run_design(
        "design-e",
        8,
        c_free_M=1e-9,
        k_cat_per_s=10.0,
        k_m_M=1e-4,
        k_escape_per_s=2.0,
        v_prod_M_per_s=1e-6,
    )
    assert seen["v_prod"] == 1e-6
    assert seen["k_escape"] == 2.0
    assert seen["specificity"] == pytest.approx(10.0 / 1e-4)
    assert seen["c_eff"] > 0
    assert result.omitted == ["kon"]


def test_payload_repeat_indices_are_used(monkeypatch):
    seen: list[tuple[list[int], list[float]]] = []
    real = steric_report

    def wrapper(geom, indices, radii, standoff_A=None):
        seen.append((list(indices), list(radii)))
        return real(geom, indices, radii, standoff_A=standoff_A)

    monkeypatch.setattr("origami.engine.steric_report", wrapper)
    # Radii and linker widths are fixtures, not measured payload sizes.
    payloads = [
        {
            "payload_id": "alpha",
            "role": "fixture",
            "fusion_terminus": "N",
            "repeat_index": 1,
            "radius_A": 9.0,
            "linker_sigma_A": 10.0,
        },
        {
            "payload_id": "beta",
            "role": "fixture",
            "fusion_terminus": "C",
            "repeat_index": 4,
            "radius_A": 8.0,
            "linker_sigma_A": 11.0,
        },
    ]
    result = run_design("design-d", 8, payloads=payloads, c_free_M=1e-9)
    assert seen[0] == ([1, 4], [9.0, 8.0])
    assert result.n_repeats == 8
    assert result.calibrated is False


def test_missing_payload_radius_is_not_filled_in():
    with pytest.raises(ValueError, match="radius_A"):
        run_design(
            "missing-radius",
            6,
            payloads=[{"payload_id": "alpha", "repeat_index": 0}],
        )


def test_long_scaffold_warns_past_persistence_length():
    # 16 repeats at the deposited mean rise stay under the 15 nm cutoff.
    # 18 repeats cross it: 18 * 0.8416 nm is about 15.15 nm.
    result = run_design("long", 18)
    assert any("exceeds persistence" in warning for warning in result.warnings)
    assert result.calibrated is False


def test_observations_keep_the_design_uncalibrated():
    result = run_design(
        "obs",
        8,
        observations=[Observation(n_repeats=8, y=0.2, source="user_entered")],
    )
    assert result.calibrated is False
    assert result.n_repeats == 8


def test_run_design_is_the_single_report_interface():
    import origami.engine as engine
    from origami.report import DesignReport

    imported = [
        line.strip()
        for line in inspect.getsource(engine).splitlines()
        if line.strip().startswith(("import ", "from "))
    ]
    assert any("origami.io" in line for line in imported)
    assert any("origami.report" in line for line in imported)
    result = run_design("iface", 8)
    assert isinstance(result, DesignReport)
    assert result.to_dict()["calibrated"] is False


def test_calcium_occupancy_constant_matches_peptide_kd():
    assert CAM_M13_KD_CA_SAT_M == CAM_M13_KD_M.value
    assert CAM_M13_KD_CA_SAT_M == 0.19e-9
    assert CAM_CA_HILL_N == 4.0
    assert CAM_CA_EC50_M == 2e-6
    assert RESTING_CA_M == 1e-7
