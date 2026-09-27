"""Synthetic checks for the thermal gate.

Temperatures such as 80 C and 40 C are obvious fixtures. They are not
literature melting temperatures and are not cited measurements.
"""

from origami.stability.gate import ThermalGateResult, ThermalRow, thermal_gate


def _row(
    n_repeats: int,
    observable: str,
    value: float,
    uncertainty: float | None = None,
    units: str = "C",
) -> ThermalRow:
    return ThermalRow(
        n_repeats=n_repeats,
        observable=observable,
        value=value,
        units=units,
        uncertainty=uncertainty,
        data_class="synthetic_fixture",
    )


def test_empty_rows_are_omitted() -> None:
    result = thermal_gate(4, 37.0, [])
    assert result == ThermalGateResult(
        state="omitted",
        tm_C=None,
        interval_low=None,
        interval_high=None,
        n_repeats=4,
        reason="no Tm_C rows",
    )


def test_delta_g_rows_do_not_become_a_tm() -> None:
    rows = [_row(4, "delta_G", -12.0, units="kcal/mol")]
    result = thermal_gate(4, 25.0, rows)
    assert result.state == "omitted"
    assert result.tm_C is None
    assert result.reason == "no Tm_C rows"


def test_assay_below_tm_passes() -> None:
    rows = [_row(4, "Tm_C", 80.0, uncertainty=1.0)]
    result = thermal_gate(4, 37.0, rows)
    assert result.state == "pass"
    assert result.tm_C == 80.0
    assert result.interval_low == 79.0
    assert result.interval_high == 81.0
    assert result.n_repeats == 4


def test_assay_above_tm_fails() -> None:
    rows = [_row(8, "Tm_C", 40.0, uncertainty=2.0)]
    result = thermal_gate(8, 55.0, rows)
    assert result.state == "fail"
    assert result.tm_C == 40.0
    assert result.interval_low == 38.0
    assert result.interval_high == 42.0


def test_assay_equal_to_tm_fails() -> None:
    rows = [_row(4, "Tm_C", 40.0)]
    result = thermal_gate(4, 40.0, rows)
    assert result.state == "fail"
    assert result.tm_C == 40.0
    assert result.interval_low == 40.0
    assert result.interval_high == 40.0


def test_n_outside_cited_repeat_range_is_extrapolated() -> None:
    rows = [
        _row(4, "Tm_C", 80.0, uncertainty=1.0),
        _row(8, "Tm_C", 40.0, uncertainty=1.0),
        _row(1, "delta_G", -5.0, units="kcal/mol"),
    ]
    below = thermal_gate(2, 37.0, rows)
    above = thermal_gate(12, 37.0, rows)
    for result in (below, above):
        assert result.state == "extrapolated"
        assert result.tm_C is None
        assert result.interval_low is None
        assert result.interval_high is None
        assert "outside the cited repeat range" in result.reason
    assert below.n_repeats == 2
    assert above.n_repeats == 12


def test_n_between_measured_points_is_not_interpolated() -> None:
    rows = [
        _row(4, "Tm_C", 80.0),
        _row(8, "Tm_C", 40.0),
    ]
    result = thermal_gate(6, 37.0, rows)
    assert result.state == "omitted"
    assert result.tm_C is None
    assert result.interval_low is None
    assert result.interval_high is None
    assert result.reason == "no measurement at this n; interpolation is not implemented"


def test_cited_range_is_inclusive() -> None:
    rows = [
        _row(4, "Tm_C", 80.0),
        _row(8, "Tm_C", 40.0),
    ]
    low = thermal_gate(4, 37.0, rows)
    high = thermal_gate(8, 50.0, rows)
    assert low.state == "pass"
    assert low.tm_C == 80.0
    assert high.state == "fail"
    assert high.tm_C == 40.0


def test_duplicate_n_uses_mean_and_envelope_not_pooled_sigma() -> None:
    rows = [
        _row(4, "Tm_C", 80.0, uncertainty=5.0),
        _row(4, "Tm_C", 60.0, uncertainty=None),
        _row(4, "delta_G", -9.0, units="kcal/mol"),
    ]
    result = thermal_gate(4, 50.0, rows)
    assert result.state == "pass"
    assert result.tm_C == 70.0
    assert result.interval_low == 60.0
    assert result.interval_high == 85.0
