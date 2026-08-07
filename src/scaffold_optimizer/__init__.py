"""CTPR docking-spacing optimizer (computational ranking)."""

from src.scaffold_optimizer.optimizer import (
    InteractionClass,
    OptimizationResult,
    SpacingCandidate,
    optimize_ctpr_spacing,
)

__all__ = [
    "InteractionClass",
    "OptimizationResult",
    "SpacingCandidate",
    "optimize_ctpr_spacing",
]
