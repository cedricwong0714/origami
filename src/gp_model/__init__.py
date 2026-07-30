# src/gp_model/__init__.py
from src.gp_model.trainer import GPCorrectionModel
from src.gp_model.predictor import predict_augmented_kinetics

__all__ = ["GPCorrectionModel", "predict_augmented_kinetics"]