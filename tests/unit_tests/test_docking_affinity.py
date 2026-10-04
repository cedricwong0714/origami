"""Affinity check: a typed Kd is compared with C_eff, then with payloads."""

import math

import pytest

from origami.docking.affinity import evaluate_affinity
from origami.docking.evaluate import evaluate_docking
from origami.physical.payload_radii import payload_radius


def test_bound_fraction_is_langmuir_at_local_concentration() -> None:
    """theta = C_eff / (C_eff + Kd). Holds when Kd is at or below C_eff.

    Scientific basis: Langmuir isotherm. The midpoint is the definition
    of Kd, not a fitted cutoff.
    Failure mode: a verdict that ignores the local concentration.
    """
    report = evaluate_affinity(8, affinity="kd", value=0.19, unit="nM")
    c_eff = report["c_eff_M"]
    kd = report["kd_M"]
    assert report["calibrated"] is False
    assert report["association_theta"] == c_eff / (c_eff + kd)
    assert report["association_holds"] is (kd <= c_eff)
    assert report["kd_M"] == pytest.approx(0.19e-9)


def test_association_constant_is_the_inverse_of_kd() -> None:
    kd_report = evaluate_affinity(8, affinity="kd", value=1.0, unit="uM")
    ka_per_M = 1.0 / kd_report["kd_M"]
    ka_report = evaluate_affinity(8, affinity="ka", value=ka_per_M, unit="M")
    assert ka_report["kd_M"] == kd_report["kd_M"]
    assert ka_report["association_holds"] is kd_report["association_holds"]


def test_payloads_are_not_driven_when_the_association_does_not_hold() -> None:
    loose = evaluate_affinity(8, affinity="kd", value=1.0, unit="M")
    assert loose["association_holds"] is False
    assert loose["drives_lgbit_smbit"] is False
    assert loose["drives_spycatcher_spytag"] is False


def test_default_radii_match_deposited_spycatcher_and_lgbit() -> None:
    report = evaluate_affinity(8, affinity="kd", value=1.0, unit="nM")
    expected = [
        payload_radius("spycatcher").clash_radius_A,
        payload_radius("lgbit").clash_radius_A,
    ]
    docking = evaluate_docking(8, radii_A=expected)
    assert report["radii_A"] == expected
    assert report["c_eff_M"] == docking["c_eff_M"]
    assert report["radius_origin"] == "deposited_clash_radii"


def test_spy_half_life_is_ln2_over_k_obs() -> None:
    """t_half = ln(2) / k_obs even when the 95% band on k_obs reaches zero.

    Scientific basis: first-order half-life. The omitted interval is not a missing rate.
    Failure mode: a finite k_obs shown as "not computed".
    """
    report = evaluate_affinity(8, affinity="kd", value=0.19, unit="nM")
    k_obs = report["spy_k_obs_per_s"]
    assert k_obs is not None and k_obs > 0
    assert report["spy_half_life_s"] == pytest.approx(math.log(2.0) / k_obs)
