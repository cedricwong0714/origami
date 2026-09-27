"""Physics ranking score: local concentration penalized by steric instability.

score = (1 - P_instability) * log10(1 + C_eff / C_ref)

This is still a mechanistic scalar, not a GP. The residual GP sits on top.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from origami.physical.geometry import CtprGeometry, build_ctpr
from origami.physical.linkers import EffectiveConcentration, gaussian_chain_ceff
from origami.physical.steric import StericReport, payload_center, steric_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN


_C_REF_M = 1e-3  # 1 mM reference for a dimensionless log term, not a measured Km


@dataclass
class PhysicsReport:
    n_repeats: int
    payload_indices: list[int]
    geometry: CtprGeometry
    steric: StericReport
    pair_distances_A: dict[tuple[int, int], float]
    ceff: dict[tuple[int, int], EffectiveConcentration]
    physics_score: float
    feasible: bool
    warnings: list[str] = field(default_factory=list)
    evidence_level: str = "literature_supported"
    calibrated: bool = False


def physics_report(
    n_repeats: int,
    payload_indices: list[int] | None = None,
    radii_A: list[float] | None = None,
    clash_refuse: float = 0.85,
) -> PhysicsReport:
    if n_repeats < N_REPEATS_MIN or n_repeats > N_REPEATS_MAX:
        raise ValueError(f"n_repeats must be in [{N_REPEATS_MIN}, {N_REPEATS_MAX}]")
    if payload_indices is None:
        payload_indices = [0, n_repeats - 1]
    if radii_A is None:
        radii_A = [DEFAULT_PAYLOAD_RADIUS_A.value] * len(payload_indices)
    geom = build_ctpr(n_repeats)
    steric = steric_report(geom, payload_indices, radii_A)
    distances: dict[tuple[int, int], float] = {}
    ceffs: dict[tuple[int, int], EffectiveConcentration] = {}
    warnings: list[str] = []
    ceff_terms: list[float] = []
    for a in range(len(payload_indices)):
        for b in range(a + 1, len(payload_indices)):
            i, j = payload_indices[a], payload_indices[b]
            r = float(
                np.linalg.norm(
                    payload_center(geom.site(i), radii_A[a])
                    - payload_center(geom.site(j), radii_A[b])
                )
            )
            distances[(i, j)] = r
            ce = gaussian_chain_ceff(r)
            ceffs[(i, j)] = ce
            ceff_terms.append(ce.C_eff_M)
    mean_ceff = float(sum(ceff_terms) / max(len(ceff_terms), 1)) if ceff_terms else 0.0
    survive = 1.0 - steric.p_any_instability
    score = survive * float(math.log10(1.0 + mean_ceff / _C_REF_M))
    if n_repeats < 3:
        warnings.append("n_repeats below typical designed CTPR repertoire (Kajander et al., 2007).")
    if steric.p_any_payload_clash > 0.5:
        warnings.append(
            "High payload–payload clash probability: clustered enzymes may occlude functional sites."
        )
    if steric.p_any_instability > clash_refuse:
        warnings.append("Design refused as sterically implausible under current literature priors.")
        feasible = False
    else:
        feasible = True
    warnings.append(
        "All structural/kinetic numbers are literature placeholders, not this project's lab data."
    )
    return PhysicsReport(
        n_repeats=n_repeats,
        payload_indices=list(payload_indices),
        geometry=geom,
        steric=steric,
        pair_distances_A=distances,
        ceff=ceffs,
        physics_score=score,
        feasible=feasible,
        warnings=warnings,
    )
