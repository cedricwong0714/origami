"""Team lengths stay labeled as choices. The scan is allowed to disagree.

Fixture clash probabilities below are not measurements.
"""

from origami.physical.registers import TEAM_CHANNELING_N, use_case_register


def _row(n: int, end_pair: float, thermal_state: str = "pass") -> dict:
    return {
        "n": n,
        "end_pair_p_clash": end_pair,
        "p_instability": end_pair,
        "thermal_state": thermal_state,
    }


def test_channeling_candidate_is_not_the_minimum_when_an_earlier_length_clears():
    rows = [_row(n, 0.9 if n < 4 else 0.1) for n in range(3, 16)]
    register = use_case_register(
        rows,
        active_next_n=3,
        clash_limit=0.85,
        measured_n={2, 3, 4, 5, 6, 8, 10},
        library_min=3,
        one_turn_n=8,
    )
    assert register["calibrated"] is False
    assert register["lower_extrema_n"] == 2
    assert register["upper_extrema_n"] == 20
    assert register["biomarker_n"] == 3
    assert register["channeling_candidate_n"] == TEAM_CHANNELING_N
    assert register["shortest_end_pair_n"] == 4
    assert register["channeling_candidate_is_steric_minimum"] is False
    assert register["active_learner_next_n"] == 3
    assert register["lower_bound_in_phillips2012_ctpra_dsc"] is True
    assert register["upper_bound_in_phillips2012_ctpra_dsc"] is False
    assert register["channeling_candidate_in_phillips2012_ctpra_dsc"] is False
    assert register["biomarker_n_is_library_minimum"] is True
    assert register["one_turn_n"] == 8


def test_flag_is_true_only_when_the_scan_first_clears_at_the_candidate():
    rows = [_row(n, 0.95 if n < TEAM_CHANNELING_N else 0.2) for n in range(3, 21)]
    register = use_case_register(
        rows,
        active_next_n=8,
        clash_limit=0.85,
        measured_n={2, 3, 4, 5, 6, 8, 10},
        library_min=3,
        one_turn_n=8,
    )
    assert register["shortest_end_pair_n"] == TEAM_CHANNELING_N
    assert register["channeling_candidate_is_steric_minimum"] is True
    assert register["active_learner_next_n"] == 8


def test_default_run_keeps_fourteen_out_of_the_acquisition():
    """The Phillips series stops at n=10. n=14 is extrapolated, and the
    end-pair clash on the canonical screw is already low before n=14.
    The untrained acquisition is reported beside that fact and is not
    trained toward 14.
    """
    from origami.engine import run_design

    report = run_design("register", 8)
    registers = report.registers
    assert registers is not None
    assert registers["calibrated"] is False
    assert registers["channeling_candidate_is_steric_minimum"] is False
    assert registers["shortest_end_pair_n"] != 14
    assert registers["active_learner_next_n"] == report.next_n
    by_n = {row["n"]: row for row in registers["end_pairs"]}
    assert by_n[14]["thermal_state"] == "extrapolated"
    assert by_n[3]["thermal_state"] == "pass"
    assert 2 not in by_n
    assert registers["one_turn_n"] == 8
    assert report.calibrated is False
