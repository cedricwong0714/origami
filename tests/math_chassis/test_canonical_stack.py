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


def test_sequence_uses_composition_and_esm_falls_back_without_torch():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 10,
            "sequence": "ACDE",
            "sequence_encoding": "esm2",
            "observations": [{"n_repeats": 8, "y": 0.5, "source": "surrogate"}],
        }
    )
    assert report["canonical"]["sequence_encoding"] == "onehot"
    plain = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 10,
            "sequence": "AAAA",
            "observations": [{"n_repeats": 8, "y": 0.5, "source": "surrogate"}],
        }
    )
    assert plain["canonical"]["sequence_encoding"] == "composition"


def test_scatter_model_does_not_replace_the_assay_cv():
    from pathlib import Path

    cfg = Path("data/config/active_learning_config.json").read_text()
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 14,
            "observations": [
                {"n_repeats": n, "y": 0.2 * n, "source": "surrogate"} for n in (8, 10, 12, 14)
            ],
        }
    )
    scatter = report["canonical"]["heteroscedastic"]
    assert scatter["fitted"] is True
    assert scatter["replaces_assay_cv"] is False
    assert report["canonical"]["used_heteroscedastic_std"] is False
    assert Path("data/config/active_learning_config.json").read_text() == cfg
    short = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 11,
            "observations": [{"n_repeats": 8, "y": 0.4, "source": "surrogate"}],
        }
    )
    assert short["canonical"]["heteroscedastic"]["fitted"] is False


def test_purity_miss_cuts_the_batch_weight():
    from origami.ssdk.batch_acquire import _penalty

    assert _penalty({"outputs": {}}, 8) == 1.0
    missed = {
        "outputs": {
            "purity": {
                "fitted": True,
                "rows": [{"n_repeats": 8, "passes": False}],
            }
        }
    }
    assert _penalty(missed, 8) == 0.25
    assert _penalty(missed, 9) == 1.0


def test_learn_ssdk_cli_prints_the_family():
    import json
    import subprocess
    import sys

    body = json.dumps(
        {
            "n_min": 8,
            "n_max": 10,
            "observations": [],
        }
    )
    proc = subprocess.run(
        [sys.executable, "-m", "src.ui.cli", "learn-ssdk", "--json-body", body],
        check=False,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "primary_family: design_engine_fallback" in proc.stdout
    assert "feature_matrix_sha256:" in proc.stdout
    assert "chassis_n:" in proc.stdout
    assert "chassis_kinetics_computable: False" in proc.stdout
    assert "calibrated: false" in proc.stdout


def test_bad_sequence_is_rejected():
    with pytest.raises(SsdkLearnError):
        learn_ssdk(
            {
                "n_min": 8,
                "n_max": 10,
                "sequence": "ACDX",
                "observations": [{"n_repeats": 8, "y": 0.2, "source": "surrogate"}],
            }
        )
