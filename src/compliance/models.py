"""Shared compliance models (AGENTS.md verification layer schema)."""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Check(BaseModel):
    name: str
    passed: bool
    message: str
    severity: Literal["pass", "warning", "error"] = "pass"


class VerificationLayerResult(BaseModel):
    layer: int
    layer_name: str
    checks: list[Check] = Field(default_factory=list)
    passed: bool
    blocks_export: bool = False
    checksum: Optional[str] = None


class ReadingFrameResult(BaseModel):
    valid: bool
    error: Optional[str] = None
    protein: Optional[str] = None


class ForbiddenSiteResult(BaseModel):
    sequence_id: str
    found_sites: dict[str, dict] = Field(default_factory=dict)
    passed: bool = True


class UnexpectedSequenceModificationError(ValueError):
    """Raised when a sequence changes without explicit declaration."""
