from uuid import UUID
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict, Field
from app.models.road_segment import RoadType, RoadImportance


class RoadHealthFactorBreakdown(BaseModel):
    """
    Normalized sub-factor penalties and scores comprising the overall 0-100 road health score.
    Higher penalty indicates greater negative impact on road condition.
    """
    active_issue_penalty: float = Field(..., description="Penalty from count of unresolved issues (0-100)")
    severity_penalty: float = Field(..., description="Penalty from weighted severity of open issues (0-100)")
    density_penalty: float = Field(..., description="Penalty from active issues per kilometer (0-100)")
    report_frequency_penalty: float = Field(..., description="Penalty from recent citizen report velocity (0-100)")
    resolution_time_penalty: float = Field(..., description="Penalty from slow average resolution turnaround (0-100)")
    recent_incidents_penalty: float = Field(..., description="Penalty from recent hazard reports within last 7-14 days (0-100)")

    model_config = ConfigDict(from_attributes=True)


class RoadHealthMetrics(BaseModel):
    active_issues_count: int
    total_issues_count: int
    total_reports_count: int
    recent_7d_reports_count: int
    recent_14d_reports_count: int
    length_km: float
    issues_per_km: float
    avg_resolution_hours: Optional[float] = None
    critical_issues_count: int
    high_issues_count: int


class RoadHealthResponse(BaseModel):
    """
    Concise road health score representation.
    """
    road_id: UUID
    name: str
    road_type: RoadType
    importance: RoadImportance
    health_score: float = Field(..., ge=0.0, le=100.0, description="0 (Critical) to 100 (Pristine)")
    health_status: str = Field(..., description="EXCELLENT, GOOD, FAIR, POOR, CRITICAL")
    risk_level: str = Field(..., description="LOW, MODERATE, HIGH, SEVERE")
    active_issues_count: int
    disclaimer: str = Field(
        "Application-generated indicator, not an official government road rating.",
        description="Non-official indicator advisory"
    )

    model_config = ConfigDict(from_attributes=True)


class RoadHealthDetailResponse(RoadHealthResponse):
    """
    In-depth road health breakdown with factor penalties and detailed metrics.
    """
    factors: RoadHealthFactorBreakdown
    metrics: RoadHealthMetrics


class RoadLeaderboardItem(BaseModel):
    road_id: UUID
    name: str
    road_type: RoadType
    importance: RoadImportance
    health_score: float
    health_status: str
    active_issues_count: int
    length_km: float
    primary_hazard: Optional[str] = None


class HealthDistributionItem(BaseModel):
    status: str
    count: int
    percentage: float


class HealthTrendPoint(BaseModel):
    period: str
    avg_health_score: float
    critical_segments_count: int
    monitored_segments_count: int


class RoadHealthSummary(BaseModel):
    total_monitored_segments: int
    total_monitored_km: float
    average_health_score: float
    critical_segments_count: int
    poor_segments_count: int
    good_or_excellent_count: int


class RoadHealthAnalyticsResponse(BaseModel):
    """
    City-wide road health overview, best/worst segments, distribution, and trends.
    """
    summary: RoadHealthSummary
    worst_roads: List[RoadLeaderboardItem]
    best_roads: List[RoadLeaderboardItem]
    health_distribution: List[HealthDistributionItem]
    health_trends: List[HealthTrendPoint]
    disclaimer: str = "Application-generated indicator, not an official government road rating."
