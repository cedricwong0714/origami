"""
ORIGAMI Core: CTPR Scaffold Geometry Engine
Generates 3D coordinates and docking site positions for CTPR scaffolds.
Implements rigid-body screw-matrix transformations based on validated structural parameters.

Key Invariants (CLASP Docs / AGENTS.md §15.1):
- Rise per repeat: 1.1 nm (axial translation)
- Twist per repeat: ~20 degrees (helical rotation)
- Persistence length: 15 nm (rigid rod approximation for N<14)
- Inter-site spacing example: 3 repeats ≈ 5.5 nm center-to-center

Uncertainty (CLASP Docs §1.1): first-order propagation of rise/twist std
devs through the screw transform, plus worm-like-chain flexibility when
total contour length exceeds the persistence length.
"""

from __future__ import annotations

import warnings
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator

from .schema import ScaffoldSpec

# Structural Constants (SCABs 2024 / Dueber 2009)
CTPR_RISE_NM = 1.1
CTPR_TWIST_DEG = 20.0
CTPR_RADIUS_NM = 1.8
PERSISTENCE_LENGTH_NM = 15.0
DOCKING_LOOP_OFFSET_NM = 0.35

# Default structural std-devs (half-width of published CTPR variation ranges)
DEFAULT_RISE_STD_NM = 0.05
DEFAULT_TWIST_STD_DEG = 1.0


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
    # Per-axis std-dev from first-order uncertainty propagation (nm)
    position_uncertainty_nm: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    @property
    def distance_from_origin_nm(self) -> float:
        return float(np.linalg.norm(self.position_nm))

    @property
    def position_uncertainty_norm_nm(self) -> float:
        return float(np.linalg.norm(self.position_uncertainty_nm))


class ScaffoldGeometry(BaseModel):
    scaffold_id: str
    repeat_count: int = Field(..., ge=1, le=20)
    total_length_nm: float = Field(..., gt=0)
    is_rigid: bool
    docking_sites: List[DockingSiteGeometry] = Field(default_factory=list)
    backbone_coordinates_nm: List[Tuple[float, float, float]] = Field(default_factory=list)
    wlc_end_to_end_rms_nm: Optional[float] = None
    rigid_rod_warning: Optional[str] = None
    rise_std_nm: float = DEFAULT_RISE_STD_NM
    twist_std_deg: float = DEFAULT_TWIST_STD_DEG

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

    def get_inter_site_distance_uncertainty_nm(self, site_a: int, site_b: int) -> float:
        """
        Combined distance uncertainty: quadrature of per-site structural
        uncertainties plus WLC flexibility contribution when non-rigid.
        """
        if site_a >= len(self.docking_sites) or site_b >= len(self.docking_sites):
            raise IndexError("Docking site index out of range")
        ua = np.array(self.docking_sites[site_a].position_uncertainty_nm)
        ub = np.array(self.docking_sites[site_b].position_uncertainty_nm)
        structural = float(np.linalg.norm(np.sqrt(ua**2 + ub**2)))
        flex = 0.0
        if not self.is_rigid and self.wlc_end_to_end_rms_nm is not None:
            rigid_length = self.total_length_nm
            # Extra variance of WLC relative to rigid rod as flexibility term
            flex = abs(self.wlc_end_to_end_rms_nm - rigid_length) / max(
                1, abs(self.docking_sites[site_a].repeat_index
                       - self.docking_sites[site_b].repeat_index)
            )
        return float(np.sqrt(structural**2 + flex**2))

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


def wlc_mean_square_end_to_end(contour_nm: float, persistence_nm: float) -> float:
    """
    Worm-like-chain mean-square end-to-end distance:
    ⟨R²⟩ = 2 Lp L [1 − (Lp/L)(1 − exp(−L/Lp))]
    """
    if contour_nm <= 0 or persistence_nm <= 0:
        return 0.0
    ratio = contour_nm / persistence_nm
    if ratio < 1e-8:
        return contour_nm**2
    return float(
        2.0 * persistence_nm * contour_nm
        * (1.0 - (1.0 / ratio) * (1.0 - np.exp(-ratio)))
    )


