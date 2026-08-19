from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.schemas.report import PaginationMetadata


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
    report_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class IssueDetailResponse(IssueResponse):
    reports: List[IssueReportSummary] = []


class IssuePaginationResponse(BaseModel):
    items: List[IssueResponse]
    metadata: PaginationMetadata
