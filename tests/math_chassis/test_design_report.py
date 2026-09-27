"""Packaging tests for DesignReport.

These checks do not validate CTPR geometry, Kd, clash, or capture physics.
They only check that assemble_report records caller-supplied numbers and
refuses an unsupported calibration claim.
"""

import json

import numpy as np

from origami.report import DesignReport, assemble_report


def _full_report_kwargs() -> dict:
    # Synthetic caller inputs. p_capture is deliberately not Da / (1 + Da).
    return {
        "design_id": "ctpr-8-cam-m13",
        "prior_geometry_id": "src.core.ctpr_geometry",
        "prior_kd_id": "cam_m13_peptide_0.19nM",
        "n_repeats": 8,
        "pair_distances_A": {"0-7": 42.0},
        "p_clash": {"0-7": 0.1},
        "c_eff_M": {"0-7": 1.5e-4},
        "theta_ss": 0.35,
        "theta_95_lower": 0.2,
        "theta_95_upper": 0.5,
        "da": 2.0,
        "p_capture": 0.4,
        "gp_mean": [0.2, 0.5],
        "gp_std": [0.1, 0.3],
        "next_n": 12,
        "calibrated": False,
        "warnings": ["Caller-supplied summary. Not a wet-lab calibration."],
        "omitted": [],
    }


def _assert_json_round_trip(report: DesignReport) -> dict:
    payload = report.to_dict()
    encoded = json.dumps(payload)
    loaded = json.loads(encoded)
    assert loaded == payload
    restored = DesignReport(**loaded)
    assert restored.to_dict() == payload
    return payload


def test_refuses_calibrated_true_without_wet_lab():
    kwargs = _full_report_kwargs()
    kwargs["calibrated"] = True
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        message = str(exc)
        assert "wet_lab" in message
        assert "calibrated" in message
    else:
        raise AssertionError("calibrated=True without wet_lab must be refused")

    kwargs["evidence_source"] = "none"
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        assert "wet_lab" in str(exc)
    else:
        raise AssertionError("evidence_source='none' must keep calibrated=True refused")

    kwargs["evidence_source"] = "literature_placeholder"
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        assert "wet_lab" in str(exc)
    else:
        raise AssertionError("a literature source must not unlock calibrated=True")


def test_full_report_stays_uncalibrated_and_keeps_prior_ids():
    report = assemble_report(**_full_report_kwargs())
    assert report.calibrated is False
    assert report.prior_geometry_id == "src.core.ctpr_geometry"
    assert report.prior_kd_id == "cam_m13_peptide_0.19nM"
    assert report.design_id == "ctpr-8-cam-m13"
    assert report.n_repeats == 8
    assert report.pair_distances_A == {"0-7": 42.0}
    assert report.p_clash == {"0-7": 0.1}
    assert report.c_eff_M["0-7"] == 1.5e-4
    assert report.theta_ss == 0.35
    assert report.theta_95_lower == 0.2
    assert report.theta_95_upper == 0.5
    assert report.da == 2.0
    assert report.p_capture == 0.4
    assert report.p_capture != report.da / (1.0 + report.da)
    assert report.gp_mean == [0.2, 0.5]
    assert report.gp_std == [0.1, 0.3]
    assert report.next_n == 12
    assert report.warnings == ["Caller-supplied summary. Not a wet-lab calibration."]
    assert report.omitted == []
    for name in ("theta_t", "time_s", "theta_time", "time_course"):
        assert not hasattr(report, name)


def test_wet_lab_claim_stores_calibrated_as_given():
    # The string is the caller's claim. This test does not create wet-lab data.
    claimed_kwargs = _full_report_kwargs()
    claimed_kwargs["calibrated"] = True
    claimed_kwargs["evidence_source"] = "wet_lab"
    claimed = assemble_report(**claimed_kwargs)
    assert claimed.calibrated is True

    still_false_kwargs = _full_report_kwargs()
    still_false_kwargs["evidence_source"] = "wet_lab"
    still_false = assemble_report(**still_false_kwargs)
    assert still_false.calibrated is False


