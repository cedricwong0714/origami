import numpy as np

from origami.design_engine.gp import ResidualGP as GpA
from origami.gp_protocol import predict_mean_std
from src.gp_model.residual_gp import ResidualGP as GpB

X = np.linspace(0, 1, 6).reshape(-1, 1)
S = 1.0 + X.ravel()
Y = S + 0.3 + 0.05 * np.sin(5 * X.ravel())


def test_both_families_give_same_shapes():
    a = GpA().fit(X, Y, S)
    b = GpB().fit(X, Y, S)
    ra, rb = predict_mean_std(a, X, S), predict_mean_std(b, X, S)
    for r in (ra, rb):
        assert r["mean"].shape == r["std"].shape == (6,)
        assert np.all(r["std"] >= 0)
    assert ra["noise_included"] is True and rb["noise_included"] is False


def test_both_track_the_data_they_were_fit_on():
    for gp in (GpA().fit(X, Y, S), GpB().fit(X, Y, S)):
        r = predict_mean_std(gp, X, S)
        assert np.max(np.abs(r["mean"] - Y)) < 0.2
