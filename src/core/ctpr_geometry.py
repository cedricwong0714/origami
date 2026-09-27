"""
ORIGAMI Core: CTPR Scaffold Geometry Engine

Cylindrical screw (superhelix) kinematics for consensus TPR arrays:
each repeat advances by axial rise and rotates by twist about the
scaffold axis. Repeat centers and docking sites sit off-axis on a
cylinder — not on a straight polypeptide rod.

Key Invariants:
- Rise per repeat: mean of the deposited 2AVP/2HYZ/2FO7 screw fit
  (Kajander et al. 2007 coordinates, DOI 10.1107/S0907444907024353).
  The previous CLASP prior was 1.1 nm.
- Twist per repeat: 45 degrees. That angle is inside the deposited
  twist range and keeps eight repeats per turn. The deposited mean
  twist is not exactly 45 degrees; see origami.physical.deposited.
- Persistence length: 15 nm (project rigid-rod cutoff; not in the
  deposited coordinate table)
- Scaffold cylinder radius: 1.8 nm (not the deposited repeat-centroid
  radius; the fit's outer C-alpha shell is wider)

Center-of-mass / docking chord (Δi repeats apart, radius R):
  d = sqrt( 2 R² (1 − cos(Δi · θ)) + (Δi · rise)² )

Uncertainty: first-order rise/twist std-devs through the screw, plus
WLC flexibility when contour length exceeds the persistence length.
"""

from __future__ import annotations

import warnings
from enum import Enum
from typing import List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field, field_validator

from .schema import ScaffoldSpec

# Structural Constants
# Parameter: CTPR axial rise per repeat
# Value: 0.8416139416984938
# Units: nm
# Source: screw fit to PDB 2AVP, 2HYZ, 2FO7 C-alpha coordinates,
#   Kajander et al. (2007) Acta Crystallogr D 63:800-811,
#   DOI: 10.1107/S0907444907024353
# System: Consensus TPR asymmetric-unit chains (2 or 4 repeats)
# Method: Kabsch fit of successive 34-residue blocks, then screw decomposition.
#   Mean of 7 steps. Recomputed by origami.physical.deposited.
# Notes: Previous CLASP prior was 1.1 nm. This is not a number printed in
#   the article PDF (that PDF is not open). calibrated stays false.
#   1 nm = 10 Å, so the mean 8.416139416984938 Å is 0.8416139416984938 nm.
CTPR_RISE_NM = 0.8416139416984938

# Parameter: CTPR superhelical twist per repeat
# Value: 45.0
# Units: degrees
# Source: Kajander et al. (2007) Acta Crystallogr D Biol Crystallogr 63:800–811,
#   DOI: 10.1107/S0907444907024353, PMID: 17582171
#   (CTPR8: eight tandem repeats complete one superhelical turn → 360°/8 = 45°).
#   Bismut et al. (2025) Protein Science 34:e70150, DOI: 10.1002/pro.70150
# System: Designed consensus TPR arrays (CTPR8 / CTPR20), crystal lattice
# Method: X-ray crystallography of CTPR superhelices (PDB 2AVP / 2FO7 / 2HYZ)
# Notes: Superhelical twist between successive repeats, not ~24° A/B tilt
CTPR_TWIST_DEG = 45.0

# Parameter: CTPR scaffold cylinder radius
# Value: 1.8
# Units: nm
# Source: CLASP Docs §2.4 / steric_checker scaffold cylinder
# Notes: Not the deposited repeat-centroid radius (about 1.22 nm).
#   The deposited outer C-alpha shell is about 1.84–2.01 nm, so 1.8 nm
#   sits inside that shell. Left unchanged; the comparison flags it.
CTPR_RADIUS_NM = 1.8
# Parameter: rigid-rod persistence cutoff
# Value: 15.0
# Units: nm
# Source: CLASP docs cutoff. Not retrieved from the deposited coordinates
#   or from the open abstract of Synakewicz et al. 2022,
#   DOI: 10.1021/acsnano.1c09162.
PERSISTENCE_LENGTH_NM = 15.0

