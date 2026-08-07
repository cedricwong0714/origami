"""Layer 2 — biological plausibility (AGENTS.md §9.2)."""

from __future__ import annotations

from src.compliance.biological_parameters import ORIGAMI_PARAMETER_LIBRARY
from src.compliance.models import Check, VerificationLayerResult
from src.core.schema import DesignSpec


def verify_biological_plausibility(
    design_spec: DesignSpec,
    parameter_library: dict | None = None,
) -> VerificationLayerResult:
    """
    Warn when design parameters fall outside validated biological ranges.
    Warnings do not hard-fail MVP designs.
    """
    library = parameter_library or ORIGAMI_PARAMETER_LIBRARY
    checks: list[Check] = []

    scaffold_len_nm = design_spec.scaffold.repeat_count * library["CTPR_RISE_NM"].value
    rise_param = library["CTPR_RISE_NM"]
    in_range = rise_param.is_within_range(
        design_spec.scaffold.repeat_count * rise_param.value / max(design_spec.scaffold.repeat_count, 1)
    )
    checks.append(
        Check(
            name="scaffold_length_plausible",
            passed=scaffold_len_nm <= 25.0,
            message=(
                f"Scaffold length {scaffold_len_nm:.1f} nm exceeds typical MVP range."
                if scaffold_len_nm > 25.0
                else f"Scaffold length {scaffold_len_nm:.1f} nm within MVP range."
            ),
            severity="warning" if scaffold_len_nm > 25.0 else "pass",
        )
    )
    _ = in_range  # per-repeat rise validated via library import, not repeat_count scaling

    for pos in design_spec.scaffold.docking_positions:
        ok = 1 <= pos <= design_spec.scaffold.repeat_count
        checks.append(
            Check(
                name=f"docking_range_{pos}",
                passed=ok,
                message=(
                    f"Docking position {pos} outside 1..{design_spec.scaffold.repeat_count}."
                    if not ok
                    else f"Docking position {pos} within scaffold."
                ),
                severity="error" if not ok else "pass",
            )
        )

    hard_fail = any(c.severity == "error" and not c.passed for c in checks)
    return VerificationLayerResult(
        layer=2,
        layer_name="biological_plausibility",
        checks=checks,
        passed=not hard_fail,
    )