def _site_position_uncertainty(
    repeat_index_0based: int,
    rise_nm: float,
    twist_deg: float,
    rise_std_nm: float,
    twist_std_deg: float,
    radius_nm: float,
) -> Tuple[float, float, float]:
    """
    First-order (linear) uncertainty of docking-site position.

    Axial: σ_z ≈ sqrt(n) · σ_rise (independent rise errors).
    Radial/angular: σ_θ ≈ sqrt(n) · σ_twist → tangential σ ≈ r · σ_θ(rad).
    """
    n = max(1, repeat_index_0based)
    sigma_z = np.sqrt(n) * rise_std_nm
    sigma_theta_rad = np.radians(np.sqrt(n) * twist_std_deg)
    sigma_tangential = radius_nm * sigma_theta_rad
    # Split tangential uncertainty equally into x/y in the mean sense
    sigma_xy = sigma_tangential / np.sqrt(2.0)
    return (float(sigma_xy), float(sigma_xy), float(sigma_z))


def generate_scaffold_geometry(
    spec: ScaffoldSpec,
    rise_std_nm: float = DEFAULT_RISE_STD_NM,
    twist_std_deg: float = DEFAULT_TWIST_STD_DEG,
) -> ScaffoldGeometry:
    """
    Build CTPR geometry from a ScaffoldSpec.

    ``ScaffoldSpec.docking_positions`` are **1-based** repeat indices in
    ``[1, repeat_count]`` (same convention as verification). Internally these
    are converted to 0-based backbone array indices.

    Propagates structural uncertainty and applies a WLC flexibility correction
    when total length exceeds the persistence length.
    """
    n_repeats = spec.repeat_count
    total_length = n_repeats * CTPR_RISE_NM
    is_rigid = total_length <= PERSISTENCE_LENGTH_NM

    wlc_rms = float(np.sqrt(wlc_mean_square_end_to_end(total_length, PERSISTENCE_LENGTH_NM)))
    rigid_warning = None
    if not is_rigid:
        rigid_warning = (
            f"Scaffold contour {total_length:.2f} nm exceeds persistence length "
            f"{PERSISTENCE_LENGTH_NM} nm. Rigid-rod coordinates are an approximation; "
            f"WLC end-to-end RMS ≈ {wlc_rms:.2f} nm. Distance uncertainties include "
            f"flexibility contribution."
        )
        warnings.warn(rigid_warning, UserWarning, stacklevel=2)

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
    radial_offset = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM
    for dock_1based in sorted(set(spec.docking_positions)):
        if dock_1based < 1 or dock_1based > n_repeats:
            continue
        idx0 = dock_1based - 1
        base_pos = np.array(backbone[idx0])
        angle = idx0 * CTPR_TWIST_DEG
        radial_dir = np.array([np.cos(np.radians(angle)), np.sin(np.radians(angle)), 0.0])
        site_pos = base_pos + radial_dir * radial_offset
        unc = _site_position_uncertainty(
            idx0, CTPR_RISE_NM, CTPR_TWIST_DEG, rise_std_nm, twist_std_deg, radial_offset
        )

        docking_sites.append(DockingSiteGeometry(
            repeat_index=dock_1based,
            position_nm=tuple(site_pos.tolist()),
            orientation_vector=tuple(radial_dir.tolist()),
            orientation_type=DockingSiteOrientation.RADIAL_OUTWARD,
            position_uncertainty_nm=unc,
        ))

    return ScaffoldGeometry(
        scaffold_id=spec.scaffold_id,
        repeat_count=n_repeats,
        total_length_nm=total_length,
        is_rigid=is_rigid,
        docking_sites=docking_sites,
        backbone_coordinates_nm=backbone,
        wlc_end_to_end_rms_nm=wlc_rms,
        rigid_rod_warning=rigid_warning,
        rise_std_nm=rise_std_nm,
        twist_std_deg=twist_std_deg,
    )