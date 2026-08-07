"""Export helpers for Design Mode outputs (wiki / judging artifacts)."""

from __future__ import annotations

import json
from typing import Any, Optional

from src.core.schema import DesignSpec, MechanismType
from src.scaffold_optimizer import InteractionClass


def interaction_class_to_mechanism(interaction: InteractionClass) -> MechanismType:
    """Map optimizer interaction class to a mechanism profile (heuristic)."""
    mapping = {
        InteractionClass.METABOLIC: MechanismType.INTERMEDIATE_TRANSFER,
        InteractionClass.BINDING: MechanismType.TARGET_COMPLEMENTATION,
        InteractionClass.KINASE: MechanismType.INTERMEDIATE_TRANSFER,
        InteractionClass.ELECTRON: MechanismType.REDOX_TRANSFER,
    }
    return mapping[interaction]


def passport_json_bytes(result: dict[str, Any]) -> bytes:
    """Serialize passport + key design metadata for download."""
    payload = {
        "design_id": result.get("design_id"),
        "status": result.get("status"),
        "passport": result.get("passport"),
        "prediction": result.get("prediction"),
        "geometry_summary": _geometry_summary(result.get("geometry")),
        "errors": result.get("errors"),
        "warnings": result.get("warnings"),
        "export_note": (
            "Software-generated Proximity Design Passport. "
            "Not wet-lab validation. Review uncertainty and evidence tier before wiki use."
        ),
    }
    return json.dumps(payload, indent=2, default=str).encode("utf-8")


def wiki_markdown_snippet(
    result: dict[str, Any],
    spec: Optional[DesignSpec] = None,
) -> str:
    """Short markdown block suitable for pasting into a wiki figure caption."""
    passport = result.get("passport") or {}
    pred = result.get("prediction") or {}
    lo, hi = pred.get("uncertainty_95ci", [None, None])
    spec_line = ""
    if spec is not None:
        docks = spec.scaffold.docking_positions
        spec_line = (
            f"- Scaffold: `{spec.scaffold.scaffold_id}` · "
            f"{spec.scaffold.repeat_count} repeats · docking {docks}\n"
        )

    lines = [
        "### ORIGAMI Proximity Design Passport (software export)",
        "",
        spec_line,
        f"- Mechanism profile: `{passport.get('mechanism_profile', '—')}`",
        f"- Evidence maturity: {passport.get('evidence_maturity', '—')}",
        f"- Biosecurity: {passport.get('biosecurity_review_state', '—')}",
        f"- Steric feasible (model): {passport.get('steric_feasible', '—')}",
        "",
    ]
    if pred:
        lines.extend(
            [
                f"- Predicted {pred.get('primary_metric_name', 'metric')}: "
                f"**{pred.get('primary_metric_value', '—')} {pred.get('unit', '')}**",
                f"- 95% CI: [{lo}, {hi}] (computational / literature tier until calibrated)",
                "",
            ]
        )
    lines.extend(
        [
            "> Passing software checks ≠ experimental validation. "
            "Do not present as Tier-1 calibrated without lab data.",
            "",
        ]
    )
    return "\n".join(line for line in lines if line is not None)


def _geometry_summary(geo: Any) -> Optional[dict[str, Any]]:
    if not geo:
        return None
    if hasattr(geo, "model_dump"):
        geo = geo.model_dump()
    return {
        "total_length_nm": geo.get("total_length_nm"),
        "is_rigid": geo.get("is_rigid"),
        "n_docking_sites": len(geo.get("docking_sites") or []),
    }
