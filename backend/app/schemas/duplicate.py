from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Optional, Dict, Any, List
from app.models.report import ReportCategory, ReportSeverity, ReportStatus


class DuplicateScoreBreakdown(BaseModel):
    distance_meters: float
    location_score: float
    category_score: float
    time_score: float
    image_score: Optional[float] = None
    text_similarity_score: Optional[float] = None
    composite_score: float


class DuplicateCandidateItem(BaseModel):
    issue_id: UUID
    issue_title: str
    issue_category: ReportCategory
    issue_severity: ReportSeverity
    issue_status: ReportStatus
    latitude: float
    longitude: float
    distance_meters: float
    duplicate_score: float
    is_match: bool
    score_breakdown: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DuplicateCandidatesResponse(BaseModel):
    report_id: UUID
    threshold: float
    total_candidates: int
    matched_issue_id: Optional[UUID] = None
    candidates: List[DuplicateCandidateItem] = []
