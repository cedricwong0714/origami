"""Physics-informed design engine: CTPR geometry + steric GP/BO loop."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from origami.design_engine.active_learning import NextExperiment, recommend
from origami.design_engine.gp import GPPosterior, ResidualGP
from origami.physical.score import PhysicsReport, physics_report
from origami.priors import DEFAULT_PAYLOAD_RADIUS_A, N_REPEATS_MAX, N_REPEATS_MIN, all_priors


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
