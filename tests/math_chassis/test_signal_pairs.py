"""Signal-pair loading and recruitment occupancy.

The default pair uses the published CaM–M13 Kd. Other Kd values in this
file are unit-test fixtures, not literature parameters. kon is not taken
from the 2006 Kd paper.
"""

import pytest

from origami.io.signal_pairs import SignalPair, default_cam_m13_pair, load_signal_pairs
from origami.physical.recruitment import occupancy_for_pair, recruitment_occupancy
from origami.priors import CAM_M13_KD_M

# Fixture dissociation constant. Not a measured Kd and not the CaM–M13 value.
_FIXTURE_KD_M = 2.5e-6
_FIXTURE_SOURCE = "fixture Kd for a unit test; not a literature value"


def _row(**overrides: object) -> dict:
    row: dict = {
        "signal_id": "ligand",
        "binder_id": "binder",
        "partner_id": "partner",
        "kd_M": _FIXTURE_KD_M,
        "kd_source": _FIXTURE_SOURCE,
    }
    row.update(overrides)
    return row


def test_default_pair_uses_published_cam_m13_kd():
    pair = default_cam_m13_pair()

    assert pair.signal_id == "Ca2+"
    assert pair.binder_id == "CaM"
    assert pair.partner_id == "M13"
    assert pair.kd_M == 0.19e-9
    assert pair.kd_M == CAM_M13_KD_M.value
    assert pair.kd_source == CAM_M13_KD_M.source
    assert "10.1021/bi060857u" in pair.kd_source
    assert pair.kd_sigma_M == CAM_M13_KD_M.sigma
    assert pair.kd_sigma_M == 0.09e-9
    assert pair.kon_per_M_s is None


def test_custom_kd_changes_steady_occupancy():
    published = default_cam_m13_pair()
    custom = SignalPair(
        signal_id="ligand",
        binder_id="binder",
        partner_id="partner",
        kd_M=_FIXTURE_KD_M,
        kd_source=_FIXTURE_SOURCE,
    )
    c_free_M = 1e-9

    theta_published = occupancy_for_pair(published, c_free_M).theta_ss
    theta_custom = occupancy_for_pair(custom, c_free_M).theta_ss

    assert theta_custom != theta_published
    assert theta_published == c_free_M / (c_free_M + published.kd_M)
    assert theta_custom == c_free_M / (c_free_M + custom.kd_M)
    assert theta_published > theta_custom


def test_missing_kon_does_not_produce_a_time_series():
    pair = default_cam_m13_pair()
    result = occupancy_for_pair(pair, c_free_M=1e-9)

    direct = recruitment_occupancy(
        c_free_M=1e-9,
        kon_per_M_s=None,
        kd_M=pair.kd_M,
    )
    assert result.kon_per_M_s is None
    assert result.time_s is None
    assert result.theta_t is None
    assert result.theta_ss == direct.theta_ss


def test_missing_kd_source_raises():
    empty = _row(kd_source="")
    with pytest.raises(ValueError, match="kd_source"):
        load_signal_pairs([empty])

    blank = _row(kd_source="   ")
    with pytest.raises(ValueError, match="kd_source"):
        load_signal_pairs([blank])

    omitted = _row()
    del omitted["kd_source"]
    with pytest.raises(ValueError, match="kd_source"):
        load_signal_pairs([omitted])


def test_missing_or_nonpositive_kd_raises_and_is_not_defaulted():
    omitted = _row()
    del omitted["kd_M"]
    with pytest.raises(ValueError, match="kd_M"):
        load_signal_pairs([omitted])

    with pytest.raises(ValueError, match="kd_M"):
        load_signal_pairs([_row(kd_M=None)])

    with pytest.raises(ValueError, match="kd_M"):
        load_signal_pairs([_row(kd_M=0.0)])

    with pytest.raises(ValueError, match="kd_M"):
        load_signal_pairs([_row(kd_M=-1e-9)])


def test_loader_keeps_caller_kd_and_optional_kon():
    loaded = load_signal_pairs([_row()])
    assert loaded == [
        SignalPair(
            signal_id="ligand",
            binder_id="binder",
            partner_id="partner",
            kd_M=_FIXTURE_KD_M,
            kd_source=_FIXTURE_SOURCE,
            kon_per_M_s=None,
        )
    ]
    assert loaded[0].kd_M != 0.19e-9

    # 1e6 /M/s is a caller-supplied fixture, not a rate from the Kd paper.
    with_kon = load_signal_pairs([_row(kon_per_M_s=1e6)])
    assert with_kon[0].kon_per_M_s == 1e6


