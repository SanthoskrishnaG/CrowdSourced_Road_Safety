from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models.report import ReportCategory, ReportSeverity, ReportStatus


class ReportMapPoint(BaseModel):
    """
    Lightweight, public-safe representation of a road report optimized for map rendering.
    Excludes sensitive reporter identities or personal contact information.
    """
    id: UUID
    category: ReportCategory
    title: str
    description: Optional[str] = None
    severity: ReportSeverity
    status: ReportStatus
    latitude: float
    longitude: float
    address: Optional[str] = None
    created_at: datetime
    thumbnail_url: Optional[str] = None
    image_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class RoadSegmentMapItem(BaseModel):
    """
    Lightweight map representation of a road segment with start/end coordinates,
    corridor classification, and dynamic health status.
    """
    id: UUID
    name: str
    start_latitude: float
    start_longitude: float
    end_latitude: float
    end_longitude: float
    road_type: str
    importance: str
    active_issues_count: int = 0
    health_score: float = 100.0
    health_status: str = "EXCELLENT"  # EXCELLENT (green), GOOD (blue), FAIR (yellow), POOR (orange), CRITICAL (red)
    risk_level: str = "LOW"

    model_config = ConfigDict(from_attributes=True)
