"""Series selection keeps one paper's constructs from being averaged.

Numbers are read back from the literature JSON. They are not re-typed here
as a second source.
"""

import pytest

from origami.engine import ClaspDesignEngine
from origami.stability.series import (
    PHILLIPS_2012_CTPRA_DSC,
    CitedDeltaGRank,
    assert_single_tm_series,
    construct_family,
    delta_g_at_n,
    literature_table_path,
    load_named_series,
    rank_companion_delta_g,
    rank_printed_delta_g,
)
from origami.stability.table import ThermalObservation, load_thermal_table


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


def test_named_tm_series_stay_separate():
    cortajarena = load_named_series("cortajarena2011_ctpra_dsc")
    cd = load_named_series("phillips2012_ctpra_cd")
    ctpr = load_named_series("phillips2012_ctpr_dsc")
    assert {row.doi for row in cortajarena} == {"10.1002/pro.564"}
    assert {row.method for row in cortajarena} == {"DSC"}
    assert all(row.construct.startswith("CTPRa") for row in cortajarena)
    assert {row.method for row in cd} == {"CD"}
    assert all(row.construct.startswith("CTPRa") for row in cd)
    assert {row.construct for row in ctpr} <= {"CTPR2", "CTPR3"}
    assert not any(row.construct.startswith("CTPRa") for row in ctpr)


def test_default_report_carries_phillips_delta_g_without_using_it_as_the_gate():
    from origami.engine import run_design
    from origami.stability.series import delta_g_at_n

    cited = delta_g_at_n("phillips2012_ctpra_dsc", 8)
    assert cited is not None
    report = run_design("dg", 8)
    assert report.stability_state == "pass"
    assert report.delta_g == cited.value
    assert report.delta_g_units == cited.units
    assert report.delta_g_uncertainty == cited.uncertainty
    gap = run_design("dg-gap", 7)
    assert gap.stability_state == "omitted"
    assert gap.delta_g is None
    other = run_design(
        "cortajarena",
        4,
        thermal_series="cortajarena2011_ctpra_dsc",
        t_assay_C=25.0,
    )
    assert other.stability_state == "pass"
    assert other.delta_g is None


def _delta_g_row(n_repeats: int, value: float, units: str = "kcal mol-1") -> ThermalObservation:
    """Fixture row. The number is not a literature free energy."""
    return ThermalObservation(
        record_id=f"fixture-dg-{n_repeats}",
        doi="10.0000/fixture",
        citation="fixture",
        year=2020,
        construct=f"FIX{n_repeats}",
        n_repeats=n_repeats,
        observable="delta_G",
        value=value,
        units=units,
        uncertainty=None,
        method="fixture",
        buffer="fixture",
        pH=None,
        figure_or_table="fixture",
        peer_reviewed=False,
        data_class="synthetic_fixture",
    )


def test_rank_follows_the_larger_printed_value_not_the_longer_scaffold():
    shorter = delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, 3)
    longer = delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, 4)
    assert shorter is not None and longer is not None
    # Table I prints a larger unfolding ΔG at CTPRa3 than at CTPRa4.
    assert shorter.value > longer.value
    ranked = rank_companion_delta_g(PHILLIPS_2012_CTPRA_DSC, [3, 4])
    assert ranked.status == "chosen"
    assert ranked.observation is not None
    assert ranked.observation.n_repeats == shorter.n_repeats
    assert ranked.observation.value == shorter.value


def test_rank_tie_mixed_units_and_unranked_sign_pick_nobody():
    tie = rank_printed_delta_g(
        [_delta_g_row(3, 4.0), _delta_g_row(4, 4.0)],
        [3, 4],
        larger_printed_value_is_more_stable=True,
    )
    assert tie == CitedDeltaGRank(observation=None, status="tie")
    mixed = rank_printed_delta_g(
        [_delta_g_row(3, 4.0, "kcal mol-1"), _delta_g_row(4, 8.0, "kJ mol-1")],
        [3, 4],
        larger_printed_value_is_more_stable=True,
    )
    assert mixed.status == "mixed_units"
    assert mixed.observation is None
    unsigned = rank_printed_delta_g(
        [_delta_g_row(3, -1.0), _delta_g_row(4, -8.0)],
        [3, 4],
        larger_printed_value_is_more_stable=False,
    )
    assert unsigned.status == "not_rankable"
    assert rank_companion_delta_g("cortajarena2011_ctpra_dsc", [2, 4]).status == "no_companion"


def test_ctpr_dsc_companion_is_separate_from_ctpra():
    two = delta_g_at_n("phillips2012_ctpr_dsc", 2)
    three = delta_g_at_n("phillips2012_ctpr_dsc", 3)
    assert two is not None and three is not None
    assert two.construct == "CTPR2"
    assert three.construct == "CTPR3"
    ranked = rank_companion_delta_g("phillips2012_ctpr_dsc", [2, 3])
    assert ranked.observation is not None
    expected = two if two.value > three.value else three
    assert ranked.observation.n_repeats == expected.n_repeats
    assert ranked.observation.value == expected.value
    ctpra = delta_g_at_n(PHILLIPS_2012_CTPRA_DSC, 2)
    assert ctpra is not None
    assert ctpra.construct.startswith("CTPRa")


def test_default_report_names_largest_feasible_delta_g_without_moving_next_n():
    from origami.engine import feasible_repeat_counts, run_design

    library = ClaspDesignEngine().run()
    report = run_design("rank", 8)
    assert library.next_experiment is not None
    assert report.next_n == library.next_experiment.n_repeats
    ranked = rank_companion_delta_g(
        PHILLIPS_2012_CTPRA_DSC,
        feasible_repeat_counts(library),
    )
    assert ranked.status == "chosen"
    assert ranked.observation is not None
    assert report.highest_cited_delta_g_n == ranked.observation.n_repeats
    assert report.highest_cited_delta_g == ranked.observation.value
    assert report.highest_cited_delta_g_units == ranked.observation.units
    assert report.highest_cited_delta_g_uncertainty == ranked.observation.uncertainty
    assert any("does not change next_n" in line for line in report.warnings)

    other = run_design(
        "cortajarena",
        4,
        thermal_series="cortajarena2011_ctpra_dsc",
        t_assay_C=25.0,
    )
    assert other.highest_cited_delta_g_n is None
    skipped = run_design("off", 8, thermal_prior=False)
    assert skipped.highest_cited_delta_g is None
    hot = run_design("hot", 8, t_assay_C=90.0)
    assert hot.next_n is None
    assert hot.highest_cited_delta_g_n is None


def test_caller_supplied_delta_g_rows_are_not_ranked():
    from origami.engine import run_design
    from origami.stability.gate import ThermalRow

    rows = [
        ThermalRow(4, "Tm_C", 80.0, "C", 1.0, "synthetic_fixture"),
        ThermalRow(6, "Tm_C", 90.0, "C", 1.0, "synthetic_fixture"),
        ThermalRow(4, "delta_G", 1.0, "kcal mol-1", 0.1, "synthetic_fixture"),
        ThermalRow(6, "delta_G", 9.0, "kcal mol-1", 0.1, "synthetic_fixture"),
    ]
    report = run_design("caller", 4, thermal_rows=rows, t_assay_C=37.0)
    assert report.delta_g is None
    assert report.highest_cited_delta_g_n is None


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