def test_user_supplied_kon_returns_a_time_series():
    pair = SignalPair(
        signal_id="Ca2+",
        binder_id="CaM",
        partner_id="M13",
        kd_M=CAM_M13_KD_M.value,
        kd_source=CAM_M13_KD_M.source,
        kon_per_M_s=1e6,
    )
    result = occupancy_for_pair(pair, c_free_M=1e-8)
    assert result.time_s is not None
    assert result.theta_t is not None
    assert abs(float(result.theta_t[-1]) - result.theta_ss) < 1e-3


def test_signal_off_is_empty_for_a_pair():
    result = occupancy_for_pair(default_cam_m13_pair(), c_free_M=1e-6, signal_on=False)
    assert result.theta_ss == 0.0
    assert result.time_s is None


def test_custom_pair_does_not_inherit_cam_m13_sigma():
    """A missing sigma is not the 0.09 nM CaM–M13 error bar.

    1e-6 M and 2e-7 M below are fixtures, not literature Kd values.
    """
    c_free_M = 1e-6
    cam_sigma_M = 0.09e-9
    unspecified = SignalPair(
        signal_id="ligand",
        binder_id="binder",
        partner_id="partner",
        kd_M=1e-6,
        kd_source=_FIXTURE_SOURCE,
    )
    assert unspecified.kd_sigma_M is None

    result = occupancy_for_pair(unspecified, c_free_M=c_free_M)
    borrowed = recruitment_occupancy(
        c_free_M=c_free_M,
        kd_M=1e-6,
        kd_sigma_M=cam_sigma_M,
    )
    borrowed_width = borrowed.theta_95_upper - borrowed.theta_95_lower

    assert result.theta_95_lower == result.theta_ss == result.theta_95_upper
    assert result.theta_95_upper - result.theta_95_lower == 0.0
    assert borrowed_width > 0.0
    assert result.theta_95_upper - result.theta_95_lower != borrowed_width
    assert result.kd_sigma_M != cam_sigma_M
    assert any("no reported uncertainty" in warning.lower() for warning in result.warnings)

    # Fixture sigma, not the published 0.09 nM CaM–M13 value.
    explicit_sigma_M = 2e-7
    explicit = SignalPair(
        signal_id="ligand",
        binder_id="binder",
        partner_id="partner",
        kd_M=1e-6,
        kd_source=_FIXTURE_SOURCE,
        kd_sigma_M=explicit_sigma_M,
    )
    explicit_result = occupancy_for_pair(explicit, c_free_M=c_free_M)
    direct = recruitment_occupancy(
        c_free_M=c_free_M,
        kd_M=1e-6,
        kd_sigma_M=explicit_sigma_M,
    )
    assert explicit_result.kd_sigma_M == explicit_sigma_M
    assert explicit_result.kd_sigma_M != cam_sigma_M
    assert explicit_result.theta_95_lower == direct.theta_95_lower
    assert explicit_result.theta_95_upper == direct.theta_95_upper
    assert explicit_result.theta_95_lower < explicit_result.theta_ss
    assert explicit_result.theta_ss < explicit_result.theta_95_upper

    published = default_cam_m13_pair()
    published_result = occupancy_for_pair(published, c_free_M=1e-9)
    published_direct = recruitment_occupancy(
        c_free_M=1e-9,
        kd_M=published.kd_M,
        kd_sigma_M=CAM_M13_KD_M.sigma,
    )
    assert published.kd_sigma_M == cam_sigma_M
    assert published_result.kd_sigma_M == CAM_M13_KD_M.sigma
    assert published_result.theta_95_lower == published_direct.theta_95_lower
    assert published_result.theta_95_upper == published_direct.theta_95_upper
    assert published_result.theta_95_lower < published_result.theta_ss
    assert published_result.theta_ss < published_result.theta_95_upper


def test_loader_keeps_omitted_sigma_as_none():
    omitted = load_signal_pairs([_row()])
    assert omitted[0].kd_sigma_M is None

    # 1e-8 M is a fixture uncertainty, not a literature sigma.
    explicit = load_signal_pairs([_row(kd_sigma_M=1e-8)])
    assert explicit[0].kd_sigma_M == 1e-8

    zero = load_signal_pairs([_row(kd_sigma_M=0.0)])
    assert zero[0].kd_sigma_M == 0.0

    with pytest.raises(ValueError, match="kd_sigma_M"):
        load_signal_pairs([_row(kd_sigma_M=-1.0)])
