import numpy as np
import pytest

from src.experiment_design.bayesian_selector import BayesianExperimentSelector
from src.experiment_design.cost_aware import recommend_with_cost
from src.gp_model.residual_gp import ResidualGP


@pytest.fixture
def setup():
    gp = ResidualGP()
    X = np.linspace(0, 1, 6).reshape(-1, 1)
    ym = np.ones(6)
    gp.fit(X[:3], np.array([1.1, 1.2, 1.1]), ym[:3])
    return BayesianExperimentSelector(gp), X, ym


def test_cheaper_equal_score_candidate_ranks_higher(setup):
    sel, X, ym = setup
    base = recommend_with_cost(sel, X, ym, [1.0] * 6, "h", n_recommendations=6)
    best = base[0]["features"]
    costs = [1.0] * 6
    # make a different candidate 100x cheaper
    other = next(i for i in range(6) if [float(X[i, 0])] != best)
    costs[other] = 0.01
    out = recommend_with_cost(sel, X, ym, costs, "h", n_recommendations=6)
    row = next(r for r in out if r["features"] == [float(X[other, 0])])
    assert row["score_per_cost"] == pytest.approx(row["acquisition_score"] / 0.01)
    assert out[0]["score_per_cost"] >= out[-1]["score_per_cost"]


def test_pending_region_excluded(setup):
    sel, X, ym = setup
    out = recommend_with_cost(
        sel, X, ym, [1.0] * 6, "h", pending=np.array([[0.0]]), min_separation=0.05,
        n_recommendations=6,
    )
    assert all(r["features"] != [0.0] for r in out)
    assert all("pending" in r["reason"] for r in out)


def test_reason_is_present_and_ranked(setup):
    sel, X, ym = setup
    out = recommend_with_cost(sel, X, ym, [2.0] * 6, "plate_wells")
    assert [r["rank"] for r in out] == [1, 2, 3]
    assert all("plate_wells" in r["reason"] for r in out)


@pytest.mark.parametrize("costs", [[0.0] * 6, [-1.0] * 6, [1.0] * 5, [float("nan")] * 6])
def test_bad_costs_rejected(setup, costs):
    sel, X, ym = setup
    with pytest.raises(ValueError):
        recommend_with_cost(sel, X, ym, costs, "h")
