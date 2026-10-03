"""Plate-to-freeze scoring and standard-curve quantification.

Scientific basis: a blank-corrected RLU can be compared with a frozen
dose only at the same calcium, and amount is (RLU - a) / b from the
caller-supplied line. ODE parameter sigmas are not invented.
Failure mode: scoring a well that has no calcium, or treating the ±30%
band as a propagated interval.
A passing test is not scientific validation.
"""

from __future__ import annotations

import json

import pytest

from origami.lab.freeze_compare import FreezeCompareError, compare_plate_csv
from origami.lab.plate_reader import parse_plate_csv
from origami.ssdk.learn import SsdkLearnError, learn_ssdk
from origami.ssdk.quantify import quantify_luminescence_rows
from src.predictions.freeze import freeze_prediction
from src.predictions.luminescence_interval import (
    delta_method_interval,
    parameter_error_report,
    placeholder_interval,
)

_HEAD = "well,construct,n_repeats,batch,role,rlu,calcium_uM\n"


def test_calcium_column_keeps_doses_separate():
    text = _HEAD + (
        "A1,c8,8,b1,blank,10,\n"
        "B1,c8,8,b1,sample,110,1\n"
        "B2,c8,8,b1,sample,210,5\n"
    )
    rows = parse_plate_csv(text, "p.csv")["observations"]
    by_calcium = {row["calcium_uM"]: row["y"] for row in rows}
    assert by_calcium[1.0] == pytest.approx(100.0)
    assert by_calcium[5.0] == pytest.approx(200.0)


def test_empty_calcium_cell_is_rejected_when_the_column_exists():
    from origami.lab.plate_reader import PlateReaderError

    with pytest.raises(PlateReaderError, match="calcium_uM is empty"):
        parse_plate_csv(
            _HEAD + "A1,c,8,b1,blank,1,\nB1,c,8,b1,sample,5,\n",
            "p.csv",
        )


def test_plate_scores_only_a_matching_calcium_and_names_the_placeholder():
    text = (
        "well,construct,n_repeats,batch,role,rlu,calcium_uM\n"
        "A1,inside,8,b1,blank,0,1\n"
        "B1,inside,8,b1,sample,800,1\n"
        "A2,outside,8,b1,blank,0,1\n"
        "B2,outside,8,b1,sample,2000,1\n"
        "A3,other,5,b2,blank,0,1\n"
        "B3,other,5,b2,sample,800,1\n"
    )
    report = compare_plate_csv(text, source="demo.csv")
    assert report["calibrated"] is False
    assert report["parameter_error"]["parameter_error_propagated"] is False
    by_construct = {row["construct"]: row for row in report["comparisons"]}
    assert by_construct["inside"]["status"] == "compared"
    assert by_construct["inside"]["within_95ci"] is True
    assert by_construct["inside"]["uncertainty_method"] == (
        "fixed_relative_placeholder_pm_30_percent"
    )
    assert by_construct["outside"]["within_95ci"] is False
    assert by_construct["other"]["status"] == "no_frozen_scaffold"
    untested = {item["key"] for item in report["untested_predictions"]}
    assert "contour_nm" in untested
    assert "phillips_tm_length_curve" in untested


def test_plate_without_calcium_is_not_scored():
    text = (
        "well,construct,n_repeats,batch,role,rlu\n"
        "A1,c8,8,b1,blank,0\n"
        "B1,c8,8,b1,sample,800\n"
    )
    row = compare_plate_csv(text)["comparisons"][0]
    assert row["status"] == "not_comparable"
    assert row["calcium_uM"] is None


def test_checksum_mismatch_refuses_the_file(tmp_path):
    path = freeze_prediction(
        "scaffold-n8",
        design_spec={"n_repeats": 8},
        predictions={
            "ca_1uM": {
                "predicted_value": 10.0,
                "uncertainty_95_lower": 7.0,
                "uncertainty_95_upper": 13.0,
                "confidence_tier": "hypothesis_only",
            }
        },
        model_version="test",
        output_dir=tmp_path,
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["predictions"]["ca_1uM"]["predicted_value"] = 11.0
    path.write_text(json.dumps(payload), encoding="utf-8")
    text = (
        "well,construct,n_repeats,batch,role,rlu,calcium_uM\n"
        "A1,c,8,b1,blank,0,1\nB1,c,8,b1,sample,10,1\n"
    )
    with pytest.raises(FreezeCompareError, match="checksum"):
        compare_plate_csv(text, frozen_dir=tmp_path)


def test_placeholder_interval_does_not_propagate_ode_error():
    interval = placeholder_interval(100.0)
    assert interval["uncertainty_95_lower"] == pytest.approx(70.0)
    assert interval["uncertainty_95_upper"] == pytest.approx(130.0)
    assert interval["parameter_error_propagated"] is False
    names = {item["name"] for item in parameter_error_report()["blocked_parameters"]}
    assert names == {"k_c_M", "n_h", "k_on", "k_off", "k_lock", "r0", "alpha", "eta"}


def test_delta_method_accepts_only_user_entered_sigmas():
    interval = delta_method_interval(
        10.0,
        {"alpha": 2.0},
        {"alpha": {"sigma": 3.0, "provenance": "user_entered", "units": "RLU per M"}},
    )
    half = 1.96 * 2.0 * 3.0
    assert interval["uncertainty_95_upper"] - 10.0 == pytest.approx(half)
    assert interval["parameter_error_propagated"] is True
    assert interval["calibrated"] is False
    with pytest.raises(ValueError, match="user_entered"):
        delta_method_interval(
            10.0,
            {"alpha": 2.0},
            {"alpha": {"sigma": 3.0, "provenance": "literature_placeholder"}},
        )


def test_standard_curve_converts_luminescence_and_leaves_locking():
    report = quantify_luminescence_rows(
        [
            {"n_repeats": 8, "y": 10.0, "sigma": 1.0, "output": "luminescence"},
            {"n_repeats": 8, "y": 0.2, "output": "locking_fraction"},
        ],
        {"amount": [0, 1, 2, 3], "rlu": [0, 2, 4, 6]},
        "fmol",
    )
    assert report["applied"] is True
    assert report["calibrated"] is False
    lum, lock = report["rows"]
    assert lum["y"] == pytest.approx(5.0)
    assert lum["y_rlu"] == pytest.approx(10.0)
    assert lum["units"] == "fmol"
    assert lum["sigma"] is not None
    assert lock["y"] == pytest.approx(0.2)
    assert "y_rlu" not in lock


def test_learn_quantifies_only_when_asked():
    body = {
        "n_min": 8,
        "n_max": 12,
        "observations": [
            {"n_repeats": 8, "y": 10.0, "source": "curve"},
            {"n_repeats": 10, "y": 20.0, "source": "curve"},
        ],
        "standard_curve": {"amount": [0, 1, 2], "rlu": [0, 2, 4]},
        "amount_units": "fmol",
    }
    untouched = learn_ssdk(body)
    assert untouched["quantification"]["applied"] is False
    assert untouched["calibrated"] is False
    converted = learn_ssdk({**body, "quantify_luminescence": True})
    assert converted["quantification"]["applied"] is True
    amounts = [row["y"] for row in converted["quantification"]["rows"]]
    assert amounts == pytest.approx([5.0, 10.0])
    with pytest.raises(SsdkLearnError, match="not usable"):
        learn_ssdk(
            {
                **body,
                "quantify_luminescence": True,
                "standard_curve": {"amount": [1, 1, 1], "rlu": [2, 2, 2]},
            }
        )
