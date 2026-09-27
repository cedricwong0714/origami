"""Backbone rows do not mention payloads and follow contour = n * rise."""

from __future__ import annotations

from origami.physical.backbone import backbone_library
from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN


def test_backbone_has_no_payload_fields() -> None:
    bundle = backbone_library()
    assert bundle["payloads"] is False
    assert bundle["calibrated"] is False
    assert [row["n_repeats"] for row in bundle["by_n"]] == list(
        range(N_REPEATS_MIN, N_REPEATS_MAX + 1)
    )
    by_n = {row["n_repeats"]: row for row in bundle["by_n"]}
    rise = bundle["screw"]["rise_A"]
    assert by_n[8]["contour_A"] == rise * 8
    assert by_n[16]["rigid_screw"] is True
    assert by_n[18]["rigid_screw"] is False
    assert "c_eff" not in str(bundle["by_n"][0]).lower()
    assert "p_clash" not in str(bundle["by_n"][0]).lower()
    facing = {row["delta_i"]: row for row in bundle["junction_from_repeat_0"]}
    assert facing[4]["facing_cosine"] == -1.0
    assert abs(facing[8]["facing_cosine"] - 1.0) < 1e-9
