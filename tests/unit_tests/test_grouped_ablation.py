import numpy as np
import pytest

from src.gp_model.ablation import grouped_ablation, spearman


def _data(offset=0.5, n_groups=4, per=5, seed=0):
    rng = np.random.default_rng(seed)
    n = n_groups * per
    x = np.linspace(0.0, 1.0, n)
    ym = 1.0 + 2.0 * x
    y = ym + offset + rng.normal(0, 0.02, n)
    groups = [f"b{i % n_groups}" for i in range(n)]
    return x.reshape(-1, 1), y, ym, groups


def test_gp_reduces_held_out_error_for_a_systematic_offset():
    """A constant physics bias shared across batches is learnable by the GP."""
    X, y, ym, g = _data()
    out = grouped_ablation(X, y, ym, g)
    r = out["results"]
    assert r["physics+GP"]["rmse"] < r["physics"]["rmse"]
    assert r["physics"]["coverage_95"] is None
    assert out["calibrated"] is False


def test_groups_are_never_split():
    X, y, ym, g = _data()
    out = grouped_ablation(X, y, ym, g)
    assert out["groups"] == ["b0", "b1", "b2", "b3"]
    assert out["n_rows"] == 20


def test_xgb_inactive_below_row_gate_and_not_justified():
    X, y, ym, g = _data(per=3)  # 12 rows, 9 train rows per fold < 15
    out = grouped_ablation(X, y, ym, g)
    assert out["xgb_active_folds"] == 0
    assert out["xgb_justified"] is False
    assert out["xgb_gain_rmse"] is None


def test_single_group_rejected():
    X, y, ym, _ = _data()
    with pytest.raises(ValueError, match="two distinct groups"):
        grouped_ablation(X, y, ym, ["a"] * len(y))


def test_length_mismatch_rejected():
    X, y, ym, g = _data()
    with pytest.raises(ValueError, match="same length"):
        grouped_ablation(X, y[:-1], ym, g)


def test_spearman_known_values():
    assert spearman(np.array([1, 2, 3, 4.0]), np.array([10, 20, 30, 40.0])) == pytest.approx(1.0)
    assert spearman(np.array([1, 2, 3, 4.0]), np.array([4, 3, 2, 1.0])) == pytest.approx(-1.0)
    assert spearman(np.array([1, 1, 1.0]), np.array([1, 2, 3.0])) is None
