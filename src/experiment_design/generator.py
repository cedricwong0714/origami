# src/experiment_design/generator.py
import numpy as np
from typing import Literal
from src.gp_model.trainer import GPCorrectionModel
from src.gp_model.predictor import predict_augmented_kinetics
from src.experiment_design.acquisition import upper_confidence_bound, expected_improvement

class ExperimentGenerator:
    def __init__(self, gp_model: GPCorrectionModel):
        self.gp_model = gp_model

    def suggest_next_experiments(
        self,
        candidate_time_points: np.ndarray,
        candidate_ode_baseline: np.ndarray,
        top_k: int = 3,
        strategy: Literal["UCB", "EI"] = "UCB",
        current_best: float = 0.0
    ) -> list[dict[str, float]]:
        """
        Evaluates acquisition scores across candidate points and returns top K recommendations.
        """
        predictions = predict_augmented_kinetics(
            candidate_time_points, 
            candidate_ode_baseline, 
            self.gp_model
        )
        
        mean = predictions["mean"]
        std = predictions["std"]

        if strategy == "UCB":
            scores = upper_confidence_bound(mean, std)
        elif strategy == "EI":
            scores = expected_improvement(mean, std, current_best=current_best)
        else:
            raise ValueError(f"Unsupported strategy '{strategy}'. Use 'UCB' or 'EI'.")

        # Rank candidate indices by highest acquisition score
        ranked_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in ranked_indices:
            results.append({
                "time_point": float(candidate_time_points[idx]),
                "predicted_mean": float(mean[idx]),
                "uncertainty_std": float(std[idx]),
                "acquisition_score": float(scores[idx])
            })

        return results