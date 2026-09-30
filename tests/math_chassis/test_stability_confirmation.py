"""The stability panel echoes the literature file. It does not add a model.

Scientific basis: the default series is Phillips et al. 2012 CTPRa DSC
(DOI 10.1002/pro.2018, 50 mM phosphate, pH 7.0). 37 C is an E. coli
operating assumption, not a DSC setpoint from that table. Unfolding
delta_G is printed beside the Tm gate and does not decide the state.
Failure mode: a panel that averages series, fills a missing Tm by
blending neighbors, or lets delta_G set thermal_state.
"""

from __future__ import annotations

import json
import math

from origami.api.stability import literature_confirm
from origami.drylab import STABILITY_SERIES, stability_panel
from origami.stability.gate import ThermalRow, thermal_gate
from origami.stability.series import (
    CORTAJARENA_2011_CTPRA_DSC,
    DEFAULT_OPERATING_TEMPERATURE_C,
    PHILLIPS_2012_CTPR_DSC,
    PHILLIPS_2012_CTPRA_CD,
    PHILLIPS_2012_CTPRA_DSC,
    construct_family,
    delta_g_at_n,
    literature_table_path,
    load_named_series,
)
from origami.stability.table import ThermalObservation

# Assay comparison named in the confirmation contract. Not a DSC setpoint.
_ASSAY_C = 37.0
_LENGTHS = (3, 8, 14)
_SERIES = (
    PHILLIPS_2012_CTPRA_DSC,
    CORTAJARENA_2011_CTPRA_DSC,
    PHILLIPS_2012_CTPRA_CD,
    PHILLIPS_2012_CTPR_DSC,
)


def _json_rows() -> list[dict[str, object]]:
    payload = json.loads(literature_table_path().read_text(encoding="utf-8"))
    rows = payload["rows"]
    assert isinstance(rows, list)
    return rows


def _raw_row(record_id: str) -> dict[str, object]:
    matches = [row for row in _json_rows() if row["record_id"] == record_id]
    assert len(matches) == 1
    return matches[0]


def _tm_from_json(series_id: str) -> dict[int, float]:
    """Repeat count to Tm, copied from the JSON row that series selected."""
    found: dict[int, float] = {}
    for obs in load_named_series(series_id):
        raw = _raw_row(obs.record_id)
        assert raw["observable"] == "Tm_C"
        assert raw["n_repeats"] == obs.n_repeats
        assert float(raw["value"]) == float(obs.value)
        n_repeats = int(obs.n_repeats)
        assert n_repeats not in found
        found[n_repeats] = float(raw["value"])
    return found


def _panel_row(panel: list[dict[str, object]], series_id: str, n_repeats: int) -> dict[str, object]:
    matches = [
        row
        for row in panel
        if row["series_id"] == series_id and row["n_repeats"] == n_repeats
    ]
    assert len(matches) == 1
    return matches[0]


def _tm_gate_rows(series_id: str) -> list[ThermalRow]:
    loaded: list[ThermalObservation] = load_named_series(series_id)
    rows = [
        ThermalRow(
            n_repeats=obs.n_repeats,
            observable=obs.observable,
            value=float(obs.value),
            units=obs.units,
            uncertainty=None if obs.uncertainty is None else float(obs.uncertainty),
            data_class="literature",
        )
        for obs in loaded
    ]
    assert rows
    assert all(row.observable == "Tm_C" for row in rows)
    return rows


def _same_series_identity(raw: dict[str, object], exemplar: dict[str, object]) -> bool:
    return (
        raw["doi"] == exemplar["doi"]
        and raw["method"] == exemplar["method"]
        and raw["buffer"] == exemplar["buffer"]
        and raw["pH"] == exemplar["pH"]
        and construct_family(str(raw["construct"]))
        == construct_family(str(exemplar["construct"]))
    )


