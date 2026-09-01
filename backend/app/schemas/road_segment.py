from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field
from app.models.road_segment import RoadType, RoadImportance
from app.schemas.issue import IssueResponse
from app.schemas.report import ReportResponse


class RoadSegmentBase(BaseModel):
    name: str = Field(..., max_length=200, description="Corridor or street segment name")
    start_latitude: float = Field(..., ge=-90, le=90)
    start_longitude: float = Field(..., ge=-180, le=180)
    end_latitude: float = Field(..., ge=-90, le=90)
    end_longitude: float = Field(..., ge=-180, le=180)
    road_type: RoadType = RoadType.ARTERIAL
    importance: RoadImportance = RoadImportance.MEDIUM
    speed_limit_kmh: Optional[int] = Field(50, ge=10, le=150)


class RoadSegmentCreate(RoadSegmentBase):
    pass


class RoadSegmentUpdate(BaseModel):
    name: Optional[str] = None
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    road_type: Optional[RoadType] = None
    importance: Optional[RoadImportance] = None
    speed_limit_kmh: Optional[int] = None


class RoadSegmentResponse(RoadSegmentBase):
    id: UUID
    length_meters: Optional[float] = None
    active_issues_count: int = 0
    health_score: float = Field(100.0, ge=0.0, le=100.0, description="0 (Critical) to 100 (Pristine)")
    health_status: str = Field("EXCELLENT", description="EXCELLENT, GOOD, FAIR, POOR, CRITICAL")
    risk_level: str = Field("LOW", description="LOW, MODERATE, HIGH, SEVERE")
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RoadSegmentDetailResponse(RoadSegmentResponse):
    issues: List[IssueResponse] = []
    recent_reports: List[ReportResponse] = []
