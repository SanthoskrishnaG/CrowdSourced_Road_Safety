from uuid import UUID
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.road_segment import RoadType, RoadImportance


class RoadRiskFactor(BaseModel):
    factor_name: str = Field(..., description="Name of contributing factor")
    impact_percentage: float = Field(..., description="Normalized contribution percentage (0-100)")
    description: str = Field(..., description="Explainability detail on why this factor impacts risk")


class RoadRiskResponse(BaseModel):
    """
    Detailed predictive risk forecast for an individual road corridor segment.
    """
    road_id: UUID
    name: str
    road_type: RoadType
    importance: RoadImportance
    risk_score: float = Field(..., ge=0.0, le=100.0, description="0 (Low Risk) to 100 (Critical Risk)")
    risk_level: str = Field(..., description="LOW (0-24), MEDIUM (25-49), HIGH (50-74), CRITICAL (75-100)")
    worsening_probability: float = Field(..., ge=0.0, le=1.0, description="Calibrated likelihood (0.0 - 1.0) of condition deteriorating")
    current_health_score: float
    active_issues_count: int
    contributing_factors: List[RoadRiskFactor] = []
    features_used: Optional[Dict[str, Any]] = None
    model_version: str = Field("road-risk-v1.0", description="Trained model version")
    disclaimer: str = Field(
        "Application-generated predictive estimate for prioritization. Does not claim certainty or replace official engineering inspections.",
        description="Predictive model limitation advisory"
    )

    model_config = ConfigDict(from_attributes=True)


class RoadRiskPredictionItem(BaseModel):
    road_id: UUID
    name: str
    road_type: RoadType
    importance: RoadImportance
    risk_score: float
    risk_level: str
    worsening_probability: float
    current_health_score: float
    active_issues_count: int
    top_contributing_factor: Optional[str] = None


class RoadRiskPredictionSummary(BaseModel):
    total_evaluated_segments: int
    high_or_critical_risk_count: int
    average_risk_score: float
    critical_risk_count: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int


class RoadRiskPredictionListResponse(BaseModel):
    """
    Batch ranking and predictive risk catalog across all monitored road segments.
    """
    summary: RoadRiskPredictionSummary
    predictions: List[RoadRiskPredictionItem]
    model_version: str = "road-risk-v1.0"
    disclaimer: str = (
        "Application-generated predictive estimate for prioritization. "
        "Does not claim certainty or replace official engineering inspections."
    )
