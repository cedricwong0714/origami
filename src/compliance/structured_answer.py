"""Structured biological answers (AGENTS.md §7.3)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class StructuredBiologicalAnswer(BaseModel):
    direct_evidence: str
    model_inference: str
    engineering_recommendation: str
    unknown: str
    citations: list[dict] = Field(default_factory=list)
    confidence: Literal["high", "medium", "low", "none"]
    human_review_required: bool
    human_review_reason: Optional[str] = None
    parameter_key: str = ""
    value: Optional[float] = None
    unit: Optional[str] = None
    status: Literal["OK", "INSUFFICIENT_EVIDENCE"] = "OK"
