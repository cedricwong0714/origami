"""CTPR scaffold geometry.

Docking-site coordinates come from ``src.core.ctpr_geometry.screw_point_nm``.
That function is in nanometres and degrees. This module stores ångströms and
radians. The only conversion is at that boundary: 1 nm = 10 Å.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from origami.priors import CTPR_RADIUS_A, CTPR_RISE_A, CTPR_ROTATION_RAD
from src.core.ctpr_geometry import (
    CTPR_RADIUS_NM,
    CTPR_RISE_NM,
    CTPR_TWIST_DEG,
    DOCKING_LOOP_OFFSET_NM,
    screw_point_nm,
)

# Prior id stored on geometries produced by build_ctpr.
CANONICAL_GEOMETRY_PRIOR_ID = "src.core.ctpr_geometry"

# 1 nm = 10 Å. Used only when crossing to or from src.core.ctpr_geometry.
_NM_TO_A = 10.0


def _rotation_z(theta: float) -> np.ndarray:
    c, s = np.cos(theta), np.sin(theta)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def se3(R: np.ndarray, t: np.ndarray) -> np.ndarray:
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = t
    return T


def apply_se3(T: np.ndarray, points: np.ndarray) -> np.ndarray:
    pts = np.atleast_2d(points)
    h = np.concatenate([pts, np.ones((pts.shape[0], 1))], axis=1)
    out = (T @ h.T).T[:, :3]
    return out if points.ndim == 2 else out[0]


@dataclass(frozen=True)
class DockingSite:
    index: int
    xyz_A: np.ndarray
    orientation: np.ndarray  # 3x3 rotation, columns = local axes
    covariance_A2: np.ndarray  # 3x3 positional covariance from parameter sigma


@dataclass
class CtprGeometry:
    n_repeats: int
    sites: list[DockingSite]
    rise_A: float
    rotation_rad: float
    radius_A: float
    axis: np.ndarray
    coord_covariance: np.ndarray  # (3N, 3N), includes site–site correlation
    # build_ctpr sets this to CANONICAL_GEOMETRY_PRIOR_ID.
    provenance: str = "literature_placeholder"

    def cross_covariance(self, i: int, j: int) -> np.ndarray:
        """Cov(site i, site j), shape (3, 3)."""
        c = self.coord_covariance
        return c[3 * i : 3 * i + 3, 3 * j : 3 * j + 3]

    @property
    def coordinates(self) -> np.ndarray:
        return np.stack([s.xyz_A for s in self.sites], axis=0)

    def site(self, index: int) -> DockingSite:
        return self.sites[index]

    def end_to_end_A(self, i: int, j: int) -> float:
        return float(np.linalg.norm(self.sites[j].xyz_A - self.sites[i].xyz_A))


def _repeat_transform(rise_A: float, rotation_rad: float) -> np.ndarray:
    R = _rotation_z(rotation_rad)
    t = np.array([0.0, 0.0, rise_A])
    return se3(R, t)


def canonical_defaults_A() -> tuple[float, float, float]:
    """Canonical rise (Å), twist (rad), and docking radius (Å).

    Converted from ``src.core.ctpr_geometry`` at this boundary.
    1 nm = 10 Å. 45 degrees = π/4 radians.
    Docking radius = (scaffold cylinder + docking-loop offset) in Å.
    """
    rise_A = CTPR_RISE_NM * _NM_TO_A
    rotation_rad = math.radians(CTPR_TWIST_DEG)
    radius_A = (CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) * _NM_TO_A
    return rise_A, rotation_rad, radius_A


def _screw_coordinates_A(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
    radius_A: float,
) -> np.ndarray:
    """Docking coordinates in Å from ``screw_point_nm``.

    ``screw_point_nm`` takes nanometres and degrees and returns nanometres.
    Divide Å by 10 on the way in and multiply nm by 10 on the way out.
    """
    rise_nm = rise_A / _NM_TO_A
    radius_nm = radius_A / _NM_TO_A
    twist_deg = math.degrees(rotation_rad)
    coords = np.zeros((n_repeats, 3), dtype=float)
    for i in range(n_repeats):
        x_nm, y_nm, z_nm = screw_point_nm(
            i,
            radius_nm,
            rise_nm=rise_nm,
            twist_deg=twist_deg,
        )
        coords[i, 0] = x_nm * _NM_TO_A
        coords[i, 1] = y_nm * _NM_TO_A
        coords[i, 2] = z_nm * _NM_TO_A
    return coords


def helical_frames(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
    radius_A: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return (N,3) docking coordinates in Å and (N,3,3) orientations.

    Coordinates are the canonical screw, not a second geometry model.
    Orientation columns are radial, tangential, and axial.
    """
    coords = _screw_coordinates_A(n_repeats, rise_A, rotation_rad, radius_A)
    orients = np.zeros((n_repeats, 3, 3), dtype=float)
    for i in range(n_repeats):
        orients[i] = _rotation_z(i * rotation_rad)
    return coords, orients


