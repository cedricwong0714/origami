"""Probabilistic steric clashes for spherical payloads on an uncertain scaffold.

P(overlap) uses the delta method on ||x_i - x_j|| given Gaussian positional
covariance from the helical-parameter Jacobian. Optional Monte Carlo check.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.stats import norm

from origami.physical.geometry import CtprGeometry, DockingSite
from origami.priors import CTPR_SCAFFOLD_RADIUS_A


def payload_center(site: DockingSite, payload_radius_A: float) -> np.ndarray:
    """Enzyme body sits *outward* of the fusion point, not on top of the solenoid."""
    xy = site.xyz_A[:2]
    nrm = float(np.linalg.norm(xy))
    if nrm < 1e-9:
        direction = np.array([1.0, 0.0, 0.0])
    else:
        direction = np.array([xy[0] / nrm, xy[1] / nrm, 0.0])
    return site.xyz_A + payload_radius_A * direction


def clash_probability(
    a: DockingSite,
    b: DockingSite,
    radius_a_A: float,
    radius_b_A: float,
    cross_covariance: np.ndarray | None = None,
) -> float:
    """P(||X_a - X_b|| < R_a + R_b) under local Gaussian uncertainty.

    If cross_covariance is Cov(X_a, X_b), distance variance uses
    Σ_a + Σ_b − Σ_ab − Σ_abᵀ. Omitting it treats the sites as independent
    and overstates distance noise when they share helical-parameter error.
    """
    ca, cb = payload_center(a, radius_a_A), payload_center(b, radius_b_A)
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
    scaffold_radius_A: float | None = None,
) -> float:
    """Payload sphere vs cylindrical scaffold (axis = z)."""
    r_scaf = CTPR_SCAFFOLD_RADIUS_A.value if scaffold_radius_A is None else scaffold_radius_A
    centre = payload_center(site, payload_radius_A)
    radial = float(np.linalg.norm(centre[:2]))
    # clash if the sphere reaches the cylinder: radial < r_scaf + payload_radius
    var_xy = float(np.trace(site.covariance_A2[:2, :2]) / 2.0)
    std = np.sqrt(max(var_xy, 1e-12))
    return float(norm.cdf((r_scaf + payload_radius_A - radial) / std))


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
    method: str = "delta_method_gaussian"
    provenance: str = "literature_placeholder"


def steric_report(
    geom: CtprGeometry,
    indices: list[int],
    radii_A: list[float],
) -> StericReport:
    if len(indices) != len(radii_A):
        raise ValueError("indices and radii must match")
    sites = [geom.site(i) for i in indices]
    pairs: list[PairClash] = []
    p_survive = 1.0
    for a in range(len(sites)):
        for b in range(a + 1, len(sites)):
            dist = float(
                np.linalg.norm(
                    payload_center(sites[a], radii_A[a]) - payload_center(sites[b], radii_A[b])
                )
            )
            contact = radii_A[a] + radii_A[b]
            p = clash_probability(
                sites[a],
                sites[b],
                radii_A[a],
                radii_A[b],
                cross_covariance=geom.cross_covariance(indices[a], indices[b]),
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
        scaffold_overlap_probability(site, radius)
        for site, radius in zip(sites, radii_A)
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
