"""Layer 4 — safety and biosecurity (AGENTS.md §9.4). Never bypass."""

from __future__ import annotations

from typing import Optional

from src.compiler.expression_vector import (
    ExpressionPlan,
    validate_expression_plan,
    verify_parts_against_allowlist,
)
from src.compliance.models import Check, VerificationLayerResult
from src.core.schema import DesignSpec, MoCloPart


def verify_safety_and_biosecurity(
    spec: DesignSpec,
    parts: list[MoCloPart],
    expression_plan: Optional[ExpressionPlan] = None,
) -> VerificationLayerResult:
    checks: list[Check] = []
    sequences = {p.part_id: p.sequence for p in parts if p.sequence}
    allowlist = verify_parts_against_allowlist(
        [p.part_id for p in parts],
        sequences_by_id=sequences,
    )

    if allowlist.get("ok"):
        for part_id in allowlist.get("checked_part_ids", []):
            checks.append(
                Check(
                    name=f"allowlist_check_{part_id}",
                    passed=True,
                    message=f"Part '{part_id}' is validated.",
                    severity="pass",
                )
            )
    for err in allowlist.get("errors", []):
        checks.append(
            Check(
                name="allowlist",
                passed=False,
                message=err,
                severity="error",
            )
        )
    for warn in allowlist.get("warnings", []):
        checks.append(
            Check(
                name="allowlist_warning",
                passed=True,
                message=warn,
                severity="warning",
            )
        )

    if expression_plan is not None:
        expr = validate_expression_plan(expression_plan)
        for err in expr.get("errors", []):
            checks.append(
                Check(
                    name="expression_strategy",
                    passed=False,
                    message=err,
                    severity="error",
                )
            )
        if expr.get("ok"):
            checks.append(
                Check(
                    name="expression_strategy",
                    passed=True,
                    message="Coexpression strategy accepted.",
                    severity="pass",
                )
            )

    blocks = any(c.severity == "error" and not c.passed for c in checks)
    return VerificationLayerResult(
        layer=4,
        layer_name="safety_and_biosecurity",
        checks=checks,
        passed=not blocks,
        blocks_export=blocks,
    )
