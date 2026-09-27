"""Exported structural and thermal rows match the models already in the engine.

Scientific basis: contour = n * rise; rigid when contour <= persistence length.
Phillips 2012 CTPRa DSC has no row at n=14, so that length stays extrapolated.
Failure mode: a confirmation export that fills Tm(n) or marks calibrated.
"""

from __future__ import annotations

from origami.confirmations import confirm_library, geometry_scene
from origami.priors import LINKER_SIGMA_A, N_REPEATS_MAX, N_REPEATS_MIN
from origami.stability.series import DEFAULT_OPERATING_TEMPERATURE_C


def test_library_covers_every_candidate_and_stays_uncalibrated() -> None:
    bundle = confirm_library(thermal_prior=True, t_assay_C=DEFAULT_OPERATING_TEMPERATURE_C)
    rows = bundle["rows"]
    assert bundle["calibrated"] is False
    assert [row["n_repeats"] for row in rows] == list(range(N_REPEATS_MIN, N_REPEATS_MAX + 1))
    by_n = {row["n_repeats"]: row for row in rows}
    assert by_n[8]["thermal_state"] == "pass"
    assert by_n[8]["tm_C"] is not None
    assert by_n[8]["rigid_screw"] is True
    assert by_n[14]["thermal_state"] == "extrapolated"
    assert by_n[14]["tm_C"] is None
    assert by_n[14]["delta_g"] is None
    assert by_n[16]["rigid_screw"] is True
    assert by_n[18]["rigid_screw"] is False
    assert by_n[8]["repeats_per_turn"] == 8.0
    assert bundle["linker_sigma_A"] == LINKER_SIGMA_A.value


def test_scene_places_one_consensus_repeat_per_step() -> None:
    scene = geometry_scene(
        8,
        [0, 7],
        [25.0, 25.0],
        [LINKER_SIGMA_A.value, LINKER_SIGMA_A.value],
    )
    assert scene["ca_count"] == 8 * 34
    assert len(scene["ca_A"]) == 8 * 34
    assert len(scene["sites_A"]) == 8
    assert len(scene["payloads"]) == 2
    assert scene["payloads"][0]["repeat_index"] == 0
    assert scene["payloads"][1]["repeat_index"] == 7
    assert scene["method"] == "delta_method_ca_envelope"
