"""Structural report for one CTPR screw.

AlphaFold, ESMFold, and a PyMOL session return one coordinate set.
This module reports how that screw changes with repeat count: pitch,
phase between docking sites, curvature, and whether the contour is
still inside the rigid-rod persistence length.

Every length on the screw comes from ``CtprGeometry``. The deposited
block compares that screw with the C-alpha fit in
``origami.physical.deposited``. Distance intervals propagate the
Jacobian: rise, twist, and docking-radius sigmas are the deposited
sample standard deviations. They are not a calibrated experimental error.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from origami.physical.deposited import DEPOSITED_KEYS, deposited_summary
from origami.physical.geometry import CANONICAL_GEOMETRY_PRIOR_ID, CtprGeometry
from origami.priors import CTPR_SCAFFOLD_RADIUS_A
from src.core.ctpr_geometry import PERSISTENCE_LENGTH_NM, wlc_mean_square_end_to_end

# Standard-normal 97.5% quantile. Same factor as Parameter.interval_95.
# Not a biological constant.
_NORMAL_97_5 = 1.96

# 1 nm = 10 Å. Same boundary conversion as origami.physical.geometry.
_NM_TO_A = 10.0

_CONTOUR_DEFINITION = "n_repeats * rise_per_repeat"
_UNCERTAINTY_MODEL = (
    "delta_method_deposited_rise_twist_and_junction_radius_sample_std"
)

STRUCTURE_KEYS = frozenset(
    {
        "provenance",
        "calibrated",
        "n_repeats",
        "rise_A",
        "twist_rad",
        "docking_radius_A",
        "scaffold_radius_A",
        "pitch_A",
        "repeats_per_turn",
        "axial_span_A",
        "contour_A",
        "contour_nm",
        "contour_definition",
        "persistence_length_nm",
        "persistence_length_A",
        "wlc_end_to_end_rms_A",
        "wlc_end_to_end_rms_nm",
        "rigid_screw",
        "docking_curvature_per_A",
        "docking_torsion_per_A",
        "backbone_curvature_per_A",
        "backbone_torsion_per_A",
        "pairs",
        "deposited",
        "warnings",
        "uncertainty_model",
    }
)
PAIR_STRUCTURE_KEYS = frozenset(
    {
        "i",
        "j",
        "delta_repeats",
        "phase_rad",
        "facing_cosine",
        "chord_A",
        "axial_A",
        "chord_sigma_A",
        "chord_95_low_A",
        "chord_95_high_A",
        "linearization_crosses_zero",
    }
)


@dataclass(frozen=True)
class PairStructure:
    """Geometry of two docking sites on the screw.

    ``phase_rad`` is ``(j - i) * twist`` and is not folded into
    ``[-π, π]``. ``facing_cosine`` is the dot product of the radial
    axes. A value of 1 means the sites point the same way around the
    helix. A value of -1 means they point opposite ways.
    """

    i: int
    j: int
    delta_repeats: int
    phase_rad: float
    facing_cosine: float
    chord_A: float
    axial_A: float
    chord_sigma_A: float
    chord_95_low_A: float
    chord_95_high_A: float
    linearization_crosses_zero: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "i": int(self.i),
            "j": int(self.j),
            "delta_repeats": int(self.delta_repeats),
            "phase_rad": float(self.phase_rad),
            "facing_cosine": float(self.facing_cosine),
            "chord_A": float(self.chord_A),
            "axial_A": float(self.axial_A),
            "chord_sigma_A": float(self.chord_sigma_A),
            "chord_95_low_A": float(self.chord_95_low_A),
            "chord_95_high_A": float(self.chord_95_high_A),
            "linearization_crosses_zero": bool(self.linearization_crosses_zero),
        }


@dataclass(frozen=True)
class StructuralReport:
    """Screw invariants and site-pair geometry for one scaffold.

    ``calibrated`` is always false. A passing structural report is not
    a crystal structure and not a wet-lab measurement.
    """

    provenance: str
    calibrated: bool
    n_repeats: int
    rise_A: float
    twist_rad: float
    docking_radius_A: float
    scaffold_radius_A: float
    pitch_A: float
    repeats_per_turn: float
    axial_span_A: float
    contour_A: float
    contour_nm: float
    contour_definition: str
    persistence_length_nm: float
    persistence_length_A: float
    wlc_end_to_end_rms_A: float
    wlc_end_to_end_rms_nm: float
    rigid_screw: bool
    docking_curvature_per_A: float
    docking_torsion_per_A: float
    backbone_curvature_per_A: float
    backbone_torsion_per_A: float
    pairs: list[PairStructure]
    deposited: dict[str, object]
    warnings: list[str]
    uncertainty_model: str

    def to_dict(self) -> dict[str, object]:
        return {
            "provenance": self.provenance,
            "calibrated": False,
            "n_repeats": int(self.n_repeats),
            "rise_A": float(self.rise_A),
            "twist_rad": float(self.twist_rad),
            "docking_radius_A": float(self.docking_radius_A),
            "scaffold_radius_A": float(self.scaffold_radius_A),
            "pitch_A": float(self.pitch_A),
            "repeats_per_turn": float(self.repeats_per_turn),
            "axial_span_A": float(self.axial_span_A),
            "contour_A": float(self.contour_A),
            "contour_nm": float(self.contour_nm),
            "contour_definition": self.contour_definition,
            "persistence_length_nm": float(self.persistence_length_nm),
            "persistence_length_A": float(self.persistence_length_A),
            "wlc_end_to_end_rms_A": float(self.wlc_end_to_end_rms_A),
            "wlc_end_to_end_rms_nm": float(self.wlc_end_to_end_rms_nm),
            "rigid_screw": bool(self.rigid_screw),
            "docking_curvature_per_A": float(self.docking_curvature_per_A),
            "docking_torsion_per_A": float(self.docking_torsion_per_A),
            "backbone_curvature_per_A": float(self.backbone_curvature_per_A),
            "backbone_torsion_per_A": float(self.backbone_torsion_per_A),
            "pairs": [pair.to_dict() for pair in self.pairs],
            "deposited": dict(self.deposited),
            "warnings": list(self.warnings),
            "uncertainty_model": self.uncertainty_model,
        }


def helix_curvature_torsion(radius_A: float, pitch_A: float) -> tuple[float, float]:
    """Curvature and torsion of a circular helix, in 1/Å.

    For ``r(t) = (R cos t, R sin t, b t)`` with ``b = pitch / 2π``,

        κ = R / (R² + b²)
        τ = b / (R² + b²)

    ``pitch_A`` is the axial advance in one full turn. These are
    identities of that curve. They are not fitted to a density map.
    """
    if radius_A <= 0.0:
        raise ValueError("radius_A must be > 0")
    if pitch_A <= 0.0:
        raise ValueError("pitch_A must be > 0")
    axial_per_rad = pitch_A / (2.0 * math.pi)
    denom = radius_A**2 + axial_per_rad**2
    curvature = radius_A / denom
    torsion = axial_per_rad / denom
    return float(curvature), float(torsion)


def _covariance_block(geom: CtprGeometry, i: int, j: int) -> np.ndarray:
    """Jacobian covariance block. This is not the 1e-8-guarded site copy."""
    cov = geom.coord_covariance
    return np.asarray(cov[3 * i : 3 * i + 3, 3 * j : 3 * j + 3], dtype=float)


def chord_sigma_A(geom: CtprGeometry, i: int, j: int) -> float:
    """Delta-method std of the docking-site chord, in Å.

    Variance is ``uᵀ (Σ_ii + Σ_jj − Σ_ij − Σ_ijᵀ) u`` with ``u`` the unit
    chord. ``Σ`` is the helical-parameter Jacobian covariance. Shared
    parameter error can shrink or widen the chord interval: motion that
    moves both sites the same way shrinks it, and motion that moves them
    apart widens it. The blocks are read from ``coord_covariance``.
    """
    if i == j:
        raise ValueError("chord uncertainty needs two distinct sites")
    delta = geom.sites[j].xyz_A - geom.sites[i].xyz_A
    dist = float(np.linalg.norm(delta))
    if dist < 1e-12:
        raise ValueError("docking sites are coincident; chord direction is undefined")
    unit = delta / dist
    cross = _covariance_block(geom, i, j)
    sigma = (
        _covariance_block(geom, i, i)
        + _covariance_block(geom, j, j)
        - cross
        - cross.T
    )
    sigma = 0.5 * (sigma + sigma.T)
    variance = float(unit @ sigma @ unit)
    if variance < 0.0 and variance > -1e-8:
        variance = 0.0
    if variance < 0.0:
        raise ValueError("chord variance is negative; covariance is not usable")
    return float(math.sqrt(variance))


def structural_report(
    geom: CtprGeometry,
    indices: list[int] | None = None,
) -> StructuralReport:
    """Build the structural report for ``geom``.

    ``indices`` selects docking sites. Each unordered pair among them is
    reported once, in increasing index order. Omit ``indices`` to report
    the screw only.

    Contour length uses the same definition as
    ``src.core.ctpr_geometry.generate_scaffold_geometry``:
    ``n_repeats * rise``. Axial span of the docking sites is
    ``(n_repeats - 1) * rise``. Persistence length is
    ``PERSISTENCE_LENGTH_NM`` from that module. The rigid-screw flag is
    true when the contour is at most that persistence length.
    """
    if geom.n_repeats < 1:
        raise ValueError("n_repeats must be >= 1")
    if geom.rise_A <= 0.0 or geom.rotation_rad <= 0.0 or geom.radius_A <= 0.0:
        raise ValueError("rise, twist, and docking radius must be > 0")
    if len(geom.sites) != geom.n_repeats:
        raise ValueError("site count does not match n_repeats")

    warnings: list[str] = []
    if geom.provenance != CANONICAL_GEOMETRY_PRIOR_ID:
        warnings.append(
            "Geometry provenance is not src.core.ctpr_geometry. "
            "Pitch and phase still follow the coordinates that were supplied."
        )

    repeats_per_turn = (2.0 * math.pi) / geom.rotation_rad
    pitch_A = geom.rise_A * repeats_per_turn
    axial_span_A = (geom.n_repeats - 1) * geom.rise_A
    contour_A = geom.n_repeats * geom.rise_A
    contour_nm = contour_A / _NM_TO_A
    persistence_nm = float(PERSISTENCE_LENGTH_NM)
    persistence_A = persistence_nm * _NM_TO_A
    wlc_ms_nm2 = float(wlc_mean_square_end_to_end(contour_nm, persistence_nm))
    wlc_rms_nm = float(math.sqrt(wlc_ms_nm2))
    wlc_rms_A = wlc_rms_nm * _NM_TO_A
    rigid = contour_nm <= persistence_nm
    if not rigid:
        warnings.append(
            f"Scaffold contour {contour_nm:.2f} nm exceeds persistence length "
            f"{persistence_nm} nm from src.core.ctpr_geometry. "
            f"WLC end-to-end RMS is {wlc_rms_nm:.2f} nm. "
            "Rigid screw coordinates are an approximation."
        )

    dock_kappa, dock_tau = helix_curvature_torsion(geom.radius_A, pitch_A)
    backbone_radius_A = float(CTPR_SCAFFOLD_RADIUS_A.value)
    back_kappa, back_tau = helix_curvature_torsion(backbone_radius_A, pitch_A)
    deposited = deposited_summary(
        runtime_rise_A=float(geom.rise_A),
        runtime_twist_deg=float(math.degrees(geom.rotation_rad)),
        runtime_scaffold_radius_A=backbone_radius_A,
        runtime_docking_radius_A=float(geom.radius_A),
    )
    if set(deposited) != DEPOSITED_KEYS:
        raise RuntimeError("deposited geometry summary keys drifted")
    warnings.extend(str(note) for note in deposited["notes"])

    chosen = list(range(geom.n_repeats)) if indices is None else list(indices)
    if len(set(chosen)) != len(chosen):
        raise ValueError("docking indices must be unique")
    for index in chosen:
        if index < 0 or index >= geom.n_repeats:
            raise ValueError(f"docking index {index} is outside 0..{geom.n_repeats - 1}")

    pairs: list[PairStructure] = []
    ordered = sorted(chosen)
    for left in range(len(ordered)):
        for right in range(left + 1, len(ordered)):
            i, j = ordered[left], ordered[right]
            pairs.append(_pair(geom, i, j, warnings))

    return StructuralReport(
        provenance=geom.provenance,
        calibrated=False,
        n_repeats=geom.n_repeats,
        rise_A=float(geom.rise_A),
        twist_rad=float(geom.rotation_rad),
        docking_radius_A=float(geom.radius_A),
        scaffold_radius_A=backbone_radius_A,
        pitch_A=float(pitch_A),
        repeats_per_turn=float(repeats_per_turn),
        axial_span_A=float(axial_span_A),
        contour_A=float(contour_A),
        contour_nm=float(contour_nm),
        contour_definition=_CONTOUR_DEFINITION,
        persistence_length_nm=persistence_nm,
        persistence_length_A=float(persistence_A),
        wlc_end_to_end_rms_A=float(wlc_rms_A),
        wlc_end_to_end_rms_nm=float(wlc_rms_nm),
        rigid_screw=rigid,
        docking_curvature_per_A=dock_kappa,
        docking_torsion_per_A=dock_tau,
        backbone_curvature_per_A=back_kappa,
        backbone_torsion_per_A=back_tau,
        pairs=pairs,
        deposited=deposited,
        warnings=warnings,
        uncertainty_model=_UNCERTAINTY_MODEL,
    )


def _pair(
    geom: CtprGeometry,
    i: int,
    j: int,
    warnings: list[str],
) -> PairStructure:
    delta_n = j - i
    phase = delta_n * geom.rotation_rad
    radial_i = geom.sites[i].orientation[:, 0]
    radial_j = geom.sites[j].orientation[:, 0]
    facing = float(np.dot(radial_i, radial_j))
    chord = float(np.linalg.norm(geom.sites[j].xyz_A - geom.sites[i].xyz_A))
    axial = float(geom.sites[j].xyz_A[2] - geom.sites[i].xyz_A[2])
    expected_axial = delta_n * geom.rise_A
    if not math.isclose(axial, expected_axial, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(
            f"axial separation {axial} Å does not match {delta_n} rises "
            f"of {geom.rise_A} Å"
        )
    sigma = chord_sigma_A(geom, i, j)
    low = chord - _NORMAL_97_5 * sigma
    high = chord + _NORMAL_97_5 * sigma
    crosses = low < 0.0
    if crosses:
        warnings.append(
            f"Linear chord interval for sites {i}-{j} crosses zero. "
            "The Jacobian widths are large relative to this chord, so the "
            "interval is an extrapolation of the linearization."
        )
    if not math.isclose(facing, math.cos(phase), rel_tol=0.0, abs_tol=1e-8):
        raise ValueError(
            f"facing cosine {facing} does not match cos(phase) for sites {i}-{j}"
        )
    return PairStructure(
        i=i,
        j=j,
        delta_repeats=delta_n,
        phase_rad=float(phase),
        facing_cosine=facing,
        chord_A=chord,
        axial_A=axial,
        chord_sigma_A=sigma,
        chord_95_low_A=float(low),
        chord_95_high_A=float(high),
        linearization_crosses_zero=crosses,
    )
