# src/gp_model/__init__.py
from src.gp_model.predictor import predict_augmented_kinetics
from src.gp_model.residual_gp import ResidualGP
from src.gp_model.stacked_ensemble import StackedEnsemblePredictor, StackedPrediction
from src.gp_model.trainer import GPCorrectionModel
from src.gp_model.xgb_meta import InsufficientDataError, XGBoostMetaPredictor

__all__ = [
    "GPCorrectionModel",
    "predict_augmented_kinetics",
    "ResidualGP",
    "XGBoostMetaPredictor",
    "InsufficientDataError",
    "StackedEnsemblePredictor",
    "StackedPrediction",
]