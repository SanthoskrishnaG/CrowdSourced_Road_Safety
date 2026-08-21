from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict


class AnalyticsSummaryResponse(BaseModel):
    total_reports: int
    total_issues: int
    active_issues: int
    critical_issues: int
    high_priority_issues: int
    awaiting_verification: int
    in_progress_issues: int
    fixed_issues: int
    closed_issues: int
    avg_resolution_time_hours: Optional[float] = None
    avg_close_time_hours: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class CategoryDistributionItem(BaseModel):
    category: str
    count: int
    percentage: float


class CategoryAnalyticsResponse(BaseModel):
    total: int
    categories: List[CategoryDistributionItem]


class SeverityDistributionItem(BaseModel):
    severity: str
    count: int
    percentage: float


class SeverityAnalyticsResponse(BaseModel):
    total: int
    severities: List[SeverityDistributionItem]


class StatusDistributionItem(BaseModel):
    status: str
    count: int
    percentage: float


class StatusAnalyticsResponse(BaseModel):
    total: int
    statuses: List[StatusDistributionItem]


class ResolutionTimeBreakdown(BaseModel):
    avg_hours: Optional[float] = None
    avg_days: Optional[float] = None
    sample_size: int


class ResolutionAnalyticsResponse(BaseModel):
    total_fixed: int
    total_closed: int
    avg_hours_reported_to_fixed: Optional[float] = None
    avg_days_reported_to_fixed: Optional[float] = None
    avg_hours_reported_to_closed: Optional[float] = None
    avg_days_reported_to_closed: Optional[float] = None
    by_category: Dict[str, Optional[float]] = {}
    by_severity: Dict[str, Optional[float]] = {}


class GeographicDensityItem(BaseModel):
    latitude: float
    longitude: float
    issue_count: int
    critical_count: int
    density_level: str  # HIGH, MEDIUM, LOW
    sample_address: Optional[str] = None


class GeographicAnalyticsResponse(BaseModel):
    total_clusters: int
    clusters: List[GeographicDensityItem]


class TrendPoint(BaseModel):
    period: str
    count: int
    critical_count: int
    resolved_count: int


class TrendsAnalyticsResponse(BaseModel):
    interval: str  # day, week, month
    data: List[TrendPoint]


class HeatmapPoint(BaseModel):
    latitude: float
    longitude: float
    intensity: float
    category: str
    severity: str
    status: str
    title: str


class HeatmapAnalyticsResponse(BaseModel):
    total_points: int
    points: List[HeatmapPoint]
