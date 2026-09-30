"""Per-series length curves are evaluated, not copied from a table cell.

Scientific basis: the saturating form is the length model
y(n) = y_inf - (y_inf - y_1) * exp(-(n-1)/lambda), with positive
coefficients. It is an assumption about a rod whose ends matter less
as it gets longer, not a calibrated chassis measurement. With fewer
than four points the three-parameter form is not identifiable from
the point count, so the fit is the line y(n) = a + b*n.
Failure mode: a hardcoded 63 or 74, a 3-parameter fit on three points,
or one series trained on another series' rows.
A passing test is not scientific validation.
"""

from __future__ import annotations

import math

import pytest

from origami.stability.length_fit import (
    fit_length_curve,
    fit_named_delta_g,
    fit_named_tm,
    line_value,
    saturating_value,
)
from origami.stability.series import (
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPR_DSC,
    PHILLIPS_2012_CTPRA_DSC,
    load_named_series,
)


def test_saturating_fit_recovers_parameters() -> None:
    y_inf = 85.0
    y_1 = 40.0
    lam = 2.5
    ns = [2, 3, 4, 6, 8, 10]
    ys = [saturating_value(n, y_inf, y_1, lam) for n in ns]
    fit = fit_length_curve(ns, ys, units="C")
    assert fit.form == "saturating"
    assert len(fit.parameters) == 3
    by_name = {parameter.name: parameter for parameter in fit.parameters}
    assert by_name["y_inf"].value == pytest.approx(y_inf, rel=1e-6, abs=1e-6)
    assert by_name["y_1"].value == pytest.approx(y_1, rel=1e-6, abs=1e-6)
    assert by_name["lambda"].value == pytest.approx(lam, rel=1e-6, abs=1e-6)
    assert all(parameter.identifiable for parameter in fit.parameters)
    assert fit.predict(4).calibrated is False


def test_held_in_prediction_is_the_model_not_a_copied_cell() -> None:
    """The value at a training length is the equation, not 63 or 74.

    63 °C and 74 °C are Phillips 2012 CTPRa DSC table cells. This series
    is synthetic and does not contain those cells.
    """
    y_inf = 90.0
    y_1 = 30.0
    lam = 3.0
    ns = [2, 4, 6, 8]
    ys = [saturating_value(n, y_inf, y_1, lam) for n in ns]
    fit = fit_length_curve(ns, ys, units="C")
    theta = tuple(parameter.value for parameter in fit.parameters)
    pred = fit.predict(6)
    expected = saturating_value(6, theta[0], theta[1], theta[2])
    assert pred.value == pytest.approx(expected, abs=1e-9)
    assert pred.value == pytest.approx(ys[2], abs=1e-6)
    assert pred.value not in (63, 74)
    pred_14 = fit.predict(14)
    assert pred_14.value == pytest.approx(saturating_value(14, theta[0], theta[1], theta[2]))
    assert pred_14.value not in (63, 74)
    assert math.isfinite(pred_14.value or float("nan"))
    assert pred.band_label == "linear approximation"
    assert pred.confidence_tier == "hypothesis_only"


def test_phillips_n14_tm_is_finite_and_past_the_longest_cited_length() -> None:
    fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    cited = [obs.n_repeats for obs in load_named_series(PHILLIPS_2012_CTPRA_DSC)]
    pred = fit.predict(14)
    assert pred.value is not None
    assert math.isfinite(pred.value)
    assert pred.longest_cited_n == max(cited)
    assert 14 > pred.longest_cited_n
    assert pred.past_longest_cited_length is True
    assert pred.length_note == (
        f"14 is past the longest cited length in this series ({pred.longest_cited_n})."
    )
    assert pred.length_note is not None
    assert "extrapolated" not in pred.length_note
    theta = tuple(parameter.value for parameter in fit.parameters)
    assert pred.value == pytest.approx(saturating_value(14, theta[0], theta[1], theta[2]))


def test_a_series_is_not_fit_on_another_series_points() -> None:
    phillips = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    cortajarena = fit_named_tm(CORTAJARENA_2011_CTPRA_DSC)
    phillips_rows = {
        (obs.n_repeats, float(obs.value)) for obs in load_named_series(PHILLIPS_2012_CTPRA_DSC)
    }
    cortajarena_rows = {
        (obs.n_repeats, float(obs.value))
        for obs in load_named_series(CORTAJARENA_2011_CTPRA_DSC)
    }
    assert set(zip(phillips.n_repeats, phillips.values, strict=True)) == phillips_rows
    assert set(zip(cortajarena.n_repeats, cortajarena.values, strict=True)) == cortajarena_rows
    assert phillips_rows.isdisjoint(cortajarena_rows)
    assert phillips.predict(8).value != pytest.approx(cortajarena.predict(8).value)
    mixed = fit_length_curve(
        list(phillips.n_repeats) + list(cortajarena.n_repeats),
        list(phillips.values) + list(cortajarena.values),
        units="C",
    )
    assert mixed.form == "not_fit"
    assert any("not averaged" in warning for warning in mixed.warnings)
    assert mixed.predict(14).value is None


