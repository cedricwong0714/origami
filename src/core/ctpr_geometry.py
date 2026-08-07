"""
ORIGAMI Core: CTPR Scaffold Geometry Engine
Generates 3D coordinates and docking site positions for CTPR scaffolds.
Implements rigid-body screw-matrix transformations based on validated structural parameters.

Key Invariants (CLASP Docs):
- Rise per repeat: 1.1 nm (axial translation)
- Twist per repeat: ~20 degrees (helical rotation)
- Persistence length: 15 nm (rigid rod approximation for N<14)
- Inter-site spacing example: 3 repeats ≈ 5.5 nm center-to-center
"""

from __future__ import annotations
import numpy as np
from typing import List, Tuple
from pydantic import BaseModel, Field, field_validator
from enum import Enum
from .schema import ScaffoldSpec

# Structural Constants (SCABs 2024 / Dueber 2009)
CTPR_RISE_NM = 1.1
CTPR_TWIST_DEG = 20.0
CTPR_RADIUS_NM = 1.8
PERSISTENCE_LENGTH_NM = 15.0
DOCKING_LOOP_OFFSET_NM = 0.35


class DockingSiteOrientation(str, Enum):
    RADIAL_OUTWARD = "radial_outward"
    AXIAL_N_TERMINAL = "axial_n_terminal"
    AXIAL_C_TERMINAL = "axial_c_terminal"


class DockingSiteGeometry(BaseModel):
    # 1-based CTPR repeat index (matches ScaffoldSpec.docking_positions)
    repeat_index: int = Field(..., ge=1)
    position_nm: Tuple[float, float, float]
    orientation_vector: Tuple[float, float, float]
    orientation_type: DockingSiteOrientation = DockingSiteOrientation.RADIAL_OUTWARD

    @property
    def distance_from_origin_nm(self) -> float:
        return float(np.linalg.norm(self.position_nm))


class ScaffoldGeometry(BaseModel):
    scaffold_id: str
    repeat_count: int = Field(..., ge=1, le=20)
    total_length_nm: float = Field(..., gt=0)
    is_rigid: bool
    docking_sites: List[DockingSiteGeometry] = Field(default_factory=list)
    backbone_coordinates_nm: List[Tuple[float, float, float]] = Field(default_factory=list)

    @field_validator("docking_sites")
    @classmethod
    def validate_docking_positions(cls, v, info):
        repeat_count = info.data.get("repeat_count")
        if repeat_count is not None:
            for site in v:
                if site.repeat_index < 1 or site.repeat_index > repeat_count:
                    raise ValueError(
                        f"Docking site at repeat {site.repeat_index} is outside "
                        f"1..{repeat_count} (1-based CTPR indexing)"
                    )
        return v

    def get_inter_site_distance_nm(self, site_a: int, site_b: int) -> float:
        if site_a >= len(self.docking_sites) or site_b >= len(self.docking_sites):
            raise IndexError("Docking site index out of range")
        pos_a = np.array(self.docking_sites[site_a].position_nm)
        pos_b = np.array(self.docking_sites[site_b].position_nm)
        return float(np.linalg.norm(pos_a - pos_b))

    def get_active_site_estimate_nm(
        self, site_a: int, site_b: int,
        payload_radius_a_nm: float = 2.0,
        payload_radius_b_nm: float = 2.0
    ) -> float:
        """Estimate distance between active sites of docked payloads."""
        anchor_distance = self.get_inter_site_distance_nm(site_a, site_b)
        return max(0.0, anchor_distance - payload_radius_a_nm - payload_radius_b_nm)


def _rotation_matrix_z(angle_deg: float) -> np.ndarray:
    rad = np.radians(angle_deg)
    c, s = np.cos(rad), np.sin(rad)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def generate_scaffold_geometry(spec: ScaffoldSpec) -> ScaffoldGeometry:
    """
    Build CTPR geometry from a ScaffoldSpec.

    ``ScaffoldSpec.docking_positions`` are **1-based** repeat indices in
    ``[1, repeat_count]`` (same convention as verification). Internally these
    are converted to 0-based backbone array indices.
    """
    n_repeats = spec.repeat_count
    total_length = n_repeats * CTPR_RISE_NM
    is_rigid = total_length <= PERSISTENCE_LENGTH_NM

    backbone: List[Tuple[float, float, float]] = []
    current_pos = np.array([0.0, 0.0, 0.0])
    current_rot = np.eye(3)
    twist_matrix = _rotation_matrix_z(CTPR_TWIST_DEG)
    translation = np.array([0.0, 0.0, CTPR_RISE_NM])

    for i in range(n_repeats):
        backbone.append(tuple(current_pos.tolist()))
        current_rot = current_rot @ twist_matrix
        current_pos = current_pos + current_rot @ translation

    docking_sites: List[DockingSiteGeometry] = []
    for dock_1based in sorted(set(spec.docking_positions)):
        if dock_1based < 1 or dock_1based > n_repeats:
            # Out-of-range sites are omitted here; verification reports the error.
            continue
        idx0 = dock_1based - 1
        base_pos = np.array(backbone[idx0])
        angle = idx0 * CTPR_TWIST_DEG
        radial_dir = np.array([np.cos(np.radians(angle)), np.sin(np.radians(angle)), 0.0])
        site_pos = base_pos + radial_dir * (CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM)

        docking_sites.append(DockingSiteGeometry(
            repeat_index=dock_1based,
            position_nm=tuple(site_pos.tolist()),
            orientation_vector=tuple(radial_dir.tolist()),
            orientation_type=DockingSiteOrientation.RADIAL_OUTWARD
        ))

    return ScaffoldGeometry(
        scaffold_id=spec.scaffold_id,
        repeat_count=n_repeats,
        total_length_nm=total_length,
        is_rigid=is_rigid,
        docking_sites=docking_sites,
        backbone_coordinates_nm=backbone
    )