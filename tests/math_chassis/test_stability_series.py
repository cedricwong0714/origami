"""Series selection keeps one paper's constructs from being averaged.

Numbers are read back from the literature JSON. They are not re-typed here
as a second source.
"""

import pytest

from origami.stability.series import (
    PHILLIPS_2012_CTPRA_DSC,
    assert_single_tm_series,
    construct_family,
    literature_table_path,
    load_named_series,
)
from origami.stability.table import load_thermal_table
from origami.engine import ClaspDesignEngine


def test_construct_family_splits_ctpra_from_ctpr():
    assert construct_family("CTPRa10") == "CTPRa"
    assert construct_family("CTPR3") == "CTPR"
    assert construct_family("CTPR2a") == "CTPR2a"


def test_full_literature_table_is_not_one_series():
    rows = load_thermal_table(literature_table_path(), allow_synthetic=False)
    with pytest.raises(ValueError, match="multiple Tm series"):
        assert_single_tm_series(rows)


def test_named_series_is_phillips_ctpra_dsc_only():
    rows = load_named_series(PHILLIPS_2012_CTPRA_DSC)
    assert len(rows) == 7
    assert {row.construct for row in rows} == {
        "CTPRa2",
        "CTPRa3",
        "CTPRa4",
        "CTPRa5",
        "CTPRa6",
        "CTPRa8",
        "CTPRa10",
    }
    assert {row.n_repeats for row in rows} == {2, 3, 4, 5, 6, 8, 10}
    assert all(row.doi == "10.1002/pro.2018" for row in rows)
    assert all(row.method == "DSC" and row.observable == "Tm_C" for row in rows)
    by_n = {row.n_repeats: row.value for row in rows}
    raw = load_thermal_table(literature_table_path(), allow_synthetic=False)
    expected = {
        row.n_repeats: row.value
        for row in raw
        if row.record_id.startswith("phillips2012_ctpra")
        and row.observable == "Tm_C"
        and row.method == "DSC"
    }
    assert by_n == expected


def test_unknown_series_raises():
    with pytest.raises(ValueError, match="unknown thermal series"):
        load_named_series("not_a_series")


def test_scan_uses_named_series_and_skips_unmeasured_n():
    engine = ClaspDesignEngine(payload_radii_A=[8.0, 8.0], n_min=3, n_max=10)
    result = engine.run(thermal_series=PHILLIPS_2012_CTPRA_DSC, t_assay_C=25.0)
    assert result.next_experiment is not None
    assert result.next_experiment.n_repeats in {3, 4, 5, 6, 8, 10}
    assert result.thermal_by_n is not None
    assert result.thermal_by_n[7].state == "omitted"
    assert result.thermal_by_n[4].state == "pass"
    hot = engine.run(thermal_series=PHILLIPS_2012_CTPRA_DSC, t_assay_C=90.0)
    assert hot.next_experiment is None
