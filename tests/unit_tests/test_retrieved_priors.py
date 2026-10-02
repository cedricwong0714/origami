"""Values below were read from retrieved papers. A passing test is not validation."""

import pytest

from origami.priors import (
    FUSION_CAM_M13_CA_KD_M, OTSA_KCAT_PER_S, OTSA_RECOMBINANT_MW_DA,
    OTSB_KCAT_PER_S, OTSB_KM_T6P_M, SPY_REVERSAL_OBSERVED,
    assumed_recruitment_kon_per_M_s, derived_recruitment_koff_per_s,
    all_priors, erickson_rmin_A,
)


def test_erickson_matches_table_1_of_the_paper():
    # Erickson 2009 Table 1: 50 kDa -> 2.4 nm, 100 kDa -> 3.05 nm.
    assert erickson_rmin_A(50_000) == pytest.approx(24.0, abs=0.7)
    assert erickson_rmin_A(100_000) == pytest.approx(30.5, abs=0.7)


def test_erickson_rejects_bad_mass():
    for bad in (0.0, -1.0, float("nan")):
        with pytest.raises(ValueError):
            erickson_rmin_A(bad)


def test_otsa_rmin_is_a_lower_bound_near_25_angstrom():
    assert erickson_rmin_A(OTSA_RECOMBINANT_MW_DA) == pytest.approx(25.0, abs=0.3)


def test_fusion_kd_is_secondhand_and_kon_is_an_assumption():
    assert FUSION_CAM_M13_CA_KD_M.value == pytest.approx(80e-9)
    assert FUSION_CAM_M13_CA_KD_M.sigma is None
    assert "10.3389/fnmol.2014.00090" in FUSION_CAM_M13_CA_KD_M.source
    assert FUSION_CAM_M13_CA_KD_M in all_priors()
    assert SPY_REVERSAL_OBSERVED is False
    with pytest.warns(UserWarning, match="unsourced"):
        assert assumed_recruitment_kon_per_M_s() == 1e6
    with pytest.warns(UserWarning):
        assert derived_recruitment_koff_per_s() == pytest.approx(0.08)


def test_enzyme_priors_are_uncalibrated_and_carry_sigma():
    assert OTSA_KCAT_PER_S.value == 34.0 and OTSA_KCAT_PER_S.sigma == 1.0
    assert OTSB_KCAT_PER_S.value == 286.0 and OTSB_KCAT_PER_S.sigma == 34.0
    assert OTSB_KM_T6P_M.value == pytest.approx(3.6e-3)
    for p in (OTSA_KCAT_PER_S, OTSB_KCAT_PER_S, OTSB_KM_T6P_M):
        assert p.calibrated is False and "Khan" in p.source
        assert p in all_priors()