def test_panel_tm_matches_json_and_n14_is_extrapolated() -> None:
    assert DEFAULT_OPERATING_TEMPERATURE_C == _ASSAY_C
    panel = stability_panel(37)
    measured = {series_id: _tm_from_json(series_id) for series_id in _SERIES}
    for series_id in _SERIES:
        for n_repeats in _LENGTHS:
            row = _panel_row(panel, series_id, n_repeats)
            assert row["calibrated"] is False
            assert row["t_assay_C"] == _ASSAY_C
            if n_repeats in measured[series_id]:
                assert row["tm_C"] == measured[series_id][n_repeats]
            else:
                assert row["tm_C"] is None
            if n_repeats == 14:
                assert 14 not in measured[series_id]
                assert row["thermal_state"] == "extrapolated"
                assert row["tm_C"] is None


def test_default_delta_g_matches_json_and_does_not_set_thermal_state() -> None:
    panel = stability_panel(37)
    tm_rows = _tm_gate_rows(PHILLIPS_2012_CTPRA_DSC)
    exemplar = _raw_row(load_named_series(PHILLIPS_2012_CTPRA_DSC)[0].record_id)
    cited: dict[int, float] = {}
    for n_repeats in (3, 8):
        observation = delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, n_repeats)
        assert observation is not None
        raw = _raw_row(observation.record_id)
        assert raw["observable"] == "delta_G"
        assert raw["n_repeats"] == n_repeats
        assert _same_series_identity(raw, exemplar)
        assert float(raw["value"]) == float(observation.value)
        cited[n_repeats] = float(raw["value"])

        row = _panel_row(panel, PHILLIPS_2012_CTPRA_DSC, n_repeats)
        gate = thermal_gate(n_repeats, _ASSAY_C, tm_rows)
        assert row["delta_g"] == cited[n_repeats]
        assert row["delta_g"] is not None
        assert row["thermal_state"] == gate.state
        assert row["tm_C"] == gate.tm_C

    missing_dg = delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, 14)
    assert missing_dg is None
    json_gap = [
        row
        for row in _json_rows()
        if row["n_repeats"] == 14 and _same_series_identity(row, exemplar)
    ]
    assert json_gap == []
    missing = _panel_row(panel, PHILLIPS_2012_CTPRA_DSC, 14)
    gate_14 = thermal_gate(14, _ASSAY_C, tm_rows)
    assert missing["delta_g"] is None
    assert missing["tm_C"] is None
    assert missing["thermal_state"] == gate_14.state == "extrapolated"

    # A measured Tm with no delta_G companion still follows the Tm gate.
    cortajarena = _panel_row(panel, CORTAJARENA_2011_CTPRA_DSC, 3)
    cortajarena_gate = thermal_gate(3, _ASSAY_C, _tm_gate_rows(CORTAJARENA_2011_CTPRA_DSC))
    assert delta_g_at_n(CORTAJARENA_2011_CTPRA_DSC, 3) is None
    assert cortajarena["delta_g"] is None
    assert cortajarena["tm_C"] is not None
    assert cortajarena["thermal_state"] == cortajarena_gate.state


def test_four_series_stay_unmixed_at_n_3_8_and_14() -> None:
    panel = stability_panel(37)
    focus = [row for row in panel if row["n_repeats"] in _LENGTHS]
    assert len(focus) == 12
    assert {row["series_id"] for row in focus} == set(_SERIES)
    assert len({row["series_id"] for row in focus}) == 4
    assert STABILITY_SERIES == _SERIES
    pairs = {(row["series_id"], row["n_repeats"]) for row in focus}
    assert pairs == {(series_id, n_repeats) for series_id in _SERIES for n_repeats in _LENGTHS}


