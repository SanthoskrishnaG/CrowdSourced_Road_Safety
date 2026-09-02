import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.issue import PriorityLevel


class PriorityFactorScore(BaseModel):
    factor_name: str
    earned_points: float
    max_points: float
    percentage: float
    description: str


class PriorityBreakdownResponse(BaseModel):
    severity_score: float
    severity_max: float = 25.0
    report_count_score: float
    report_count_max: float = 15.0
    road_health_score: float
    road_health_max: float = 15.0
    traffic_density_score: float
    traffic_density_max: float = 10.0
    location_zone_score: float
    location_zone_max: float = 10.0
    aging_score: float
    aging_max: float = 10.0
    aging_days: float
    predicted_risk_score: float
    predicted_risk_max: float = 10.0
    weather_condition_score: float
    weather_condition_max: float = 5.0
    citizen_confirmations_score: float
    citizen_confirmations_max: float = 5.0
    total_score: float
    priority_level: PriorityLevel
    factors: List[PriorityFactorScore] = []
    top_contributing_drivers: List[str] = []


class PriorityHistoryItemResponse(BaseModel):
    id: uuid.UUID
    issue_id: uuid.UUID
    previous_score: float
    new_score: float
    previous_level: PriorityLevel
    new_level: PriorityLevel
    trigger_event: str
    factor_breakdown: Dict[str, Any]
    created_at: datetime


class PriorityRecalculationResponse(BaseModel):
    issue_id: uuid.UUID
    priority_score: float
    priority_level: PriorityLevel
    previous_score: float
    previous_level: PriorityLevel
    priority_breakdown: PriorityBreakdownResponse
    history_entry_id: Optional[uuid.UUID] = None
