import numpy as np

from origami.design_engine.gp import GPHyperparameters, ResidualGP


def test_variance_shrinks_near_observations():
    rng = np.random.default_rng(0)
    X = np.linspace(4, 12, 7).reshape(-1, 1)
    S = 0.1 * X.ravel()
    y = S + 0.4 * np.sin(X.ravel()) + 0.01 * rng.normal(size=len(X))
    gp = ResidualGP().fit(X, y, S, optimize=True)
    post = gp.predict(np.array([[8.0], [30.0]]), np.array([0.8, 3.0]))
    assert post.std[0] < post.std[1]
    assert post.interpolated[0]
    assert not post.interpolated[1]


def test_residual_is_not_a_straight_line_through_physics():
    X = np.linspace(0.0, 6.0, 9).reshape(-1, 1)
    S = np.zeros(len(X))
    y = np.sin(X.ravel())
    gp = ResidualGP(GPHyperparameters(lengthscale=1.2, variance=1.0, noise=1e-4))
    gp.fit(X, y, S, optimize=False)
    xs = np.linspace(0.0, 6.0, 40).reshape(-1, 1)
    post = gp.predict(xs, np.zeros(len(xs)))
    err = float(np.mean(np.abs(post.mean - np.sin(xs.ravel()))))
    lin = np.polyval(np.polyfit(X.ravel(), y, 1), xs.ravel())
    lin_err = float(np.mean(np.abs(lin - np.sin(xs.ravel()))))
    assert err < 0.12
    assert err < 0.5 * lin_err


def test_empty_gp_returns_physics_mean_with_prior_variance():
    gp = ResidualGP()
    post = gp.predict(np.array([[5.0], [10.0]]), np.array([1.2, 2.4]))
    assert np.allclose(post.mean, [1.2, 2.4])
    assert np.all(post.std > 0)


def test_two_collinear_physics_scores_do_not_explode_alpha():
    """Two observations with almost equal S must not fit a huge slope."""
    X = np.array([[6.0], [12.0]])
    S = np.array([1.0000001, 1.0000002])
    y = np.array([0.35, 0.80])
    gp = ResidualGP().fit(X, y, S, optimize=False)
    post = gp.predict(np.array([[4.0], [6.0], [16.0]]), np.array([0.2, 1.0, 1.1]))
    assert np.all(np.isfinite(post.mean))
    assert np.max(np.abs(post.mean)) < 20.0
    assert abs(gp.alpha - 1.0) < 1e-12
