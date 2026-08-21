from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class RoadHealthResponse(BaseModel):
    latitude: float
    longitude: float
    segment_name: str = Field(default="Municipal Road Corridor")
    health_score: float = Field(..., ge=0.0, le=100.0, description="0 (Critical Hazard) to 100 (Pristine)")
    health_status: str = Field(..., description="EXCELLENT, GOOD, FAIR, POOR, CRITICAL")
    hazard_density_per_km2: float
    active_hazards_count: int
    recurring_pothole_cluster: bool = False


class AccidentRiskPrediction(BaseModel):
    risk_probability: float = Field(..., ge=0.0, le=1.0, description="Predictive probability of traffic incident")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, SEVERE")
    primary_risk_factors: List[str]
    estimated_traffic_delay_min: float = 0.0
    pedestrian_risk_flag: bool = False


class SLATrackingInfo(BaseModel):
    priority_level: str
    sla_target_hours: int
    deadline_at: datetime
    remaining_hours: float
    sla_status: str = Field(..., description="ON_TRACK, APPROACHING_BREACH, BREACHED, RESOLVED")
    is_escalated: bool = False
    escalation_reason: Optional[str] = None


class CitizenVerificationRequest(BaseModel):
    verified: bool = Field(..., description="True if citizen confirms issue is fixed, False if still present/disputed")
    feedback: Optional[str] = Field(None, max_length=500, description="Citizen feedback or remarks")
    rating: Optional[int] = Field(None, ge=1, le=5, description="Citizen satisfaction rating (1-5)")
