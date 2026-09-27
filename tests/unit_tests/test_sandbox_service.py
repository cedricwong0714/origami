"""Sandbox service wraps run_design and does not mark the report calibrated."""

from __future__ import annotations

import pytest

from origami.priors import N_REPEATS_MAX, N_REPEATS_MIN
from sandbox.service import run_sandbox


def test_default_probe_stays_uncalibrated() -> None:
    bundle = run_sandbox({"design_id": "sandbox-probe", "n_repeats": 8})
    assert bundle["result"]["calibrated"] is False
    assert bundle["result"]["n_repeats"] == 8
    assert bundle["input"]["payload_count"] == 0
    assert bundle["input"]["thermal_prior"] is True
    assert len(bundle["process"]["steps"]) >= 6
    assert bundle["library"]["n_repeats"][0] == N_REPEATS_MIN
    assert bundle["library"]["n_repeats"][-1] == N_REPEATS_MAX
    assert len(bundle["library"]["gp_mean"]) == len(bundle["library"]["n_repeats"])
    assert bundle["result"]["separation"]["gp_fitted"] is False
    assert bundle["confirmation"]["calibrated"] is False
    assert len(bundle["confirmation"]["rows"]) == 22
    assert bundle["scene"]["ca_count"] == 8 * 34
    assert bundle["drylab"]["calibrated"] is False
    assert bundle["drylab"]["gp_fitted"] is False
    assert bundle["drylab"]["active_learning"]["gp_fitted"] is False
    assert len(bundle["drylab"]["stability_panel"]) == 4 * 22


def test_rejects_empty_design_id() -> None:
    with pytest.raises(ValueError, match="design_id"):
        run_sandbox({"design_id": "  ", "n_repeats": 8})


def test_rejects_n_outside_library() -> None:
    with pytest.raises(ValueError, match="n_repeats"):
        run_sandbox({"design_id": "x", "n_repeats": 2})


def test_payload_rows_are_checked() -> None:
    with pytest.raises(ValueError, match="repeat_index"):
        run_sandbox(
            {
                "design_id": "x",
                "n_repeats": 3,
                "payloads": [
                    {
                        "payload_id": "a",
                        "role": "enzyme",
                        "fusion_terminus": "C",
                        "repeat_index": 3,
                        "radius_A": 20.0,
                        "linker_sigma_A": 12.0,
                    },
                    {
                        "payload_id": "b",
                        "role": "enzyme",
                        "fusion_terminus": "N",
                        "repeat_index": 0,
                        "radius_A": 20.0,
                        "linker_sigma_A": 12.0,
                    },
                ],
            }
        )
