"""Layer 5 — reproducibility (AGENTS.md §9.5)."""

from __future__ import annotations

from typing import Optional

from src.compliance.models import Check, VerificationLayerResult
from src.profiles.base import ProfilePrediction


def verify_reproducibility(
    profile_version: str,
    prediction: Optional[ProfilePrediction] = None,
    parameter_sources: Optional[list[str]] = None,
) -> VerificationLayerResult:
    checks: list[Check] = []
    checks.append(
        Check(
            name="model_version_pinned",
            passed=bool(profile_version),
            message=(
                "Model version is not pinned."
                if not profile_version
                else f"Model version pinned: {profile_version}."
            ),
            severity="warning" if not profile_version else "pass",
        )
    )
    sources = parameter_sources or (
        [f"profile:{prediction.profile_id}"] if prediction else []
    )
    checks.append(
        Check(
            name="parameter_sources_cited",
            passed=len(sources) > 0,
            message=(
                "No parameter sources are recorded."
                if not sources
                else f"{len(sources)} parameter source(s) recorded."
            ),
            severity="warning" if not sources else "pass",
        )
    )
    return VerificationLayerResult(
        layer=5,
        layer_name="reproducibility",
        checks=checks,
        passed=not any(c.severity == "error" and not c.passed for c in checks),
    )
