"""Probabilistic steric clashes for tethered payloads on a C-alpha trace.

Each payload is a sphere whose center sits one linker RMS outward of the
inter-repeat junction. The scaffold is the deposited repeat C-alpha cloud
placed on the runtime screw, not a cylinder and not a sphere. P(overlap)
uses the delta method on that distance given Gaussian positional covariance
from the helical-parameter Jacobian. Optional Monte Carlo check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from origami.physical.deposited import placed_ca_cloud
from origami.physical.geometry import CtprGeometry, DockingSite
from origami.priors import LINKER_SIGMA_A


def payload_center(site: DockingSite, standoff_A: float) -> np.ndarray:
    """Center sits radially outward of the junction by ``standoff_A``.

    For a tethered sphere, that distance is the linker RMS plus the payload
    radius: the linker ends at the surface, and the center is one radius
    farther out.
    """
    xy = site.xyz_A[:2]
    nrm = float(np.linalg.norm(xy))
    if nrm < 1e-9:
        direction = np.array([1.0, 0.0, 0.0])
    else:
        direction = np.array([xy[0] / nrm, xy[1] / nrm, 0.0])
    return site.xyz_A + standoff_A * direction


def clash_probability(
    a: DockingSite,
    b: DockingSite,
    radius_a_A: float,
    radius_b_A: float,
    cross_covariance: np.ndarray | None = None,
    standoff_a_A: float | None = None,
    standoff_b_A: float | None = None,
) -> float:
    """P(||X_a - X_b|| < R_a + R_b) under local Gaussian uncertainty.

    If cross_covariance is Cov(X_a, X_b), distance variance uses
    Σ_a + Σ_b − Σ_ab − Σ_abᵀ. Omitting it treats the sites as independent
    and overstates distance noise when they share helical-parameter error.
    The default standoff equals the payload radius, which keeps a sphere
    tangent to the junction. ``steric_report`` passes the linker RMS instead.
    """
    off_a = radius_a_A if standoff_a_A is None else standoff_a_A
    off_b = radius_b_A if standoff_b_A is None else standoff_b_A
    ca, cb = payload_center(a, off_a), payload_center(b, off_b)
    delta = ca - cb
    dist = float(np.linalg.norm(delta))
    sigma = a.covariance_A2 + b.covariance_A2
    if cross_covariance is not None:
        cross = np.asarray(cross_covariance, dtype=float)
        sigma = sigma - cross - cross.T
    sigma = 0.5 * (sigma + sigma.T)
    contact = radius_a_A + radius_b_A
    if dist < 1e-9:
        return 1.0
    u = delta / dist
    var_d = float(u @ sigma @ u)
    std = np.sqrt(max(var_d, 1e-12))
    return float(norm.cdf((contact - dist) / std))


def clash_probability_mc(
    a: DockingSite,
    b: DockingSite,
    radius_a_A: float,
    radius_b_A: float,
    n_samples: int = 4000,
    rng: np.random.Generator | None = None,
) -> float:
    rng = rng or np.random.default_rng(0)
    offset_a = payload_center(a, radius_a_A) - a.xyz_A
    offset_b = payload_center(b, radius_b_A) - b.xyz_A
    xa = rng.multivariate_normal(a.xyz_A, a.covariance_A2, size=n_samples) + offset_a
    xb = rng.multivariate_normal(b.xyz_A, b.covariance_A2, size=n_samples) + offset_b
    d = np.linalg.norm(xa - xb, axis=1)
    return float(np.mean(d < (radius_a_A + radius_b_A)))


def scaffold_overlap_probability(
    site: DockingSite,
    payload_radius_A: float,
    cloud_A: np.ndarray,
    standoff_A: float | None = None,
    ca_exclusion_A: float = 0.0,
) -> float:
    """P(a deposited Cα lies inside the payload sphere).

    ``ca_exclusion_A`` inflates every Cα into a sphere of that radius to
    stand in for side chains and backbone atoms, so the payload surface must
    clear the scaffold by ``payload_radius_A + ca_exclusion_A``. The default
    0.0 keeps the Cα-point behaviour. No sourced value for this radius has
    been retrieved, so it is a caller choice and is never defaulted here.

    ``cloud_A`` is the placed consensus repeat, in Å. The comparison is
    the distance from the payload center to the nearest Cα. Side chains
    are not in the cloud, so this understates the excluded volume.
    """
    offset = payload_radius_A if standoff_A is None else standoff_A
    centre = payload_center(site, offset)
    distances = np.linalg.norm(cloud_A - centre, axis=1)
    nearest = int(np.argmin(distances))
    dist = float(distances[nearest])
    if dist < 1e-9:
        return 1.0
    direction = centre - cloud_A[nearest]
    unit = direction / dist
    variance = float(unit @ site.covariance_A2 @ unit)
    std = np.sqrt(max(variance, 1e-12))
    if ca_exclusion_A < 0:
        raise ValueError("ca_exclusion_A must be non-negative")
    return float(norm.cdf((payload_radius_A + ca_exclusion_A - dist) / std))


@dataclass
class PairClash:
    i: int
    j: int
    distance_A: float
    contact_A: float
    p_clash: float


@dataclass
class StericReport:
    pairs: list[PairClash]
    p_any_payload_clash: float
    p_scaffold_clash: list[float]
    p_any_instability: float
    method: str = "delta_method_ca_envelope"
    provenance: str = "literature_placeholder"


def steric_report(
    geom: CtprGeometry,
    indices: list[int],
    radii_A: list[float],
    standoff_A: list[float] | None = None,
    ca_exclusion_A: float = 0.0,
) -> StericReport:
    if len(indices) != len(radii_A):
        raise ValueError("indices and radii must match")
    if standoff_A is None:
        standoffs = [LINKER_SIGMA_A.value] * len(indices)
    else:
        if len(standoff_A) != len(indices):
            raise ValueError("standoffs and indices must match")
        standoffs = [float(value) for value in standoff_A]
    sites = [geom.site(i) for i in indices]
    cloud = placed_ca_cloud(geom.n_repeats, geom.rise_A, geom.rotation_rad)
    pairs: list[PairClash] = []
    p_survive = 1.0
    for a in range(len(sites)):
        for b in range(a + 1, len(sites)):
            dist = float(
                np.linalg.norm(
                    payload_center(sites[a], standoffs[a] + radii_A[a])
                    - payload_center(sites[b], standoffs[b] + radii_A[b])
                )
            )
            contact = radii_A[a] + radii_A[b]
            p = clash_probability(
                sites[a],
                sites[b],
                radii_A[a],
                radii_A[b],
                cross_covariance=geom.cross_covariance(indices[a], indices[b]),
                standoff_a_A=standoffs[a] + radii_A[a],
                standoff_b_A=standoffs[b] + radii_A[b],
            )
            pairs.append(
                PairClash(
                    i=indices[a],
                    j=indices[b],
                    distance_A=dist,
                    contact_A=contact,
                    p_clash=p,
                )
            )
            p_survive *= 1.0 - p
    p_scaf = [
        scaffold_overlap_probability(
            site, radius, cloud, standoff_A=offset + radius, ca_exclusion_A=ca_exclusion_A
        )
        for site, radius, offset in zip(sites, radii_A, standoffs)
    ]
    for p in p_scaf:
        p_survive *= 1.0 - p
    p_any_pair = 1.0 - float(np.prod([1.0 - p.p_clash for p in pairs])) if pairs else 0.0
    return StericReport(
        pairs=pairs,
        p_any_payload_clash=p_any_pair,
        p_scaffold_clash=p_scaf,
        p_any_instability=1.0 - p_survive,
    )