def _jacobian(
    n_repeats: int,
    rise_A: float,
    rotation_rad: float,
    radius_A: float,
    eps: float = 1e-4,
) -> np.ndarray:
    """∂(vec coords) / ∂(rise, rotation, radius). Shape (3N, 3)."""
    theta = np.array([rise_A, rotation_rad, radius_A], dtype=float)
    base, _ = helical_frames(n_repeats, *theta)
    y0 = base.ravel()
    J = np.zeros((y0.size, 3))
    for k in range(3):
        d = np.zeros(3)
        d[k] = eps
        plus, _ = helical_frames(n_repeats, *(theta + d))
        minus, _ = helical_frames(n_repeats, *(theta - d))
        J[:, k] = (plus.ravel() - minus.ravel()) / (2.0 * eps)
    return J


def build_ctpr(
    n_repeats: int,
    rise_A: float | None = None,
    rotation_rad: float | None = None,
    radius_A: float | None = None,
) -> CtprGeometry:
    if n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    # Defaults are the src.core.ctpr_geometry constants after nm → Å.
    # Prior Parameter values are checked against those constants so the
    # parameter table cannot silently diverge from the coordinates.
    canon_rise, canon_rot, canon_rad = canonical_defaults_A()
    rise = canon_rise if rise_A is None else rise_A
    rot = canon_rot if rotation_rad is None else rotation_rad
    rad = canon_rad if radius_A is None else radius_A
    if rise_A is None and not math.isclose(CTPR_RISE_A.value, canon_rise, abs_tol=1e-9):
        raise ValueError(
            "CTPR_RISE_A does not match src.core.ctpr_geometry.CTPR_RISE_NM "
            "after converting 1 nm = 10 Å"
        )
    if rotation_rad is None and not math.isclose(
        CTPR_ROTATION_RAD.value, canon_rot, abs_tol=1e-12
    ):
        raise ValueError(
            "CTPR_ROTATION_RAD does not match src.core.ctpr_geometry.CTPR_TWIST_DEG "
            "after converting degrees to radians"
        )
    if radius_A is None and not math.isclose(CTPR_RADIUS_A.value, canon_rad, abs_tol=1e-9):
        raise ValueError(
            "CTPR_RADIUS_A does not match (CTPR_RADIUS_NM + DOCKING_LOOP_OFFSET_NM) "
            "after converting 1 nm = 10 Å"
        )
    coords, orients = helical_frames(n_repeats, rise, rot, rad)
    J = _jacobian(n_repeats, rise, rot, rad)
    theta_cov = np.diag(
        [
            CTPR_RISE_A.sigma**2,
            CTPR_ROTATION_RAD.sigma**2,
            CTPR_RADIUS_A.sigma**2,
        ]
    )
    coord_cov = J @ theta_cov @ J.T  # 3N x 3N
    sites = []
    for i in range(n_repeats):
        cov_i = coord_cov[3 * i : 3 * i + 3, 3 * i : 3 * i + 3]
        # numerical SPD guard
        cov_i = 0.5 * (cov_i + cov_i.T) + 1e-8 * np.eye(3)
        sites.append(
            DockingSite(
                index=i,
                xyz_A=coords[i],
                orientation=orients[i],
                covariance_A2=cov_i,
            )
        )
    return CtprGeometry(
        n_repeats=n_repeats,
        sites=sites,
        rise_A=rise,
        rotation_rad=rot,
        radius_A=rad,
        axis=np.array([0.0, 0.0, 1.0]),
        coord_covariance=coord_cov,
        provenance=CANONICAL_GEOMETRY_PRIOR_ID,
    )
