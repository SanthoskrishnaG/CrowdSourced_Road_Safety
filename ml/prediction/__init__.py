"""
Predictive Road Risk ML Subsystem.
Implements machine learning pipeline for predicting road corridor deterioration risk.
"""

from ml.prediction.model import RoadRiskModel, load_road_risk_model

__all__ = ["RoadRiskModel", "load_road_risk_model"]
