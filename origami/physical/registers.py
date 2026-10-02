"""Team repeat-count register, checked against the scan already run.

n = 2 and n = 20 are the bounds the team stated. n = 3 is the biomarker
measurement length. n = 14 is the channeling length the team asked to
check. None of these four numbers is produced by the acquisition
function. The function below only reports whether the steric scan and
the thermal gate agree with them.

No observation is added here. The active learner is not trained.
"""

from __future__ import annotations

# Team choices. Not melting temperatures, not a fitted optimum.
TEAM_LOWER_N = 2
TEAM_UPPER_N = 20
TEAM_BIOMARKER_N = 3
TEAM_ONE_TURN_N = 8
TEAM_CHANNELING_N = 14

TEAM_GEOMETRY_SERIES = (8, 14)
TEAM_CANONICAL_LENGTHS = (3, 8, 14)

CANONICAL_LENGTH_ROLES = {
    TEAM_LOWER_N: "Lower screening bound",
    TEAM_BIOMARKER_N: "Biomarker POC baseline (compact sub-turn construct)",
    TEAM_ONE_TURN_N: "One complete superhelical turn (8 repeats * 45° = 360°)",
    TEAM_CHANNELING_N: "Model-predicted optimum for intermediate transfer channeling",
    TEAM_UPPER_N: "Upper screening bound",
}

REGISTER_KEYS = frozenset(
    {
        "calibrated",
        "lower_extrema_n",
        "upper_extrema_n",
        "biomarker_n",
        "channeling_candidate_n",
        "one_turn_n",
        "lower_bound_in_phillips2012_ctpra_dsc",
        "upper_bound_in_phillips2012_ctpra_dsc",
        "channeling_candidate_in_phillips2012_ctpra_dsc",
        "biomarker_n_is_library_minimum",
        "shortest_end_pair_n",
        "channeling_candidate_is_steric_minimum",
        "active_learner_next_n",
        "end_pairs",
        "notes",
    }
)


def use_case_register(
    rows: list[dict[str, object]],
    *,
    active_next_n: int | None,
    clash_limit: float,
    measured_n: set[int],
    library_min: int,
    one_turn_n: int | None,
) -> dict[str, object]:
    """Compare the team lengths with one finished scan.

    ``rows`` are the candidate lengths the engine already scored. Each
    row needs ``n``, ``end_pair_p_clash``, ``p_instability``, and
    ``thermal_state``. ``thermal_state`` is ``not_scored`` when the
    thermal gate was off. This function does not rescore geometry.
    """
    if clash_limit <= 0.0 or clash_limit > 1.0:
        raise ValueError("clash_limit must be in (0, 1]")
    ordered = sorted(rows, key=lambda row: int(row["n"]))
    shortest: int | None = None
    end_pairs: list[dict[str, object]] = []
    for row in ordered:
        n_repeats = int(row["n"])
        end_pair = float(row["end_pair_p_clash"])
        thermal_state = str(row["thermal_state"])
        end_pairs.append(
            {
                "n": n_repeats,
                "end_pair_p_clash": end_pair,
                "p_instability": float(row["p_instability"]),
                "thermal_state": thermal_state,
            }
        )
        if shortest is None and end_pair < clash_limit:
            shortest = n_repeats

    notes = [
        "n=2 and n=20 are the team bounds. They are not optima.",
        "n=3 is the biomarker measurement length, chosen next to the lower bound.",
        (
            "n=14 is the team channeling candidate. "
            "shortest_end_pair_n is the first scanned length whose end-pair "
            "clash probability is below the same limit recommend() uses. "
            "Those two numbers are equal only when the scan says so."
        ),
        (
            "active_learner_next_n is the untrained acquisition on this scan. "
            "No observation was added to force a repeat count."
        ),
    ]
    if TEAM_CHANNELING_N not in measured_n:
        notes.append(
            "n=14 is not a measured row in the default Phillips CTPRa DSC "
            "series. The thermal gate marks it extrapolated, so the "
            "acquisition does not rank it while that prior is on."
        )
    if not (TEAM_UPPER_N in measured_n):
        notes.append(
            "n=20 is the team upper bound. It is not a measured melting "
            "temperature in the default series, and it is not a solubility limit."
        )

    return {
        "calibrated": False,
        "lower_extrema_n": TEAM_LOWER_N,
        "upper_extrema_n": TEAM_UPPER_N,
        "biomarker_n": TEAM_BIOMARKER_N,
        "channeling_candidate_n": TEAM_CHANNELING_N,
        "one_turn_n": one_turn_n,
        "lower_bound_in_phillips2012_ctpra_dsc": TEAM_LOWER_N in measured_n,
        "upper_bound_in_phillips2012_ctpra_dsc": TEAM_UPPER_N in measured_n,
        "channeling_candidate_in_phillips2012_ctpra_dsc": TEAM_CHANNELING_N in measured_n,
        "biomarker_n_is_library_minimum": TEAM_BIOMARKER_N == library_min,
        "shortest_end_pair_n": shortest,
        "channeling_candidate_is_steric_minimum": shortest == TEAM_CHANNELING_N,
        "active_learner_next_n": active_next_n,
        "end_pairs": end_pairs,
        "notes": notes,
    }
