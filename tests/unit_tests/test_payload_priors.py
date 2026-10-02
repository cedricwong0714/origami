"""Tests for payload radii priors and Erickson 2009 hydrodynamic scaling."""

from __future__ import annotations

import math
import pytest

from origami.priors import (
    DEFAULT_PAYLOAD_RADIUS_A,
    OTSA_K_CAT_PER_S,
    OTSB_K_CAT_PER_S,
    PAYLOAD_LIBRARY,
    erickson_rh_A,
    erickson_rmin_A,
    get_payload_parameter,
    payload_parameter_from_mw,
)


def test_erickson_scaling_formula():
    # For a 50 kDa protein (50,000 Da):
    # R_min = 0.66 * (50000)^(1/3) ≈ 24.31 Å
    # R_H = 0.78 * (50000)^(1/3) ≈ 28.73 Å
    r_min_50k = erickson_rmin_A(50000.0)
    r_h_50k = erickson_rh_A(50000.0)
    assert r_min_50k == pytest.approx(24.31, rel=1e-2)
    assert r_h_50k == pytest.approx(28.73, rel=1e-2)
    assert r_h_50k > r_min_50k

    with pytest.raises(ValueError):
        erickson_rmin_A(0.0)
    with pytest.raises(ValueError):
        erickson_rh_A(-100.0)


def test_payload_library_entries():
    assert "spycatcher" in PAYLOAD_LIBRARY
    assert "lgbit" in PAYLOAD_LIBRARY
    assert "otsa" in PAYLOAD_LIBRARY
    assert "otsb" in PAYLOAD_LIBRARY

    for key, param in PAYLOAD_LIBRARY.items():
        assert param.calibrated is False
        assert param.units == "Å"
        assert param.value > 0.0
        assert param.sigma is not None and param.sigma > 0.0
        assert len(param.source) > 10
        assert len(param.system) > 5


def test_get_payload_parameter_lookup():
    sc = get_payload_parameter("SpyCatcher")
    assert sc.value == 18.5
    assert sc.name == "payload_radius_spycatcher"

    lg = get_payload_parameter("lgbit")
    assert lg.value == 20.0

    otsa = get_payload_parameter("OtsA")
    assert otsa.value == 26.0

    otsb = get_payload_parameter("ots_b")
    assert otsb.value == 22.0

    with pytest.raises(KeyError):
        get_payload_parameter("nonexistent_payload")


def test_payload_parameter_from_mw():
    param = payload_parameter_from_mw("GFP", 27000.0)
    assert param.units == "Å"
    assert param.calibrated is False
    assert param.value == pytest.approx(erickson_rh_A(27000.0))
    assert param.sigma is not None and param.sigma > 0.0


def test_enzyme_kinetic_priors():
    assert OTSA_K_CAT_PER_S.value == 50.0
    assert OTSA_K_CAT_PER_S.units == "s^-1"
    assert OTSA_K_CAT_PER_S.calibrated is False

    assert OTSB_K_CAT_PER_S.value == 120.0
    assert OTSB_K_CAT_PER_S.units == "s^-1"
    assert OTSB_K_CAT_PER_S.calibrated is False
