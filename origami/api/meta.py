"""Read-only project metadata for the wiki UI."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from src.experiment_design.frozen_table import load_config, unmeasured_items

router = APIRouter()


@router.get("/api/meta/active-learning-config")
def active_learning_config() -> dict[str, Any]:
    cfg = load_config()
    return {
        "config": cfg,
        "placeholders_unmeasured": unmeasured_items(cfg),
        "calibrated": False,
    }


@router.get("/api/meta/dependencies")
def dependency_summary() -> dict[str, Any]:
    """Structured summary aligned with docs/DATA_DEPENDENCY_MATRIX.md."""
    return {
        "version": "2026-10-02",
        "calibrated": False,
        "no_lab_data": [
            "CTPR screw vs deposited PDB",
            "Phillips/Cortajarena stability tables and calculator",
            "Docking clash with CaM-M13 default payload",
            "Kinetics priors (peptide Kd, Spy rate, fusion Kd secondhand, assumed kon)",
            "Multi-fidelity luminescence on POST /api/ssdk/learn",
            "Plate CSV intake, ablation, cost-aware ranking",
        ],
        "needs_lab_data": [
            "BCA, gels, calcium dose-response, lock kinetics, bridging tubes",
            "Phase 3 quality slots (inter-day CV, linearity, negative panel, irreversibility)",
            "Measured thresholds and CVs in active_learning_config.json",
        ],
        "team_dry_lab": [
            "origami freeze for n=3,8,14 with pass/fail rules",
            "Group labels for ablation",
            "Replace placeholder assay CVs when inter-day data exist",
        ],
        "out_of_scope": [
            "CD, thermal shift, SEC, cryo-EM",
            "OtsA/OtsB wet-lab enzyme assays",
            "n=17 as calibrated point (any n user enters is computable)",
        ],
    }