# Parameter: Docking-loop radial offset beyond scaffold cylinder
# Value: 0.35
# Units: nm
# Source: CLASP geometry prior (loop graft extension beyond cylinder)
DOCKING_LOOP_OFFSET_NM = 0.35

# Sample standard deviation (n-1) of the same seven deposited screw steps.
# Rise: 0.4760507886412968 Å = 0.04760507886412968 nm.
# Twist: 2.3470532160238053 degrees.
# Not a standard error printed in the paper.
DEFAULT_RISE_STD_NM = 0.04760507886412968
DEFAULT_TWIST_STD_DEG = 2.3470532160238053


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
    # Helical path of repeat centers (radius = CTPR_RADIUS_NM)
    backbone_coordinates_nm: List[Tuple[float, float, float]] = Field(default_factory=list)
    # Straight superhelix axis (x=y=0) for cylinder steric checks
    axis_coordinates_nm: List[Tuple[float, float, float]] = Field(default_factory=list)
    docking_radius_nm: float = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM
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
            flex = abs(self.wlc_end_to_end_rms_nm - rigid_length) / max(
                1,
                abs(
                    self.docking_sites[site_a].repeat_index
                    - self.docking_sites[site_b].repeat_index
                ),
            )
        return float(np.sqrt(structural**2 + flex**2))

    def get_active_site_estimate_nm(
        self,
        site_a: int,
        site_b: int,
        payload_radius_a_nm: float = 2.0,
        payload_radius_b_nm: float = 2.0,
    ) -> float:
        """Estimate gap between payload surfaces (COM chord minus radii)."""
        anchor_distance = self.get_inter_site_distance_nm(site_a, site_b)
        return max(0.0, anchor_distance - payload_radius_a_nm - payload_radius_b_nm)


def helical_chord_distance_nm(
    delta_i: int,
    radius_nm: float,
    rise_nm: float = CTPR_RISE_NM,
    twist_deg: float = CTPR_TWIST_DEG,
) -> float:
    """
    Euclidean distance between two points on a cylindrical screw,
    Δi repeats apart at radial distance ``radius_nm``.
    """
    if delta_i < 0:
        raise ValueError("delta_i must be non-negative")
    if delta_i == 0:
        return 0.0
    theta = np.radians(delta_i * twist_deg)
    return float(
        np.sqrt(2.0 * radius_nm**2 * (1.0 - np.cos(theta)) + (delta_i * rise_nm) ** 2)
    )


def screw_point_nm(
    repeat_index_0based: int,
    radius_nm: float,
    rise_nm: float = CTPR_RISE_NM,
    twist_deg: float = CTPR_TWIST_DEG,
) -> Tuple[float, float, float]:
    """Cartesian coordinates of a screw point at a given 0-based repeat index."""
    angle = np.radians(repeat_index_0based * twist_deg)
    return (
        float(radius_nm * np.cos(angle)),
        float(radius_nm * np.sin(angle)),
        float(repeat_index_0based * rise_nm),
    )


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
        2.0
        * persistence_nm
        * contour_nm
        * (1.0 - (1.0 / ratio) * (1.0 - np.exp(-ratio)))
    )


def _site_position_uncertainty(
    repeat_index_0based: int,
    rise_std_nm: float,
    twist_std_deg: float,
    radius_nm: float,
) -> Tuple[float, float, float]:
    """
    First-order (linear) uncertainty of docking-site position.

    Axial: σ_z ≈ sqrt(n) · σ_rise.
    Tangential: σ ≈ r · σ_θ with σ_θ ≈ sqrt(n) · σ_twist (rad).
    """
    n = max(1, repeat_index_0based)
    sigma_z = np.sqrt(n) * rise_std_nm
    sigma_theta_rad = np.radians(np.sqrt(n) * twist_std_deg)
    sigma_tangential = radius_nm * sigma_theta_rad
    sigma_xy = sigma_tangential / np.sqrt(2.0)
    return (float(sigma_xy), float(sigma_xy), float(sigma_z))


