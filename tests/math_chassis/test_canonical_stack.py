"""Sklearn canonical learner, five wet outputs, and a feasibility-weighted batch.

Synthetic y values. A passing test is not a validated assay.
"""

from __future__ import annotations

from origami.ssdk.learn import SsdkLearnError, learn_ssdk
import pytest


def test_default_learner_is_sklearn_when_a_wet_row_exists():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 12,
            "learner": "sklearn",
            "batch_size": 3,
            "observations": [
                {"n_repeats": 8, "y": 0.4, "source": "surrogate"},
                {"n_repeats": 10, "y": 0.9, "source": "surrogate"},
            ],
        }
    )
    assert report["learner_family"] == "sklearn_matern_residual"
    assert report["canonical"]["fitted"] is True
    assert report["next_n"] not in {8, 10}
    assert report["batch"]["selected"]
    assert len(report["batch"]["selected"]) <= 3
    assert report["multioutput"]["outputs"]["luminescence"]["fitted"] is True
    assert report["multioutput"]["outputs"]["purity"]["fitted"] is False
    assert "purity" in report["multioutput"]["omitted_outputs"]


def test_design_engine_flag_keeps_the_old_family():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 12,
            "learner": "design_engine",
            "observations": [{"n_repeats": 8, "y": 0.4, "source": "surrogate"}],
        }
    )
    assert report["learner_family"] == "design_engine"
    assert report["next_n"] == report["design_engine_next_n"]


def test_no_wet_row_falls_back_and_names_the_family():
    report = learn_ssdk({"n_min": 8, "n_max": 10, "observations": []})
    assert report["learner_family"] == "design_engine_fallback"
    assert report["canonical"]["fitted"] is False
    assert report["multioutput"]["overall_status"] == "NOT_GATED"


def test_locking_row_is_its_own_output_and_does_not_invent_purity():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 11,
            "observations": [
                {"n_repeats": 8, "y": 1.0, "output": "luminescence", "source": "surrogate"},
                {"n_repeats": 8, "y": 0.2, "output": "locking_fraction", "source": "surrogate"},
            ],
        }
    )
    outputs = report["multioutput"]["outputs"]
    assert outputs["locking_fraction"]["fitted"] is True
    assert outputs["solubility"]["fitted"] is False
    assert "mu" not in outputs["solubility"]


def test_unknown_output_is_rejected():
    with pytest.raises(SsdkLearnError):
        learn_ssdk(
            {
                "n_min": 8,
                "n_max": 10,
                "observations": [{"n_repeats": 8, "y": 1.0, "output": "titer", "source": "surrogate"}],
            }
        )
