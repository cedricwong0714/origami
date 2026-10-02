# src/experiment_design/__init__.py
from src.experiment_design.acquisition import expected_improvement, upper_confidence_bound
from src.experiment_design.bayesian_selector import (
    BayesianExperimentSelector,
    ExperimentRecommendation,
)
from src.experiment_design.generator import ExperimentGenerator

__all__ = [
    "upper_confidence_bound",
    "expected_improvement",
    "ExperimentGenerator",
    "BayesianExperimentSelector",
    "ExperimentRecommendation",
]