def test_fewer_than_four_points_is_not_a_three_parameter_fit() -> None:
    three = fit_length_curve([2, 3, 4], [10.0, 12.0, 15.0], units="C")
    assert three.form == "line"
    assert len(three.parameters) == 2
    assert three.form != "saturating"
    two = fit_named_tm(PHILLIPS_2012_CTPR_DSC)
    assert two.n_points == 2
    assert two.form == "line"
    assert len(two.parameters) == 2
    assert any("Two points determine a line" in warning for warning in two.warnings)
    assert all(not parameter.identifiable for parameter in two.parameters)
    held = two.predict(two.n_repeats[0])
    a = two.parameters[0].value
    b = two.parameters[1].value
    assert held.value == pytest.approx(line_value(two.n_repeats[0], a, b))
    assert held.sigma is None
    assert held.band_95_low is None
    one = fit_length_curve([4], [70.0], units="C")
    assert one.form == "not_fit"
    assert one.predict(14).value is None
    assert len(one.parameters) == 0


def test_cortajarena_delta_g_is_not_borrowed_from_phillips() -> None:
    cortajarena = fit_named_delta_g(CORTAJARENA_2011_CTPRA_DSC)
    phillips = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    assert cortajarena.form == "not_fit"
    assert cortajarena.n_points == 0
    assert cortajarena.predict(3).value is None
    assert cortajarena.predict(14).value is None
    assert phillips.form == "line"
    assert phillips.n_points >= 4
    assert {parameter.name for parameter in phillips.parameters} == {"a", "b"}
    assert phillips.predict(14).value is not None
    assert math.isfinite(phillips.predict(14).value or float("nan"))
    assert set(phillips.values).isdisjoint(set(cortajarena.values))


def test_default_series_delta_g_shown_at_3_8_and_14_is_identifiable() -> None:
    """The ΔG number on the confirmation payload has a usable 95% band.

    Scientific basis: a saturating fit is non-identifiable when a
    parameter standard error is not finite, or when the prediction
    sigma at n = 3, 8, or 14 is larger than the absolute prediction.
    Those coefficients must not be presented as fitted values.
    Failure mode: a Phillips CTPRa DSC ΔG whose 95% half-width is
    thousands of kcal mol-1, or a Tm fit that left the saturating form.
    A passing test is not scientific validation.
    """
    from origami.api.stability import literature_confirm

    body = literature_confirm(37.0)
    assert body["calibrated"] is False
    rows = [
        row
        for row in body["rows"]
        if row["series_id"] == PHILLIPS_2012_CTPRA_DSC
    ]
    assert {row["n_repeats"] for row in rows} == {3, 8, 14}
    assert {row["tm_fit_form"] for row in rows} == {"saturating"}
    tm = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    assert tm.form == "saturating"
    dg = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    fits = body["series_fits"]
    block = next(item for item in fits if item["series_id"] == PHILLIPS_2012_CTPRA_DSC)
    assert block["tm"]["form"] == "saturating"
    for n_repeats in (3, 8, 14):
        row = next(item for item in rows if item["n_repeats"] == n_repeats)
        value = row["delta_g"]
        low = row["delta_g_band_95_low"]
        high = row["delta_g_band_95_high"]
        if value is None:
            assert row["delta_g_fit_form"] == "not_fit"
            assert any(
                "do not determine ΔG(n)" in warning for warning in dg.warnings
            )
            assert dg.predict(n_repeats).value is None
            continue
        assert isinstance(value, float)
        assert low is not None and high is not None
        half = (float(high) - float(low)) / 2.0
        assert math.isfinite(half)
        assert half < abs(float(value))
        assert row["delta_g_fit_form"] == "line"
        assert row["delta_g"] == dg.predict(n_repeats).value
        assert row["calibrated"] is False
    assert dg.form == "line"
    assert block["delta_g"]["form"] == "line"
    names = {parameter["name"] for parameter in block["delta_g"]["parameters"]}
    assert names == {"a", "b"}
    assert "y_inf" not in names


def test_nonidentifiable_line_omits_the_delta_g_point_value() -> None:
    """Both forms non-identifiable means no ΔG(n) point value.

    Scientific basis: the same identifiability rule applies to the
    straight-line fallback. Failure mode: a point value whose sigma
    exceeds the absolute prediction. A passing test is not scientific
    validation.
    """
    fit = fit_length_curve(
        [2, 4, 6, 8],
        [0.01, -0.02, 0.015, -0.01],
        units="kcal mol-1",
        undetermined_message="The rows do not determine ΔG(n).",
    )
    assert fit.form == "not_fit"
    assert fit.parameters == ()
    assert any("do not determine ΔG(n)" in warning for warning in fit.warnings)
    for n_repeats in (3, 8, 14):
        prediction = fit.predict(n_repeats)
        assert prediction.value is None
        assert prediction.band_95_low is None
        assert prediction.band_95_high is None
        assert prediction.calibrated is False


def test_line_prediction_is_not_the_phillips_table_cells() -> None:
    fit = fit_length_curve([2, 5], [10.0, 40.0], units="C")
    assert fit.form == "line"
    pred = fit.predict(5)
    a = fit.parameters[0].value
    b = fit.parameters[1].value
    assert pred.value == pytest.approx(line_value(5, a, b))
    assert pred.value == pytest.approx(40.0)
    assert pred.value not in (63, 74)
