"""Multi-fidelity luminescence on /api/ssdk/learn (synthetic y, not validation)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from origami.api.structural import app
from origami.ssdk.learn import learn_ssdk

client = TestClient(app)


def test_learn_includes_multifidelity_section_without_wet():
    report = learn_ssdk({"n_min": 8, "n_max": 10, "observations": []})
    mf = report["multifidelity_luminescence"]
    assert mf["fitted"] is False
    assert mf["calibrated"] is False
    assert len(mf["candidates"]) == 3
    assert mf["threshold_luminescence"]["status"] == "unmeasured"


def test_wet_observations_fit_multifidelity_gp():
    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 12,
            "observations": [
                {"n_repeats": 8, "y": 0.5, "fidelity": 1, "source": "surrogate"},
                {"n_repeats": 10, "y": 0.7, "fidelity": 1, "source": "surrogate"},
            ],
        }
    )
    mf = report["multifidelity_luminescence"]
    assert mf["fitted"] is True
    assert mf["gp_hyperparameters"] is not None
    assert mf["recommended_evaluation"]["evaluation_type"] == "wet_NanoBiT"
    by_n = {r["n_repeats"]: r for r in mf["candidates"]}
    assert by_n[8]["mu_luminescence"] == pytest.approx(0.5, abs=0.25)


def test_three_gps_share_one_feature_matrix():
    """Linker flags and sequence columns are the same array for every GP.

    A zero linker RMS is the old multi-fidelity default. The shared row
    must not collapse to that when the construct asks for 20 residues.
    """
    from origami.ssdk.canonical_learner import construct_flags

    report = learn_ssdk(
        {
            "n_min": 8,
            "n_max": 10,
            "construct": {
                "linker_residues": 20,
                "cam_on_scaffold": True,
                "m13_on_scaffold": True,
            },
            "sequence": "ACDE",
            "sequence_encoding": "composition",
            "observations": [
                {"n_repeats": 8, "y": 0.4, "source": "surrogate"},
                {
                    "n_repeats": 8,
                    "y": 0.2,
                    "output": "locking_fraction",
                    "source": "surrogate",
                },
            ],
        }
    )
    digest = report["canonical"]["feature_matrix_sha256"]
    assert digest == report["multioutput"]["feature_matrix_sha256"]
    assert digest == report["multifidelity_luminescence"]["feature_matrix_sha256"]
    assert report["canonical"]["sequence_encoding"] == "composition"
    assert report["multioutput"]["sequence_encoding"] == "composition"
    assert report["multifidelity_luminescence"]["sequence_encoding"] == "composition"
    assert report["multifidelity_luminescence"]["linker_rms_A"] == pytest.approx(
        construct_flags({"linker_residues": 20})["linker_rms_A"]
    )
    assert report["multifidelity_luminescence"]["linker_rms_A"] != pytest.approx(0.0)
    # The locking row is its own assay. It is not a second luminescence point.
    assert report["multioutput"]["outputs"]["locking_fraction"]["fitted"] is True
    assert report["multifidelity_luminescence"]["fitted"] is True


def test_api_learn_multifidelity():
    response = client.post(
        "/api/ssdk/learn",
        json={
            "n_min": 8,
            "n_max": 11,
            "observations": [{"n_repeats": 9, "y": 1.2, "fidelity": 1, "source": "plate"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["multifidelity_luminescence"]["fitted"] is True
