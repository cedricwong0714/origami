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
