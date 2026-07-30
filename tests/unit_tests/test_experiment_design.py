# tests/unit_tests/test_experiment_design.py
import pytest
import numpy as np
from src.gp_model.trainer import GPCorrectionModel
from src.experiment_design.generator import ExperimentGenerator

def test_experiment_recommendation_ranking():
    # 1. Train GP model on sparse initial observations
    time_obs = np.array([0.0, 10.0, 20.0, 50.0])
    ode_obs = 0.2 * time_obs
    exp_obs = np.array([0.0, 3.0, 2.5, 10.0])

    gp = GPCorrectionModel()
    gp.fit(time_obs, ode_obs, exp_obs)

    # 2. Define search space
    candidate_times = np.linspace(0, 50, 51)
    candidate_ode = 0.2 * candidate_times

    generator = ExperimentGenerator(gp)
    recommendations = generator.suggest_next_experiments(
        candidate_times, 
        candidate_ode, 
        top_k=3, 
        strategy="UCB"
    )

    assert len(recommendations) == 3
    # Verify recommendations are sorted in descending order of acquisition score
    assert recommendations[0]["acquisition_score"] >= recommendations[1]["acquisition_score"]
    assert recommendations[1]["acquisition_score"] >= recommendations[2]["acquisition_score"]