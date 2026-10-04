"""Length sweep joins the melt curve with the affinity check.

Scientific basis: the sweep does not add an equation. Each point is
the Phillips length model at that n and the Langmuir check at that
local concentration.
Failure mode: a chart that invents a length the single checks do not
reproduce, or that docks a graft index the scaffold does not contain.
"""

import pytest

from origami.api.stability import stability_at_n
from origami.docking.affinity import evaluate_affinity
from origami.docking.sweep import SweepError, sweep_lengths
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN


def test_sweep_matches_the_single_length_checks() -> None:
    report = sweep_lengths(affinity="kd", value=0.19, unit="nM")
    assert report["calibrated"] is False
    assert report["confidence_tier"] == "hypothesis_only"
    ns = [point["n_repeats"] for point in report["points"]]
    assert ns == list(range(N_REPEATS_MIN, N_REPEATS_MAX + 1))
    point = next(item for item in report["points"] if item["n_repeats"] == 8)
    single = evaluate_affinity(8, affinity="kd", value=0.19, unit="nM")
    thermal = stability_at_n(8, report["t_assay_C"])
    assert point["docking_computed"] is True
    assert point["association_theta"] == single["association_theta"]
    assert point["association_holds"] is single["association_holds"]
    assert point["nanobit_theta"] == single["nanobit_theta"]
    assert point["spy_half_life_s"] == single["spy_half_life_s"]
    assert point["p_clash"] == single["p_clash"]
    assert point["tm_C"] == thermal["row"]["tm_C"]
    assert point["delta_g"] == thermal["row"]["delta_g"]


def test_graft_outside_the_scaffold_skips_docking_and_keeps_the_melt() -> None:
    report = sweep_lengths(affinity="kd", value=0.19, unit="nM", graft_index=10)
    short = next(item for item in report["points"] if item["n_repeats"] == 8)
    long = next(item for item in report["points"] if item["n_repeats"] == 14)
    thermal = stability_at_n(8, report["t_assay_C"])
    assert short["docking_computed"] is False
    assert short["call"] == "docking_skipped"
    assert short["association_theta"] is None
    assert short["tm_C"] == thermal["row"]["tm_C"]
    assert long["docking_computed"] is True
    assert long["indices"] == [0, 10]


def test_marked_length_is_the_highest_occupancy_among_held_folds() -> None:
    """The mark is max reporter occupancy among melt-pass and held lengths.

    A tie takes the shorter scaffold. The mark is not a validated optimum.
    """
    report = sweep_lengths(affinity="kd", value=0.19, unit="nM")
    eligible = [
        point
        for point in report["points"]
        if point["thermal_state"] == "pass"
        and point["association_holds"] is True
        and isinstance(point["nanobit_theta"], float)
    ]
    if report["marked_n"] is None:
        assert eligible == []
        return
    marked = next(point for point in report["points"] if point["n_repeats"] == report["marked_n"])
    best = max(point["nanobit_theta"] for point in eligible)
    tied = [point["n_repeats"] for point in eligible if point["nanobit_theta"] == best]
    assert marked["nanobit_theta"] == best
    assert marked["n_repeats"] == min(tied)
    assert report["ranking_rule"].endswith("It is not a validated optimum.")
    assert report["calibrated"] is False


def test_graft_index_zero_is_rejected() -> None:
    with pytest.raises(SweepError, match="graft_index"):
        sweep_lengths(affinity="kd", value=0.19, unit="nM", graft_index=0)
