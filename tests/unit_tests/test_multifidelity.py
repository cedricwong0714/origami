"""Two-fidelity GP. A passing test is execution, not a validated model."""

import numpy as np
import pytest

from src.gp_model.multifidelity import (
    SIGMA_NOISE_DRY,
    MultiFidelityGP,
    coregionalization,
    matern52_ard,
)


def test_matern52_is_one_on_the_diagonal_and_psd():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(12, 3))
    K = matern52_ard(X, X, np.array([1.0, 2.0, 0.5]))
    assert np.allclose(np.diag(K), 1.0)
    assert np.all(np.linalg.eigvalsh(K) > -1e-8)


def test_coregionalization_matches_the_approved_matrix():
    B = coregionalization(2.0, 4.0, 0.5)
    assert B[0, 0] == 4.0 and B[1, 1] == 16.0
    assert B[0, 1] == pytest.approx(4.0)


def test_fit_rejects_unknown_fidelity():
    with pytest.raises(ValueError):
        MultiFidelityGP(n_restarts=1).fit(
            np.zeros((3, 1)), np.array([0, 1, 2]), np.zeros(3)
        )


def test_posterior_shrinks_near_data_and_dry_noise_stays_fixed():
    rng = np.random.default_rng(1)
    x = np.linspace(0, 1, 8).reshape(-1, 1)
    f = np.array([0, 0, 0, 0, 1, 1, 1, 1])
    y = np.sin(2 * np.pi * x[:, 0]) + rng.normal(0, 0.05, 8)
    gp = MultiFidelityGP(n_restarts=2, seed=1).fit(x, f, y)
    assert gp.hyperparameters["sigma_noise_dry_fixed"] == SIGMA_NOISE_DRY
    near = gp.predict(x[4:5], fidelity=1)
    far = gp.predict(np.array([[3.0]]), fidelity=1)
    assert near.std[0] < far.std[0]
    noisy = gp.predict(x[4:5], fidelity=1, include_noise=True)
    assert noisy.std[0] > near.std[0]
