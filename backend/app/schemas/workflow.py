from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict, Field

from app.models.report import ReportStatus
from app.models.assignment import AuthorityDepartment


class IssueVerifyRequest(BaseModel):
    department: Optional[AuthorityDepartment] = Field(None, description="Optional municipal department assignment")
    notes: Optional[str] = Field(None, max_length=500, description="Verification remarks / inspection notes")


class IssueAssignRequest(BaseModel):
    department: AuthorityDepartment = Field(..., description="Target municipal department")
    assigned_to_user_id: Optional[UUID] = Field(None, description="Optional specific assigned officer UUID")
    notes: Optional[str] = Field(None, max_length=500, description="Assignment instructions")


class IssueStatusUpdateRequest(BaseModel):
    status: ReportStatus = Field(..., description="New target status (e.g. IN_PROGRESS, FIXED, CLOSED, REJECTED)")
    comment: Optional[str] = Field(None, max_length=500, description="Status transition justification / work summary")


class IssueCommentRequest(BaseModel):
    comment: str = Field(..., min_length=1, max_length=1000, description="Authority / Admin audit comment")


class IssueAssignmentResponse(BaseModel):
    id: UUID
    issue_id: UUID
    department: AuthorityDepartment
    assigned_to_user_id: Optional[UUID] = None
    assigned_by_user_id: Optional[UUID] = None
    assigned_at: datetime
    notes: Optional[str] = None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class IssueStatusHistoryResponse(BaseModel):
    id: UUID
    issue_id: UUID
    previous_status: Optional[ReportStatus] = None
    new_status: ReportStatus
    changed_by_user_id: Optional[UUID] = None
    comment: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PriorityBreakdownResponse(BaseModel):
    severity_score: float
    report_count_score: float
    road_health_score: float = 0.0
    traffic_density_score: float
    location_zone_score: float
    aging_score: float
    aging_days: float
    predicted_risk_score: float = 0.0
    weather_condition_score: float = 0.0
    citizen_confirmations_score: float = 0.0
    total_score: float
    priority_level: str
    factors: Optional[List[Dict[str, Any]]] = None
    top_contributing_drivers: Optional[List[str]] = None

