import numpy as np
import pytest

from origami.design_engine.active_learning import recommend
from origami.design_engine.gp import ResidualGP
from origami.engine import ClaspDesignEngine, Observation


def test_bo_does_not_repeat_observed_when_alternatives_exist():
    X = np.arange(4, 13, dtype=float).reshape(-1, 1)
    S = np.exp(-((X.ravel() - 8) ** 2) / 10.0)
    y = S + 0.05
    gp = ResidualGP().fit(np.array([[8.0]]), np.array([y[4]]), np.array([S[4]]), optimize=False)
    post = gp.predict(X, S)
    nxt = recommend(X, post, S, p_instability=np.zeros(len(X)), observed={8}, acquisition="ucb")
    assert nxt.n_repeats != 8


def test_engine_recommends_integer_in_library():
    eng = ClaspDesignEngine(payload_radii_A=[16.0, 16.0], n_min=4, n_max=14)
    eng.add_observation(Observation(n_repeats=6, y=0.4, source="user_entered"))
    eng.add_observation(Observation(n_repeats=10, y=0.7, source="user_entered"))
    result = eng.run()
    assert result.next_experiment.n_repeats in result.candidates
    assert result.next_experiment.n_repeats not in {6, 10}
    assert result.evidence_level == "computationally_evaluated"
    assert all("literature_placeholder" in line or "calibrated=False" in line for line in result.priors)


def test_engine_two_user_points_stay_on_observation_scale():
    eng = ClaspDesignEngine(payload_radii_A=[18.0, 18.0], n_min=4, n_max=16)
    eng.add_observation(Observation(n_repeats=6, y=0.35, source="user_entered"))
    eng.add_observation(Observation(n_repeats=12, y=0.8, source="user_entered"))
    result = eng.run()
    assert np.all(np.isfinite(result.posterior.mean))
    assert np.all(result.posterior.std >= 0)
    assert np.max(np.abs(result.posterior.mean)) < 20.0
    # Interpolated at the observed integers: residual GP should recover y.
    idx = {n: i for i, n in enumerate(result.candidates)}
    assert result.posterior.mean[idx[6]] == pytest.approx(0.35, abs=0.15)
    assert result.posterior.mean[idx[12]] == pytest.approx(0.8, abs=0.15)


def test_engine_physics_only_still_runs():
    result = ClaspDesignEngine(n_min=5, n_max=9).run()
    assert result.posterior.mean.shape == (5,)
    assert result.next_experiment.n_repeats in range(5, 10)
    assert result.evidence_level == "literature_supported"
