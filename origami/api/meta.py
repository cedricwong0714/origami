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
            "CTPR screw from published crystals (PDB 2AVP, 2HYZ, 2FO7)",
            "Melting temperature and unfolding energy from Phillips 2012",
            "Docking distance. Clash only if you type two radii",
            "Bound fraction (peptide Kd 0.19 nM), Spy lock (Zakeri 2012), LgBiT–SmBiT (Dixon 2016)",
            "Next-length suggestion. A pass uses a cutoff that is not measured yet",
            "Plate file: blanks subtracted per batch",
        ],
        "needs_lab_data": [
            "Concentration, gels, calcium curve, Spy lock time course, four-tube bridge",
            "Day-to-day variation, linearity, negative controls",
            "Measured pass cutoffs and assay variation",
        ],
        "team_dry_lab": [
            "Saved predictions for n = 3, 8, and 14. The luminescence band is still a ±30% placeholder",
            "Group labels if you run the optional comparison",
            "Replace the placeholder assay variation when you have repeat measurements",
        ],
        "out_of_scope": [
            "Circular dichroism, thermal shift, size-exclusion chromatography, cryo-EM",
            "OtsA/OtsB enzyme assays",
            "n = 17 is computable if you type it. It is not one of the planned lengths",
        ],
    }
