from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Optional, Dict, Any, List
from enum import Enum
from app.models.report import ReportCategory, ReportSeverity, ReportStatus


class DuplicateTier(str, Enum):
    NOT_DUPLICATE = "NOT_DUPLICATE"
    POTENTIAL_DUPLICATE = "POTENTIAL_DUPLICATE"
    LIKELY_DUPLICATE = "LIKELY_DUPLICATE"


class ExplainableComponentScores(BaseModel):
    location: float = Field(..., ge=0.0, le=100.0, description="Geographic proximity score (0-100)")
    category: float = Field(..., ge=0.0, le=100.0, description="Category similarity score (0-100)")
    image: float = Field(..., ge=0.0, le=100.0, description="Image perceptual similarity score (0-100)")
    description: float = Field(..., ge=0.0, le=100.0, description="NLP semantic text embedding similarity score (0-100)")
    time: float = Field(..., ge=0.0, le=100.0, description="Time proximity decay score (0-100)")
    road_segment: float = Field(..., ge=0.0, le=100.0, description="Road corridor & address similarity score (0-100)")
    overall: float = Field(..., ge=0.0, le=100.0, description="Normalized composite duplicate score (0-100)")
    classification: DuplicateTier = Field(..., description="NOT_DUPLICATE (0-39), POTENTIAL_DUPLICATE (40-69), LIKELY_DUPLICATE (70-100)")


class DuplicateScoreBreakdown(BaseModel):
    distance_meters: float
    location_score: float
    category_score: float
    time_score: float
    image_score: Optional[float] = None
    text_similarity_score: Optional[float] = None
    road_segment_score: Optional[float] = None
    composite_score: float
    explainability: Optional[ExplainableComponentScores] = None


class DuplicateCandidateItem(BaseModel):
    issue_id: UUID
    issue_title: str
    issue_category: ReportCategory
    issue_severity: ReportSeverity
    issue_status: ReportStatus
    latitude: float
    longitude: float
    distance_meters: float
    duplicate_score: float  # Normalized 0 to 100 or 0.0 to 1.0
    classification: DuplicateTier = DuplicateTier.NOT_DUPLICATE
    is_match: bool
    requires_authority_review: bool = False
    explainability: ExplainableComponentScores
    score_breakdown: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(from_attributes=True)


class DuplicateCandidatesResponse(BaseModel):
    report_id: UUID
    threshold: float
    total_candidates: int
    matched_issue_id: Optional[UUID] = None
    candidates: List[DuplicateCandidateItem] = []


class MergeReportRequest(BaseModel):
    target_issue_id: UUID = Field(..., description="Canonical Issue UUID to merge this report into")
    merge_reason: Optional[str] = Field(None, max_length=500, description="Authority justification for merge")


class MergeReportResponse(BaseModel):
    message: str
    report_id: UUID
    target_issue_id: UUID
    updated_report_count: int
    updated_priority_score: float
    updated_priority_level: str


class RejectDuplicateRequest(BaseModel):
    rejection_reason: Optional[str] = Field(None, max_length=500, description="Justification why report is distinct and not a duplicate")


class RejectDuplicateResponse(BaseModel):
    message: str
    report_id: UUID
    canonical_issue_id: UUID
    is_distinct: bool = True
