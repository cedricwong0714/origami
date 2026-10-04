"""Modelling sandbox wrappers call the live chassis and do not invent radii."""

from __future__ import annotations

from sandbox.modelling_service import length_series, run_binding, score_length, suggest_next_length


def test_score_length_omits_clash_without_radii() -> None:
    report = score_length(8)
    assert report["n_repeats"] == 8
    assert report["calibrated"] is False
    assert report["docking"]["clash_computable"] is False
    assert report["docking"]["indices"] == [0, 3]


def test_length_series_covers_planned_n() -> None:
    rows = length_series(3, 14)
    by_n = {row["n_repeats"]: row for row in rows}
    assert set(by_n) == set(range(3, 15))
    assert by_n[8]["tm_C"] is not None
    assert by_n[8]["clash_computable"] is False
    assert by_n[14]["past_longest_cited_length"] is True


def test_bound_fraction_uses_peptide_kd() -> None:
    result = run_binding("recruitment_steady", c_free_M=1e-8)
    rec = result["recruitment"]
    assert rec["kd_M"] == 0.19e-9
    assert rec["theta_ss"] == 1e-8 / (1e-8 + 0.19e-9)


def test_next_length_runs_without_readings() -> None:
    report = suggest_next_length(3, 8, observations=[])
    assert report["calibrated"] is False
    assert 3 <= report["next_n"] <= 8
