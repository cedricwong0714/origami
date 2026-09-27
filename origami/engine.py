"""Physics-informed design engine: CTPR geometry + steric GP/BO loop."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from origami.design_engine.active_learning import NextExperiment, recommend
from origami.design_engine.gp import GPPosterior, ResidualGP
from origami.io.payloads import PayloadRecord, load_payloads
from origami.io.signal_pairs import SignalPair, default_cam_m13_pair
from origami.mechanisms.intermediate_transfer import simulate_from_ceff
from origami.physical.geometry import CANONICAL_GEOMETRY_PRIOR_ID, build_ctpr
from origami.physical.linkers import gaussian_chain_ceff
from origami.physical.recruitment import occupancy_for_pair, recruitment_occupancy
from origami.physical.score import PhysicsReport, physics_report
from origami.physical.steric import payload_center, steric_report
from origami.priors import (
    CAM_M13_KD_M,
    DEFAULT_PAYLOAD_RADIUS_A,
    N_REPEATS_MAX,
    N_REPEATS_MIN,
    all_priors,
)
from origami.report import DesignReport, assemble_report
from src.core.ctpr_geometry import CTPR_RISE_NM, PERSISTENCE_LENGTH_NM

# Id of the peptide Kd in origami.priors.CAM_M13_KD_M. Not a fusion measurement.
_PRIOR_KD_ID = "cam_m13_peptide_0.19nM"


@dataclass
class Observation:
    n_repeats: int
    y: float
    source: str = "user_entered"
    units: str = "relative_output"
    notes: str = "Not a wet-lab record unless source='wet_lab'."


@dataclass
class EngineResult:
    candidates: list[int]
    reports: dict[int, PhysicsReport]
    physics_scores: np.ndarray
    p_instability: np.ndarray
    posterior: GPPosterior
    next_experiment: NextExperiment
    observations: list[Observation]
    priors: list[str] = field(default_factory=list)
    evidence_level: str = "literature_supported"


class ClaspDesignEngine:
    """Evaluate a discrete CTPR library with physics, then residual GP + BO."""

    def __init__(
        self,
        payload_radii_A: list[float] | None = None,
        n_min: int = N_REPEATS_MIN,
        n_max: int = N_REPEATS_MAX,
        acquisition: str = "ucb",
    ) -> None:
        self.payload_radii_A = payload_radii_A or [
            DEFAULT_PAYLOAD_RADIUS_A.value,
            DEFAULT_PAYLOAD_RADIUS_A.value,
        ]
        self.n_min = n_min
        self.n_max = n_max
        self.acquisition = acquisition
        self.observations: list[Observation] = []

    def add_observation(self, obs: Observation) -> None:
        if obs.n_repeats < self.n_min or obs.n_repeats > self.n_max:
            raise ValueError("observation n_repeats outside the candidate library")
        self.observations.append(obs)

    def evaluate_one(self, n_repeats: int) -> PhysicsReport:
        indices = [0, n_repeats - 1]
        if len(self.payload_radii_A) != 2:
            # place payloads evenly along the solenoid
            k = len(self.payload_radii_A)
            indices = [int(round(i * (n_repeats - 1) / (k - 1))) for i in range(k)]
        return physics_report(n_repeats, payload_indices=indices, radii_A=self.payload_radii_A)

    def run(self) -> EngineResult:
        candidates = list(range(self.n_min, self.n_max + 1))
        reports = {n: self.evaluate_one(n) for n in candidates}
        S = np.array([reports[n].physics_score for n in candidates])
        p_inst = np.array([reports[n].steric.p_any_instability for n in candidates])
        X_all = np.array(candidates, dtype=float).reshape(-1, 1)

        gp = ResidualGP()
        if self.observations:
            X = np.array([[o.n_repeats] for o in self.observations], dtype=float)
            y = np.array([o.y for o in self.observations], dtype=float)
            S_obs = np.array([reports[o.n_repeats].physics_score for o in self.observations])
            gp.fit(X, y, S_obs, optimize=len(self.observations) >= 3)
        posterior = gp.predict(X_all, S)

        observed = {o.n_repeats for o in self.observations}
        nxt = recommend(
            X_all,
            posterior,
            S,
            p_inst,
            observed=observed,
            acquisition=self.acquisition,
        )
        prior_lines = [
            f"{p.name}={p.value} {p.units} (σ={p.sigma}, {p.provenance}, calibrated={p.calibrated})"
            for p in all_priors()
        ]
        evidence = "literature_supported"
        if any(o.source == "wet_lab" for o in self.observations):
            evidence = "parts_validated" if len(self.observations) >= 3 else "computationally_evaluated"
        elif self.observations:
            evidence = "computationally_evaluated"
        return EngineResult(
            candidates=candidates,
            reports=reports,
            physics_scores=S,
            p_instability=p_inst,
            posterior=posterior,
            next_experiment=nxt,
            observations=list(self.observations),
            priors=prior_lines,
            evidence_level=evidence,
        )


def _lookup(obj: object, name: str) -> Any:
    """Read one field from a mapping or an object. Missing fields are None."""
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


def _as_payload_records(payloads: Sequence[object]) -> list[PayloadRecord]:
    """Accept ``PayloadRecord`` objects or dict rows.

    Dict rows are parsed by ``load_payloads``. A missing ``radius_A`` or
    ``linker_sigma_A`` raises there. Neither field is replaced with
    ``DEFAULT_PAYLOAD_RADIUS_A`` or ``LINKER_SIGMA_A``.
    """
    items = list(payloads)
    if items and all(isinstance(item, PayloadRecord) for item in items):
        return [item for item in items if isinstance(item, PayloadRecord)]
    if items and all(isinstance(item, dict) for item in items):
        rows = [item for item in items if isinstance(item, dict)]
        return load_payloads(rows)
    raise TypeError(
        "payloads must be PayloadRecord objects or dict rows accepted by load_payloads"
    )


def _resolve_payloads(
    n_repeats: int,
    payloads: Sequence[object] | None,
) -> tuple[list[int], list[float], list[float | None] | None]:
    """Repeat indices, radii in Å, and linker widths in Å.

    Omitted payloads keep the engine default: one payload on each end repeat,
    both using ``DEFAULT_PAYLOAD_RADIUS_A``. Linker width is then left unset
    so Gaussian-chain ``C_eff`` uses ``LINKER_SIGMA_A``.

    A supplied payload must already carry ``repeat_index``, ``radius_A``, and
    ``linker_sigma_A``. Those are not filled in.
    """
    if not payloads:
        radius = DEFAULT_PAYLOAD_RADIUS_A.value
        return [0, n_repeats - 1], [radius, radius], None
    indices: list[int] = []
    radii: list[float] = []
    sigmas: list[float | None] = []
    for payload in _as_payload_records(payloads):
        payload_id = payload.payload_id or "payload"
        repeat_index_i = int(payload.repeat_index)
        if repeat_index_i < 0 or repeat_index_i >= n_repeats:
            raise ValueError(
                f"payload {payload_id}: repeat_index {repeat_index_i} "
                f"is outside 0..{n_repeats - 1}"
            )
        radius_f = float(payload.radius_A)
        if not math.isfinite(radius_f) or radius_f <= 0:
            raise ValueError(f"payload {payload_id}: radius_A must be > 0")
        linker_f = float(payload.linker_sigma_A)
        if not math.isfinite(linker_f) or linker_f <= 0:
            raise ValueError(f"payload {payload_id}: linker_sigma_A must be > 0")
        indices.append(repeat_index_i)
        radii.append(radius_f)
        sigmas.append(linker_f)
    return indices, radii, sigmas


def _pair_linker_sigma_A(
    sigmas: list[float | None] | None,
    a: int,
    b: int,
) -> float | None:
    """Linker width for one pair, in Å.

    Each payload linker is its own Gaussian chain, so the variances add.
    If either payload omitted ``linker_sigma_A``, return None. The linker
    model then uses ``LINKER_SIGMA_A``. The missing width is not invented.
    """
    if sigmas is None:
        return None
    left, right = sigmas[a], sigmas[b]
    if left is None or right is None:
        return None
    if left <= 0 or right <= 0:
        raise ValueError("linker_sigma_A must be > 0 when provided")
    return float(math.hypot(left, right))


def _supplied_rate(
    explicit: float | None,
    names: tuple[str, ...],
    carriers: Sequence[object],
) -> float | None:
    """Use an explicit argument, else the first supplied field. Never invent one."""
    if explicit is not None:
        return float(explicit)
    for obj in carriers:
        for name in names:
            value = _lookup(obj, name)
            if value is not None:
                return float(value)
    return None


def _signal_binding(
    signal_pair: object | None,
) -> tuple[float, float, float | None, list[str]]:
    """Kd (M), Kd sigma (M), optional kon (1/(M·s)), and warnings.

    With no signal pair, Kd is ``CAM_M13_KD_M``. kon is never filled in.
    A caller Kd without ``kd_sigma_M`` does not inherit the peptide sigma
    unless the Kd is that peptide value.
    """
    notes: list[str] = []
    if signal_pair is None:
        notes.append(
            "Recruitment Kd is origami.priors.CAM_M13_KD_M "
            f"({CAM_M13_KD_M.value} M), prior id {_PRIOR_KD_ID}."
        )
        return CAM_M13_KD_M.value, CAM_M13_KD_M.sigma, None, notes
    kd = _lookup(signal_pair, "kd_M")
    if kd is None:
        raise ValueError("signal_pair.kd_M is required when a signal pair is passed")
    kd_f = float(kd)
    if not math.isfinite(kd_f) or kd_f <= 0:
        raise ValueError("signal_pair.kd_M must be > 0")
    kd_source = _lookup(signal_pair, "kd_source")
    if kd_source is None:
        notes.append(
            "Signal pair has no kd_source. The caller Kd is used without a source string."
        )
    else:
        notes.append(f"Signal-pair Kd source: {kd_source}")
    sigma = _lookup(signal_pair, "kd_sigma_M")
    if sigma is None:
        if math.isclose(kd_f, CAM_M13_KD_M.value, rel_tol=1e-12, abs_tol=0.0):
            sigma_f = CAM_M13_KD_M.sigma
        else:
            sigma_f = 0.0
            notes.append(
                "Caller Kd has no kd_sigma_M. The occupancy interval is a point. "
                "The Biochemistry 2006 peptide sigma was not applied to a different Kd."
            )
    else:
        sigma_f = float(sigma)
    kon = _lookup(signal_pair, "kon_per_M_s")
    kon_f = None if kon is None else float(kon)
    return kd_f, sigma_f, kon_f, notes


def _evaluate_occupancy(
    signal_pair: object | None,
    c_free_M: float | None,
) -> tuple[Any, float | None, list[str]]:
    """Steady-state occupancy, supplied kon, and provenance notes.

    ``SignalPair`` values, and the default CaM–M13 pair when no pair is
    passed, go through ``occupancy_for_pair``. That function keeps a missing
    ``kd_sigma_M`` at zero width. It does not copy ``CAM_M13_KD_M.sigma``.
    The default pair's kon is None. A time course is integrated only when
    the caller supplied kon and ``c_free_M``.

    Objects that are not a ``SignalPair`` keep the previous direct
    ``recruitment_occupancy`` call. kon is still taken only from the object.
    """
    notes: list[str] = []
    if signal_pair is None or isinstance(signal_pair, SignalPair):
        pair = default_cam_m13_pair() if signal_pair is None else signal_pair
        if signal_pair is None:
            notes.append(
                "Recruitment Kd is default_cam_m13_pair() from "
                f"origami.priors.CAM_M13_KD_M ({pair.kd_M} M), prior id {_PRIOR_KD_ID}. "
                "kon is absent on that pair and is not invented."
            )
        else:
            notes.append(f"Signal-pair Kd source: {pair.kd_source}")
        kon = pair.kon_per_M_s
        if c_free_M is None:
            notes.append(
                "c_free_M was not supplied. Recruitment was evaluated with the signal "
                "gate off. No physiological free concentration was assumed."
            )
            occupancy = occupancy_for_pair(pair, c_free_M=0.0, signal_on=False)
            if kon is not None:
                notes.append(
                    "kon_per_M_s was supplied, but the time course was not integrated "
                    "because c_free_M is missing."
                )
        else:
            occupancy = occupancy_for_pair(pair, c_free_M=float(c_free_M), signal_on=True)
        return occupancy, kon, notes

    kd_M, kd_sigma_M, kon, kd_notes = _signal_binding(signal_pair)
    notes.extend(kd_notes)
    if c_free_M is None:
        notes.append(
            "c_free_M was not supplied. Recruitment was evaluated with the signal "
            "gate off. No physiological free concentration was assumed."
        )
        occupancy = recruitment_occupancy(
            c_free_M=0.0,
            kon_per_M_s=None,
            kd_M=kd_M,
            kd_sigma_M=kd_sigma_M,
            signal_on=False,
        )
        if kon is not None:
            notes.append(
                "kon_per_M_s was supplied, but the time course was not integrated "
                "because c_free_M is missing."
            )
    else:
        occupancy = recruitment_occupancy(
            c_free_M=float(c_free_M),
            kon_per_M_s=kon,
            kd_M=kd_M,
            kd_sigma_M=kd_sigma_M,
            signal_on=True,
        )
    return occupancy, kon, notes


def run_design(
    design_id: str,
    n_repeats: int,
    payloads: Sequence[object] | None = None,
    signal_pair: object | None = None,
    observations: Sequence[Observation] | None = None,
    c_free_M: float | None = None,
    k_cat_per_s: float | None = None,
    k_m_M: float | None = None,
    k_escape_per_s: float | None = None,
    v_prod_M_per_s: float | None = None,
) -> DesignReport:
    """Score one scaffold and return a ``DesignReport``.

    This is the single design interface. Payload rows come from
    ``origami.io`` (``PayloadRecord`` or ``load_payloads``). A ``SignalPair``
    is scored with ``occupancy_for_pair``. With no payloads, the design uses
    one payload on each end repeat. With no signal pair, steady-state
    occupancy uses ``default_cam_m13_pair()`` and does not invent kon.

    Coordinates come from ``build_ctpr`` (canonical screw, ångströms).
    Steric clash uses each payload ``radius_A``. Gaussian-chain ``C_eff``
    uses each payload ``linker_sigma_A`` when payloads are passed.
    ``kon``, ``k_cat``, ``K_m``, ``k_escape``, and ``v_prod`` are used only
    when the caller supplies them. Missing rates are listed in ``omitted``.
    If those Damköhler inputs are missing, ``da`` and ``p_capture`` stay None.

    ``assemble_report`` stores ``calibrated=False`` with evidence_source
    ``"none"``. A passing call is not a wet-lab validation. The report has
    no occupancy time course. ``to_dict()`` is the JSON mapping.
    """
    if isinstance(n_repeats, bool) or not isinstance(n_repeats, int):
        raise ValueError("n_repeats must be an integer")
    warnings: list[str] = []
    indices, radii, sigmas = _resolve_payloads(n_repeats, payloads)
    contour_nm = n_repeats * CTPR_RISE_NM
    if contour_nm > PERSISTENCE_LENGTH_NM:
        warnings.append(
            f"Scaffold contour {contour_nm:.2f} nm exceeds persistence length "
            f"{PERSISTENCE_LENGTH_NM} nm from src.core.ctpr_geometry. "
            "Rigid screw coordinates are an approximation."
        )

    geom = build_ctpr(n_repeats)
    if geom.provenance != CANONICAL_GEOMETRY_PRIOR_ID:
        raise RuntimeError("scaffold geometry was not built from the canonical prior")
    steric = steric_report(geom, indices, radii)
    if steric.p_any_instability < 0:
        raise RuntimeError("clash probability cannot be negative")

    pair_ceffs = []
    for a in range(len(indices)):
        for b in range(a + 1, len(indices)):
            i, j = indices[a], indices[b]
            distance_A = float(
                np.linalg.norm(
                    payload_center(geom.site(i), radii[a])
                    - payload_center(geom.site(j), radii[b])
                )
            )
            pair_ceffs.append(
                gaussian_chain_ceff(distance_A, _pair_linker_sigma_A(sigmas, a, b))
            )
    if sigmas is not None and any(s is None for s in sigmas) and any(s is not None for s in sigmas):
        warnings.append(
            "Some payloads omitted linker_sigma_A. Those pairs use LINKER_SIGMA_A. "
            "The missing width was not invented."
        )

    design_report = physics_report(n_repeats, payload_indices=indices, radii_A=radii)
    warnings.extend(design_report.warnings)
    if payloads and indices != [0, n_repeats - 1]:
        warnings.append(
            "This design is scored at the caller-supplied repeat indices. "
            "recommend() still scans the repeat-length library with the engine's "
            "existing payload placement."
        )

    occupancy, kon, kd_notes = _evaluate_occupancy(signal_pair, c_free_M)
    warnings.extend(kd_notes)
    warnings.extend(occupancy.warnings)

    carriers: list[object] = list(payloads or [])
    if signal_pair is not None:
        carriers.append(signal_pair)
    k_cat = _supplied_rate(k_cat_per_s, ("k_cat_per_s", "k_cat"), carriers)
    k_m = _supplied_rate(k_m_M, ("k_m_M", "K_m"), carriers)
    k_escape = _supplied_rate(k_escape_per_s, ("k_escape_per_s", "k_escape"), carriers)
    v_prod = _supplied_rate(v_prod_M_per_s, ("v_prod_M_per_s", "v_prod"), carriers)
    omitted: list[str] = []
    if kon is None:
        omitted.append("kon")
    if k_cat is None:
        omitted.append("k_cat")
    if k_m is None:
        omitted.append("K_m")
    if k_escape is None:
        omitted.append("k_escape")
    if v_prod is None:
        omitted.append("v_prod")
    pair_distances_A: dict[str, float] = {}
    p_clash: dict[str, float] = {}
    c_eff_M: dict[str, float] = {}
    if len(steric.pairs) != len(pair_ceffs):
        raise RuntimeError("steric pairs and effective concentrations diverged")
    for clash, ceff in zip(steric.pairs, pair_ceffs):
        key = f"{clash.i}-{clash.j}"
        pair_distances_A[key] = float(clash.distance_A)
        p_clash[key] = float(clash.p_clash)
        c_eff_M[key] = float(ceff.C_eff_M)

    rates_ready = None not in (k_cat, k_m, k_escape, v_prod)
    da: float | None = None
    p_capture: float | None = None
    if rates_ready:
        if k_cat is None or k_m is None or k_escape is None or v_prod is None:
            raise RuntimeError("rates were marked ready but a value is missing")
        if k_m <= 0:
            raise ValueError("K_m must be > 0")
        if not c_eff_M:
            warnings.append(
                "k_cat, K_m, k_escape, and v_prod were supplied, but there is no "
                "payload pair, so intermediate transfer was not simulated."
            )
        else:
            # k_cat is 1/s and K_m is M, so the ratio is 1/(M·s). No conversion.
            mean_c_eff_M = float(sum(c_eff_M.values()) / len(c_eff_M))
            transfer = simulate_from_ceff(
                v_prod_M_per_s=v_prod,
                k_escape_per_s=k_escape,
                kcat_over_km_per_M_s=k_cat / k_m,
                c_eff_M=mean_c_eff_M,
            )
            warnings.extend(transfer.warnings)
            da = float(transfer.da)
            p_capture = float(transfer.p_capture)
    if da is None and "k_escape" not in omitted and "k_capture" not in omitted:
        # Capture was not computed. assemble_report requires that omission
        # to be named when da stays unset.
        omitted.append("k_capture")

    if payloads and len(radii) >= 2:
        engine = ClaspDesignEngine(payload_radii_A=list(radii))
    else:
        engine = ClaspDesignEngine()
    for obs in observations or []:
        engine.add_observation(obs)
    library = engine.run()
    if library.next_experiment.n_repeats < N_REPEATS_MIN:
        raise RuntimeError("recommend returned a repeat count outside the library")

    return assemble_report(
        design_id=design_id,
        prior_geometry_id=geom.provenance,
        prior_kd_id=_PRIOR_KD_ID,
        n_repeats=n_repeats,
        pair_distances_A=pair_distances_A,
        p_clash=p_clash,
        c_eff_M=c_eff_M,
        theta_ss=occupancy.theta_ss,
        theta_95_lower=occupancy.theta_95_lower,
        theta_95_upper=occupancy.theta_95_upper,
        da=da,
        p_capture=p_capture,
        gp_mean=[float(value) for value in library.posterior.mean],
        gp_std=[float(value) for value in library.posterior.std],
        next_n=int(library.next_experiment.n_repeats),
        calibrated=False,
        warnings=warnings,
        omitted=omitted,
        evidence_source="none",
    )
