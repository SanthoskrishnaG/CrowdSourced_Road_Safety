from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.issue import PriorityLevel, LocationZone, TrafficDensity
from app.models.assignment import AuthorityDepartment
from app.schemas.report import PaginationMetadata
from app.schemas.workflow import IssueAssignmentResponse, IssueStatusHistoryResponse, PriorityBreakdownResponse


class IssueReportSummary(BaseModel):
    id: UUID
    title: str
    category: ReportCategory
    severity: ReportSeverity
    status: ReportStatus
    latitude: float
    longitude: float
    created_at: datetime
    image_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class IssueResponse(BaseModel):
    id: UUID
    category: ReportCategory
    title: str
    description: Optional[str] = None
    latitude: float
    longitude: float
    address: Optional[str] = None
    severity: ReportSeverity
    status: ReportStatus
    priority_score: float
    priority_level: PriorityLevel
    report_count: int
    traffic_density: TrafficDensity
    location_zone: LocationZone
    assigned_department: Optional[AuthorityDepartment] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueDetailResponse(IssueResponse):
    reports: List[IssueReportSummary] = []
    assignments: List[IssueAssignmentResponse] = []
    status_history: List[IssueStatusHistoryResponse] = []
    priority_breakdown: Optional[PriorityBreakdownResponse] = None


class IssuePaginationResponse(BaseModel):
    items: List[IssueResponse]
    metadata: PaginationMetadata