def test_gaps_are_not_midpoints_of_neighbors() -> None:
    panel = stability_panel(37)
    by_n = _tm_from_json(PHILLIPS_2012_CTPRA_DSC)
    assert 7 not in by_n
    assert 9 not in by_n
    assert 14 not in by_n
    assert 6 in by_n and 8 in by_n
    assert 8 in by_n and 10 in by_n

    row_7 = _panel_row(panel, PHILLIPS_2012_CTPRA_DSC, 7)
    row_9 = _panel_row(panel, PHILLIPS_2012_CTPRA_DSC, 9)
    row_14 = _panel_row(panel, PHILLIPS_2012_CTPRA_DSC, 14)
    midpoint_7 = (by_n[6] + by_n[8]) / 2.0
    midpoint_9 = (by_n[8] + by_n[10]) / 2.0
    assert row_7["tm_C"] is None, (
        f"n=7 is absent from the default series. tm_C must stay null, "
        f"not the midpoint {midpoint_7} of the JSON Tm values at n=6 and n=8."
    )
    assert row_9["tm_C"] is None, (
        f"n=9 is absent from the default series. tm_C must stay null, "
        f"not the midpoint {midpoint_9} of the JSON Tm values at n=8 and n=10."
    )
    assert row_14["tm_C"] is None, (
        "n=14 has no default-series row. tm_C must stay null rather than "
        "a blend of neighboring measured melting temperatures."
    )
    assert row_7["thermal_state"] == "omitted"
    assert row_9["thermal_state"] == "omitted"
    assert row_14["thermal_state"] == "extrapolated"


def test_null_tm_uncertainty_omits_the_gate_envelope() -> None:
    """A missing printed Tm uncertainty stays null on the panel.

    The gate still reports a zero-width envelope for that row. The
    confirmation payload must not copy that envelope, or the board
    would show low = high = Tm as if the sigma were 0.
    Scientific basis: Cortajarena and Regan 2011 Table I prints Tm
    without an uncertainty (DOI 10.1002/pro.564). Failure mode: a
    panel that turns that blank into ±0.
    """
    panel = stability_panel(37)
    focus = [row for row in panel if row["n_repeats"] in _LENGTHS]
    assert len(focus) == 12
    saw_null = False
    saw_printed = False
    for series_id in _SERIES:
        loaded = load_named_series(series_id)
        gate_rows = _tm_gate_rows(series_id)
        for n_repeats in _LENGTHS:
            row = _panel_row(panel, series_id, n_repeats)
            matched = [obs for obs in loaded if obs.n_repeats == n_repeats]
            gate = thermal_gate(n_repeats, _ASSAY_C, gate_rows)
            assert row["thermal_state"] == gate.state
            if len(matched) == 1 and matched[0].uncertainty is None:
                saw_null = True
                assert row["tm_C"] == float(matched[0].value)
                assert row["tm_uncertainty_C"] is None
                assert row["tm_interval_low"] is None
                assert row["tm_interval_high"] is None
                assert gate.tm_C == float(matched[0].value)
                assert gate.interval_low == gate.interval_high == gate.tm_C
            elif len(matched) == 1 and matched[0].uncertainty is not None:
                saw_printed = True
                assert row["tm_uncertainty_C"] == float(matched[0].uncertainty)
                assert row["tm_interval_low"] == gate.interval_low
                assert row["tm_interval_high"] == gate.interval_high
                assert row["tm_interval_low"] != row["tm_interval_high"]
            else:
                assert matched == []
                assert row["tm_C"] is None
                assert row["tm_uncertainty_C"] is None
                assert row["tm_interval_low"] is None
                assert row["tm_interval_high"] is None
                assert row["thermal_state"] == "extrapolated"
    assert saw_null
    assert saw_printed