def test_rejects_theta_outside_unit_interval():
    kwargs = _full_report_kwargs()
    kwargs["theta_ss"] = 1.2
    kwargs["theta_95_lower"] = None
    kwargs["theta_95_upper"] = None
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        assert "theta_ss" in str(exc)
        assert "1.2" in str(exc)
    else:
        raise AssertionError("theta_ss=1.2 must be rejected")


def test_rejects_negative_clash_and_effective_concentration():
    clash = _full_report_kwargs()
    clash["p_clash"] = {"0-7": -0.01}
    try:
        assemble_report(**clash)
    except ValueError as exc:
        assert "p_clash" in str(exc)
    else:
        raise AssertionError("negative p_clash must be rejected")

    ceff = _full_report_kwargs()
    ceff["c_eff_M"] = {"0-7": -1e-6}
    try:
        assemble_report(**ceff)
    except ValueError as exc:
        assert "c_eff_M" in str(exc)
    else:
        raise AssertionError("negative c_eff must be rejected")


def test_missing_da_requires_omitted_rate_and_no_capture():
    kwargs = _full_report_kwargs()
    kwargs["da"] = None
    kwargs["p_capture"] = None
    kwargs["omitted"] = ["linker_length"]
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        assert "k_escape" in str(exc) or "k_capture" in str(exc)
    else:
        raise AssertionError("missing Da must name k_escape or k_capture")

    kwargs["p_capture"] = 0.4
    kwargs["omitted"] = ["k_escape"]
    try:
        assemble_report(**kwargs)
    except ValueError as exc:
        assert "p_capture" in str(exc)
    else:
        raise AssertionError("p_capture must stay unset when da is None")

    kwargs["p_capture"] = None
    report = assemble_report(**kwargs)
    assert report.da is None
    assert report.p_capture is None
    assert report.omitted == ["k_escape"]
    assert not hasattr(report, "theta_t")


def test_does_not_fill_capture_or_a_time_course():
    kwargs = _full_report_kwargs()
    kwargs["da"] = 1.0
    kwargs["p_capture"] = None
    report = assemble_report(**kwargs)
    assert report.da == 1.0
    assert report.p_capture is None
    payload = report.to_dict()
    assert "theta_t" not in payload
    assert "time_s" not in payload


def test_to_dict_round_trips_through_json():
    kwargs = _full_report_kwargs()
    kwargs["n_repeats"] = np.int64(8)
    kwargs["p_clash"] = {"0-7": np.float64(0.1)}
    kwargs["gp_mean"] = np.array([0.2, 0.5])
    kwargs["gp_std"] = np.array([0.1, 0.3])
    payload = _assert_json_round_trip(assemble_report(**kwargs))
    assert type(payload["n_repeats"]) is int
    assert type(payload["p_clash"]["0-7"]) is float
    assert type(payload["gp_mean"][0]) is float
    assert type(payload["gp_std"][0]) is float
    assert type(payload["calibrated"]) is bool
    assert type(payload["next_n"]) is int
    assert payload["prior_geometry_id"] == "src.core.ctpr_geometry"
    assert payload["prior_kd_id"] == "cam_m13_peptide_0.19nM"
    assert payload["calibrated"] is False
    assert set(payload) == {
        "design_id",
        "prior_geometry_id",
        "prior_kd_id",
        "n_repeats",
        "pair_distances_A",
        "p_clash",
        "c_eff_M",
        "theta_ss",
        "theta_95_lower",
        "theta_95_upper",
        "da",
        "p_capture",
        "gp_mean",
        "gp_std",
        "next_n",
        "calibrated",
        "warnings",
        "omitted",
    }

    partial_kwargs = _full_report_kwargs()
    partial_kwargs.update(
        theta_ss=None,
        theta_95_lower=None,
        theta_95_upper=None,
        da=None,
        p_capture=None,
        gp_mean=None,
        gp_std=None,
        next_n=None,
        omitted=["k_capture"],
    )
    partial = _assert_json_round_trip(assemble_report(**partial_kwargs))
    assert partial["theta_ss"] is None
    assert partial["da"] is None
    assert partial["p_capture"] is None
    assert partial["gp_mean"] == []
    assert partial["gp_std"] == []
    assert partial["next_n"] is None
    assert partial["omitted"] == ["k_capture"]
    assert "theta_t" not in partial
