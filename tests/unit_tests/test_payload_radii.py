"""Radii derived from deposited coordinates. Not hydrodynamic, not validation."""

import math
import pytest

from origami.physical.payload_radii import (
    PayloadRadiusError, available_payloads, otsb_lower_bound_A, payload_radius, radii_for,
)
from origami.priors import erickson_rmin_A
from origami.ssdk.learn import SsdkLearnError, learn_ssdk


def test_radii_are_ordered_like_the_structures():
    # Scientific basis: a solid sphere radius cannot exceed the farthest C-alpha,
    # and extended Ca-CaM must be larger than compact Ca-CaM (Fallon & Quiocho 2003).
    for key in available_payloads():
        r = payload_radius(key)
        assert 0 < r.clash_radius_A <= r.r_max_A and not r.calibrated
    assert payload_radius("calmodulin_extended").clash_radius_A > payload_radius("calmodulin_compact").clash_radius_A


def test_radius_exceeds_erickson_lower_bound_for_otsa():
    # Rmin is a minimum for a smooth sphere of the full mass; the C-alpha sphere
    # of a 452-residue chain should be of the same order and not wildly below.
    lower = erickson_rmin_A(53611.0)
    assert payload_radius("otsa_ecoli").clash_radius_A > 0.9 * lower


def test_lgbit_is_flagged_as_proxy_and_otsb_has_no_radius():
    assert payload_radius("nanoluc_proxy_for_lgbit").is_proxy
    info = otsb_lower_bound_A()
    assert info["usable_as_clash_radius"] is False and math.isfinite(info["r_min_lower_bound_A"])
    with pytest.raises(PayloadRadiusError):
        payload_radius("otsb_ecoli")


def test_radii_for_needs_two_names():
    with pytest.raises(ValueError):
        radii_for(["spycatcher"])


def test_learn_uses_named_payloads_and_rejects_double_input():
    out = learn_ssdk({"payload_names": ["spycatcher", "otsa_ecoli"], "n_min": 3, "n_max": 8})
    assert out["radius_origin"] == "pdb_derived"
    assert out["payload_radii_A"] == radii_for(["spycatcher", "otsa_ecoli"])
    with pytest.raises(SsdkLearnError):
        learn_ssdk({"payload_names": ["spycatcher", "otsa_ecoli"], "payload_radii_A": [10, 10]})
    with pytest.raises(SsdkLearnError):
        learn_ssdk({"payload_names": ["spycatcher", "nope"]})