def test_confirm_page_payload_evaluates_the_fit_at_n_14() -> None:
    """The confirmation payload shows the length model, including n = 14.

    The lookup panel still leaves a missing table cell empty. This
    payload does not. Failure mode: a blank n = 14, a copied table
    cell used as the primary number, or one series fit on another's
    points. A passing test is not scientific validation.
    """
    from origami.stability.length_fit import fit_named_delta_g, fit_named_tm, saturating_value

    body = literature_confirm(_ASSAY_C)
    rows = body["rows"]
    assert body["calibrated"] is False
    assert body["comparison"] == "fit"
    assert body["confidence_tier"] == "hypothesis_only"
    assert len(rows) == 12
    assert {row["series_id"] for row in rows} == set(_SERIES)
    pairs = {(row["series_id"], row["n_repeats"]) for row in rows}
    assert pairs == {(series_id, n_repeats) for series_id in _SERIES for n_repeats in _LENGTHS}
    assert "no Tm(n) was fit" not in body["note"]
    assert "calculated" in body["note"].lower()
    assert "ΔHcal" in body["note"]

    default_fit = fit_named_tm(PHILLIPS_2012_CTPRA_DSC)
    assert default_fit.form == "saturating"
    theta = tuple(parameter.value for parameter in default_fit.parameters)
    for n_repeats in _LENGTHS:
        row = _panel_row(rows, PHILLIPS_2012_CTPRA_DSC, n_repeats)
        expected = saturating_value(n_repeats, theta[0], theta[1], theta[2])
        assert row["calibrated"] is False
        assert row["comparison_uses_fit"] is True
        assert row["tm_C"] == expected
        assert row["tm_C"] == default_fit.predict(n_repeats).value
        assert math.isfinite(row["tm_C"])
        assert row["thermal_state"] in ("pass", "fail")
        assert "The comparison uses the fit." in row["thermal_reason"]
        assert row["tm_band_label"] == "linear approximation"
        assert row["confidence_tier"] == "hypothesis_only"
    row_3 = _panel_row(rows, PHILLIPS_2012_CTPRA_DSC, 3)
    row_8 = _panel_row(rows, PHILLIPS_2012_CTPRA_DSC, 8)
    row_14 = _panel_row(rows, PHILLIPS_2012_CTPRA_DSC, 14)
    assert row_3["paper_tm_C"] == 63.0
    assert row_3["tm_C"] != row_3["paper_tm_C"]
    assert row_8["paper_tm_C"] == 74.0
    assert row_8["tm_C"] != 74
    assert row_8["tm_C"] != 63
    assert row_14["paper_tm_C"] is None
    assert row_14["past_longest_cited_length"] is True
    assert row_14["longest_cited_n"] == max(
        obs.n_repeats for obs in load_named_series(PHILLIPS_2012_CTPRA_DSC)
    )
    assert row_14["length_note"] == (
        f"14 is past the longest cited length in this series ({row_14['longest_cited_n']})."
    )
    assert "extrapolated" not in row_14["length_note"]
    dg_fit = fit_named_delta_g(PHILLIPS_2012_CTPRA_DSC)
    assert dg_fit.form == "saturating"
    assert math.isfinite(row_14["delta_g"])
    assert row_14["delta_g"] == dg_fit.predict(14).value
    assert row_14["paper_delta_g"] is None
    assert row_3["paper_delta_g"] == 4.8

    cortajarena_dg = fit_named_delta_g(CORTAJARENA_2011_CTPRA_DSC)
    assert cortajarena_dg.form == "not_fit"
    assert cortajarena_dg.n_points == 0
    for n_repeats in _LENGTHS:
        cortajarena = _panel_row(rows, CORTAJARENA_2011_CTPRA_DSC, n_repeats)
        assert math.isfinite(cortajarena["tm_C"])
        assert cortajarena["delta_g"] is None
        assert cortajarena["delta_g_fit_form"] == "not_fit"

    ctpr_fit = fit_named_tm(PHILLIPS_2012_CTPR_DSC)
    assert len(ctpr_fit.n_repeats) < 4
    assert ctpr_fit.form == "line"
    assert len(ctpr_fit.parameters) == 2
    ctpr_14 = _panel_row(rows, PHILLIPS_2012_CTPR_DSC, 14)
    assert math.isfinite(ctpr_14["tm_C"])
    assert ctpr_14["tm_fit_form"] == "line"
    assert any("Two points determine a line" in warning for warning in ctpr_fit.warnings)

    phillips_points = set(zip(default_fit.n_repeats, default_fit.values, strict=True))
    cort_fit = fit_named_tm(CORTAJARENA_2011_CTPRA_DSC)
    cort_points = set(zip(cort_fit.n_repeats, cort_fit.values, strict=True))
    assert phillips_points.isdisjoint(cort_points)
    assert _panel_row(rows, CORTAJARENA_2011_CTPRA_DSC, 8)["tm_C"] != row_8["tm_C"]
