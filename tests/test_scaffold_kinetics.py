"""Scaffold kinetics must change with screw length.

Scientific basis: Gaussian-chain C_eff falls as the docking-site chord
grows, and Langmuir occupancy and the tethered half-life are functions
of that concentration.
Failure mode: every repeat count returns the same literature Kd or rate.
"""

import math

from origami.dry_lab_md import TEAM_KLOCK
from origami.kinetics.scaffold_sweep import scaffold_kinetic_sweep
from origami.priors import SPY_K_ON_PER_M_S


def test_occupancy_and_half_life_change_with_length():
    sweep = scaffold_kinetic_sweep()
    by_n = {row["n_repeats"]: row for row in sweep["rows"]}
    short = by_n[3]
    long = by_n[14]
    assert short["chord_A"] < long["chord_A"]
    assert short["c_eff_M"] > long["c_eff_M"]
    assert short["theta_cam"] > long["theta_cam"]
    assert short["t_half_team_s"] < long["t_half_team_s"]
    assert sweep["calibrated"] is False


def test_team_and_literature_half_lives_differ_only_by_rate():
    row = next(item for item in scaffold_kinetic_sweep()["rows"] if item["n_repeats"] == 8)
    ratio = row["t_half_team_s"] / row["t_half_literature_s"]
    assert math.isclose(ratio, SPY_K_ON_PER_M_S.value / TEAM_KLOCK.value, rel_tol=1e-9)


def test_nanobit_curves_use_the_two_dissociation_constants_separately():
    row = next(item for item in scaffold_kinetic_sweep()["rows"] if item["n_repeats"] == 8)
    assert row["theta_nanobit_kinetic"] != row["theta_nanobit_printed"]
    assert 0.0 <= row["theta_nanobit_printed"] <= 1.0
    assert 0.0 <= row["theta_cam"] <= 1.0