def generate_scaffold_geometry(
    spec: ScaffoldSpec,
    rise_std_nm: float = DEFAULT_RISE_STD_NM,
    twist_std_deg: float = DEFAULT_TWIST_STD_DEG,
    com_radial_extra_nm: float = 0.0,
) -> ScaffoldGeometry:
    """
    Build CTPR geometry from a ScaffoldSpec using cylindrical-screw kinematics.

    ``ScaffoldSpec.docking_positions`` are **1-based** repeat indices in
    ``[1, repeat_count]``.

    Parameters
    ----------
    com_radial_extra_nm :
        Optional extra radial offset beyond scaffold+loop for payload COM
        (e.g. sensor-domain extension). Default 0 keeps docking at
        CTPR_RADIUS + DOCKING_LOOP_OFFSET. Must be ≥ 0.
    """
    if com_radial_extra_nm < 0:
        raise ValueError("com_radial_extra_nm must be ≥ 0")

    n_repeats = spec.repeat_count
    total_length = n_repeats * CTPR_RISE_NM
    is_rigid = total_length <= PERSISTENCE_LENGTH_NM

    wlc_rms = float(np.sqrt(wlc_mean_square_end_to_end(total_length, PERSISTENCE_LENGTH_NM)))
    rigid_warning = None
    if not is_rigid:
        rigid_warning = (
            f"Scaffold contour {total_length:.2f} nm exceeds persistence length "
            f"{PERSISTENCE_LENGTH_NM} nm. Rigid screw coordinates are an approximation; "
            f"WLC end-to-end RMS ≈ {wlc_rms:.2f} nm. Distance uncertainties include "
            f"flexibility contribution."
        )
        warnings.warn(rigid_warning, UserWarning, stacklevel=2)

    # Axis (centerline) + helical backbone (repeat centers on cylinder)
    axis: List[Tuple[float, float, float]] = []
    backbone: List[Tuple[float, float, float]] = []
    for i in range(n_repeats):
        axis.append((0.0, 0.0, float(i * CTPR_RISE_NM)))
        backbone.append(screw_point_nm(i, CTPR_RADIUS_NM))

    docking_radius = CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM + com_radial_extra_nm
    docking_sites: List[DockingSiteGeometry] = []
    for dock_1based in sorted(set(spec.docking_positions)):
        if dock_1based < 1 or dock_1based > n_repeats:
            continue
        idx0 = dock_1based - 1
        angle = idx0 * CTPR_TWIST_DEG
        radial_dir = (
            float(np.cos(np.radians(angle))),
            float(np.sin(np.radians(angle))),
            0.0,
        )
        site_pos = screw_point_nm(idx0, docking_radius)
        unc = _site_position_uncertainty(
            idx0, rise_std_nm, twist_std_deg, docking_radius
        )
        docking_sites.append(
            DockingSiteGeometry(
                repeat_index=dock_1based,
                position_nm=site_pos,
                orientation_vector=radial_dir,
                orientation_type=DockingSiteOrientation.RADIAL_OUTWARD,
                position_uncertainty_nm=unc,
            )
        )

    return ScaffoldGeometry(
        scaffold_id=spec.scaffold_id,
        repeat_count=n_repeats,
        total_length_nm=total_length,
        is_rigid=is_rigid,
        docking_sites=docking_sites,
        backbone_coordinates_nm=backbone,
        axis_coordinates_nm=axis,
        docking_radius_nm=docking_radius,
        wlc_end_to_end_rms_nm=wlc_rms,
        rigid_rod_warning=rigid_warning,
        rise_std_nm=rise_std_nm,
        twist_std_deg=twist_std_deg,
    )
