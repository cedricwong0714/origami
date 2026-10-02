"""Numeric golden baselines for Stream 1 engines.

These fixtures lock the current numeric outputs of the ODE solver and the
calcium-kinetics engine so that Phases 1-5 (provenance refactor, geometric
uncertainty, solver rigor) cannot silently change model behaviour.

Regeneration policy (AGENTS.md golden tests): if a fixture is missing the test
writes it and skips; if it exists the test asserts exact (within-tolerance)
equality. Update a fixture only with a documented reason in the commit message.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from src.core.asset_paths import GOLDEN_DIR
from src.core.calcium_kinetics import CAM_M13_KD_CA_SAT_M, recruitment_occupancy
from src.core.schema import MechanismType
from src.ode_model.solver import run_system_simulation

NUMERIC_GOLDEN = GOLDEN_DIR / "numeric_baseline.json"


def _current_numeric_snapshot() -> dict:
    """Compute the current deterministic numeric outputs to be frozen."""
    # Intermediate-transfer ODE product trajectory (fixed grid, fixed params).
    t, concs = run_system_simulation(
        {"S": 1.0, "E": 0.1, "E2": 0.1, "ES": 0.0, "P": 0.0},
        time_span=(0.0, 100.0),
        mechanism_type=MechanismType.INTERMEDIATE_TRANSFER,
        num_points=11,
    )
    # Calcium recruitment occupancy across a fixed Ca2+ dose-response.
    ca2_grid = np.logspace(-9, -4, 9)
    occupancy = [
        recruitment_occupancy(float(c)).occupancy_fraction for c in ca2_grid
    ]
    return {
        "golden_id": "numeric_baseline",
        "version": "1.0.0",
        "synthetic_fixture": True,
        "description": (
            "Numeric baseline locking intermediate_transfer ODE and "
            "calcium recruitment outputs before Stream 1 rigor refactors."
        ),
        "intermediate_transfer": {
            "time": [float(x) for x in t],
            "product": [float(x) for x in np.asarray(concs["P"])],
        },
        "calcium_occupancy": {
            "ca2_grid_M": [float(x) for x in ca2_grid],
            "occupancy_fraction": [float(x) for x in occupancy],
        },
    }


def test_numeric_baseline_locked():
    current = _current_numeric_snapshot()
    if not NUMERIC_GOLDEN.is_file():
        NUMERIC_GOLDEN.write_text(json.dumps(current, indent=2), encoding="utf-8")
        pytest.skip(
            f"Numeric golden created at {NUMERIC_GOLDEN}. Re-run to verify."
        )

    golden = json.loads(NUMERIC_GOLDEN.read_text(encoding="utf-8"))
    assert golden["calcium_kd_M"] == CAM_M13_KD_CA_SAT_M, (
        "The occupancy golden is locked to CAM_M13_KD_CA_SAT_M. "
        "If that peptide Kd changes, update numeric_baseline.json and "
        "document the source in CHANGELOG.md."
    )

    np.testing.assert_allclose(
        current["intermediate_transfer"]["product"],
        golden["intermediate_transfer"]["product"],
        rtol=1e-6,
        atol=1e-9,
        err_msg=(
            "intermediate_transfer ODE product changed. If intentional, update "
            "tests/golden_references/numeric_baseline.json and document why."
        ),
    )
    np.testing.assert_allclose(
        current["calcium_occupancy"]["occupancy_fraction"],
        golden["calcium_occupancy"]["occupancy_fraction"],
        rtol=1e-6,
        atol=1e-9,
        err_msg=(
            "calcium recruitment occupancy changed. If intentional, update "
            "tests/golden_references/numeric_baseline.json and document why."
        ),
    )
