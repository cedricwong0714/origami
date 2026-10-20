"""Dry-lab length posterior must move the locking calculation off the screw.

Scientific basis: the Gaussian chain local concentration depends on
separation, and the team's SpyTag–SpyCatcher rate is the wet-lab fit
printed in the wiki, not the Zakeri-page comparison rate.
Failure mode: a posterior that still reports the crystal-screw distance
or the literature on-rate after the MD table and the team fit are loaded.
"""

import math

from origami.dry_lab_md import (
    CALCIUM_HILL_ASSAY,
    EXCLUDED_LITERATURE_KD_NOTE,
    LITERATURE_SPY_KON,
    TEAM_KLOCK,
)
from origami.learned_kinetics import condition_on_length_posterior, explain_shift
from sandbox.active_learning_view import run_active_learning_sandbox


def _library():
    view = run_active_learning_sandbox(n_min=3, n_max=24, load_demo=True)
    assert view.conditioned is not None
    return view


def test_posterior_stays_with_md_lengths_not_the_screw():
    """
    The MD end-to-end values disagree with the crystal screw.
    Scientific basis: a residual GP conditioned on observations must
    move toward those observations.
    Failure mode: the reported length is still the screw chord.
    """
    view = _library()
    by_n = {row.n_repeats: row for row in view.conditioned.rows}
    for obs in view.result.observations:
        row = by_n[obs.n_repeats]
        distance_to_data = abs(row.posterior_mean_A - obs.y)
        distance_to_screw = abs(row.posterior_mean_A - row.literature_chord_A)
        assert distance_to_data < 2.0
        assert distance_to_data < distance_to_screw
        assert abs(row.literature_chord_A - obs.y) > 10.0


def test_local_concentration_ranking_changes_once_md_distance_is_used():
    """
    The screw makes short scaffolds much more concentrated than long ones.
    The MD end-to-end column does not.
    Scientific basis: C_eff falls as exp(-3 r^2 / 2 σ^2).
    Failure mode: the posterior concentration still tracks the screw.
    """
    view = _library()
    by_n = {row.n_repeats: row for row in view.conditioned.rows}
    literature_ratio = by_n[3].ceff_literature_M / by_n[14].ceff_literature_M
    posterior_ratio = by_n[3].ceff_posterior_M / by_n[14].ceff_posterior_M
    assert literature_ratio > 1e3
    assert posterior_ratio < 20.0
    assert view.conditioned.literature_best_n <= 5
    assert view.conditioned.literature_best_n != view.result.next_experiment.n_repeats


def test_half_life_uses_team_rate_and_keeps_the_literature_rate_visible():
    """
    At one posterior distance, the two half-lives differ only by the rate.
    Scientific basis: t_1/2 = ln 2 / (k C_eff).
    Failure mode: the team column silently uses 1.4e3, or the comparison
    column is dropped.
    """
    view = _library()
    row = next(item for item in view.conditioned.rows if item.n_repeats == 8)
    assert row.half_life_team_s is not None
    assert row.half_life_distance_only_s is not None
    ratio = row.half_life_team_s / row.half_life_distance_only_s
    assert math.isclose(ratio, LITERATURE_SPY_KON.value / TEAM_KLOCK.value, rel_tol=1e-9)
    assert TEAM_KLOCK.value == 249.4
    assert TEAM_KLOCK.provenance == "wet_lab"
    assert LITERATURE_SPY_KON.value == 1.4e3
    lo, hi = row.half_life_corner_bounds_s
    assert lo <= row.half_life_team_s <= hi
    assert lo < hi


def test_unmeasured_dissociation_constants_and_hill_fit_are_not_training_rows():
    """
    Wiki section 6 says the nanomolar Kd table was not measured by the team.
    The Hill fit is one construct.
    Failure mode: those numbers are loaded as if they were length-indexed data.
    """
    view = _library()
    values = [obs.y for obs in view.result.observations]
    assert 10.0 not in values
    assert 30.0 not in values
    assert 28.0 not in values
    assert CALCIUM_HILL_ASSAY.ec50_uM not in values
    assert all(obs.units == "Å" for obs in view.result.observations)
    assert "did not measure" in EXCLUDED_LITERATURE_KD_NOTE
    text = explain_shift(view.conditioned, view.result.next_experiment.n_repeats)
    assert "10 nM" in text
    assert "249.4" in text
    assert f"n={view.conditioned.literature_best_n}" in text


def test_relative_output_is_not_read_as_a_length():
    from origami.engine import Observation

    view = run_active_learning_sandbox(
        load_demo=False,
        extra_observations=[Observation(n_repeats=6, y=0.4, source="user_entered")],
    )
    assert view.conditioned is None
    assert "crystal-screw end-to-end" not in [trace.name for trace in view.figure.data]


def test_length_figure_shows_screw_and_posterior_concentration():
    view = _library()
    names = [trace.name for trace in view.figure.data]
    assert "crystal-screw end-to-end" in names
    assert "AMBER MD end-to-end" in names
    assert "MD posterior local concentration" in names
    assert "crystal-screw local concentration" in names
    marked = [row for row in view.library_rows if row["literature_best"]]
    assert len(marked) == 1
    assert marked[0]["n"] == view.conditioned.literature_best_n
