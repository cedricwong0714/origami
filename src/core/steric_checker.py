"""
ORIGAMI Core: Steric Accessibility Checker
Detects payload-payload and payload-scaffold collisions.
The math-chassis clash model uses the deposited C-alpha trace.
This module still approximates the scaffold as a cylinder, now at the
deposited repeat-centroid radius rather than the old 1.8 nm prior.

Key Invariants:
- Payloads modeled as spheres with radius from PayloadSpec
- Scaffold backbone modeled as a cylinder at CTPR_RADIUS_NM
- Docking sites have exclusion zones
- Overlap threshold: 0.5 nm penetration tolerance
"""

from __future__ import annotations
import numpy as np
from pydantic import BaseModel, Field
from typing import List, Tuple
from .ctpr_geometry import CTPR_RADIUS_NM, ScaffoldGeometry

STERIC_OVERLAP_TOLERANCE_NM = 0.5
SCAFFOLD_CYLINDER_RADIUS_NM = CTPR_RADIUS_NM


class StericViolation(BaseModel):
    entity_a: str
    entity_b: str
    overlap_nm: float
    description: str


class StericCheckResult(BaseModel):
    is_feasible: bool
    violations: List[StericViolation] = Field(default_factory=list)
    min_clearance_nm: float = Field(..., ge=0)
    warning_count: int = 0


def check_payload_pair_clash(
    pos_a_nm: Tuple[float, float, float],
    radius_a_nm: float,
    label_a: str,
    pos_b_nm: Tuple[float, float, float],
    radius_b_nm: float,
    label_b: str
) -> StericViolation | None:
    """Check if two spherical payloads overlap beyond tolerance."""
    dist = float(np.linalg.norm(np.array(pos_a_nm) - np.array(pos_b_nm)))
    min_separation = radius_a_nm + radius_b_nm
    overlap = min_separation - dist

    if overlap > STERIC_OVERLAP_TOLERANCE_NM:
        return StericViolation(
            entity_a=label_a,
            entity_b=label_b,
            overlap_nm=float(overlap),
            description=(
                f"{label_a} (r={radius_a_nm:.1f}nm) and {label_b} (r={radius_b_nm:.1f}nm) "
                f"overlap by {overlap:.2f}nm at distance {dist:.2f}nm"
            )
        )
    return None


def check_scaffold_clash(
    payload_pos_nm: Tuple[float, float, float],
    payload_radius_nm: float,
    payload_label: str,
    geometry: ScaffoldGeometry
) -> List[StericViolation]:
    """Check if payload collides with scaffold backbone cylinder (axis centerline)."""
    violations = []
    pos = np.array(payload_pos_nm)
    # Prefer straight-axis beads; fall back to legacy backbone if axis absent
    axis_beads = geometry.axis_coordinates_nm or [
        (0.0, 0.0, float(bp[2])) for bp in geometry.backbone_coordinates_nm
    ]

    for i, bp in enumerate(axis_beads):
        bp_arr = np.array(bp)
        # Distance to scaffold axis (z-axis beads)
        radial_dist = float(np.linalg.norm(pos[:2] - bp_arr[:2]))
        axial_dist = abs(pos[2] - bp_arr[2])

        min_radial = SCAFFOLD_CYLINDER_RADIUS_NM + payload_radius_nm
        if radial_dist < min_radial and axial_dist < 1.5:  # within one repeat height
            overlap = min_radial - radial_dist
            if overlap > STERIC_OVERLAP_TOLERANCE_NM:
                violations.append(StericViolation(
                    entity_a=payload_label,
                    entity_b=f"scaffold_repeat_{i}",
                    overlap_nm=float(overlap),
                    description=(
                        f"{payload_label} clashes with scaffold repeat {i} "
                        f"(radial gap={radial_dist:.2f}nm, min={min_radial:.2f}nm)"
                    )
                ))
    return violations


def run_steric_check(
    geometry: ScaffoldGeometry,
    payload_positions: List[Tuple[str, Tuple[float, float, float], float]]
) -> StericCheckResult:
    """
    Run full steric validation.
    
    Args:
        geometry: Scaffold geometry from ctpr_geometry
        payload_positions: List of (label, position_nm, radius_nm) tuples
    """
    all_violations: List[StericViolation] = []
    min_clearance = float('inf')

    # Payload-payload checks
    for i in range(len(payload_positions)):
        label_i, pos_i, r_i = payload_positions[i]
        for j in range(i + 1, len(payload_positions)):
            label_j, pos_j, r_j = payload_positions[j]
            v = check_payload_pair_clash(pos_i, r_i, label_i, pos_j, r_j, label_j)
            if v:
                all_violations.append(v)
            else:
                dist = float(np.linalg.norm(np.array(pos_i) - np.array(pos_j)))
                clearance = dist - r_i - r_j
                min_clearance = min(min_clearance, clearance)

    # Payload-scaffold checks
    for label, pos, radius in payload_positions:
        sv = check_scaffold_clash(pos, radius, label, geometry)
        all_violations.extend(sv)

    if min_clearance == float('inf'):
        min_clearance = 0.0

    return StericCheckResult(
        is_feasible=len(all_violations) == 0,
        violations=all_violations,
        min_clearance_nm=float(max(0, min_clearance)),
        warning_count=len(all_violations)
    )