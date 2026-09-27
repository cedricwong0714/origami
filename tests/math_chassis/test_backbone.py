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


def test_construct_backbones_are_screw_only() -> None:
    from origami.physical.backbone import backbone_constructs

    bundle = backbone_constructs()
    assert bundle["payloads"] is False
    assert bundle["m13_graft_repeat_index"] is None
    assert bundle["measured_block"] == "CTPR"
    assert [row["n_repeats"] for row in bundle["constructs"]] == [3, 8, 14]
    text = str(bundle)
    assert "p_clash" not in text
    assert "c_eff" not in text
    by_n = {row["n_repeats"]: row for row in bundle["constructs"]}
    assert by_n[3]["end_junction"]["delta_i"] == 2
    assert abs(by_n[3]["end_junction"]["facing_cosine"]) < 1e-9
    assert by_n[8]["end_junction"]["delta_i"] == 7
    assert by_n[14]["end_junction"]["delta_i"] == 13
    assert all(row["rigid_screw"] for row in bundle["constructs"])
    assert all(not site["m13_graft"] for site in by_n[14]["repeats"])
