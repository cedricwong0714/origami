import pytest

from src.experiment_design.replicate_choice import choose_replicate_or_new, variance_reduction


def test_known_value():
    # v=4, s2=4 -> v_post=2, reduction 2
    assert variance_reduction(2.0, 2.0) == pytest.approx(2.0)


def test_reduction_bounded_by_prior_variance_and_monotone_in_noise():
    assert 0 < variance_reduction(3.0, 0.1) < 9.0
    assert variance_reduction(3.0, 0.1) > variance_reduction(3.0, 10.0)


def test_noisy_assay_favours_uncertain_new_point_over_certain_replicate():
    out = choose_replicate_or_new(
        [{"label": "n8", "sigma_pred": 0.2, "cost": 1}],
        [{"label": "n14", "sigma_pred": 2.0, "cost": 1}],
        sigma_noise=1.0, cost_unit="h",
    )
    assert out["best"]["action"] == "new" and "h" in out["best"]["reason"]


def test_high_cost_new_point_loses():
    out = choose_replicate_or_new(
        [{"label": "n8", "sigma_pred": 1.0, "cost": 1}],
        [{"label": "n14", "sigma_pred": 1.2, "cost": 50}],
        sigma_noise=1.0, cost_unit="h",
    )
    assert out["best"]["action"] == "replicate"


@pytest.mark.parametrize("args", [(0.0, 1.0), (1.0, 0.0), (float("nan"), 1.0), (1.0, -1.0)])
def test_bad_inputs(args):
    with pytest.raises(ValueError):
        variance_reduction(*args)


def test_empty_and_bad_cost():
    with pytest.raises(ValueError):
        choose_replicate_or_new([], [], 1.0, "h")
    with pytest.raises(ValueError):
        choose_replicate_or_new([{"label": "a", "sigma_pred": 1, "cost": 0}], [], 1.0, "h")
