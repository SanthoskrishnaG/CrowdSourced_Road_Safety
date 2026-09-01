from uuid import UUID
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.report import ReportCategory, ReportSeverity


class CategoryProbability(BaseModel):
    category: str
    probability: float


class ImageQualityMetrics(BaseModel):
    quality_score: float = Field(..., ge=0.0, le=100.0, description="Overall image quality score (0 to 100)")
    is_acceptable: bool = True
    blur_score: Optional[float] = None
    brightness_score: Optional[float] = None
    contrast_score: Optional[float] = None
    resolution_score: Optional[float] = None
    is_corrupt: bool = False
    detected_issues: List[str] = []
    recommendation: Optional[str] = None


class ImageClassificationResponse(BaseModel):
    id: UUID
    image_id: UUID
    # Category
    predicted_category: ReportCategory
    confidence: float
    model_version: str
    probabilities_json: Optional[str] = None

    # Severity
    predicted_severity: Optional[ReportSeverity] = ReportSeverity.MEDIUM
    severity_confidence: Optional[float] = 0.85
    severity_model_version: Optional[str] = "road-severity-v1.0"
    severity_probabilities_json: Optional[str] = None

    # Quality
    quality_score: Optional[float] = 85.0
    quality_blur_score: Optional[float] = None
    quality_brightness_score: Optional[float] = None
    quality_contrast_score: Optional[float] = None
    quality_resolution_score: Optional[float] = None
    quality_issues_json: Optional[str] = None
    quality_recommendation: Optional[str] = None

    # Human Verification & Overrides
    user_suggested_category: Optional[ReportCategory] = None
    authority_verified_category: Optional[ReportCategory] = None
    user_suggested_severity: Optional[ReportSeverity] = None
    authority_verified_severity: Optional[ReportSeverity] = None
    is_corrected: bool = False
    is_severity_corrected: bool = False
    corrected_by_user_id: Optional[UUID] = None
    corrected_at: Optional[datetime] = None
    correction_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageClassificationOverride(BaseModel):
    verified_category: Optional[ReportCategory] = None
    verified_severity: Optional[ReportSeverity] = None
    notes: Optional[str] = Field(None, max_length=500, description="Verification / correction justification")


class StandaloneClassifyResponse(BaseModel):
    predicted_category: ReportCategory
    confidence: float
    model_version: str
    probabilities: Dict[str, float]
    # Severity & Quality
    severity: Optional[ReportSeverity] = ReportSeverity.MEDIUM
    severity_confidence: Optional[float] = 0.85
    severity_probabilities: Optional[Dict[str, float]] = None
    quality: Optional[ImageQualityMetrics] = None
    message: str = "Image successfully processed by Road Vision ML model."


class AIAnalysisImageItem(BaseModel):
    image_id: UUID
    file_path: str
    thumbnail_path: Optional[str] = None
    # Category
    ai_category: ReportCategory
    category_confidence: float
    category_model_version: str
    category_probabilities: Optional[Dict[str, float]] = None
    # Severity
    ai_severity: ReportSeverity
    severity_confidence: float
    severity_model_version: str
    severity_probabilities: Optional[Dict[str, float]] = None
    # Quality
    quality_score: float
    quality_diagnostics: ImageQualityMetrics
    # Overrides
    citizen_category: Optional[ReportCategory] = None
    authority_verified_category: Optional[ReportCategory] = None
    citizen_severity: Optional[ReportSeverity] = None
    authority_verified_severity: Optional[ReportSeverity] = None
    is_category_corrected: bool = False
    is_severity_corrected: bool = False
    corrected_by_user_id: Optional[UUID] = None
    corrected_at: Optional[datetime] = None
    correction_notes: Optional[str] = None


class ReportAIAnalysisResponse(BaseModel):
    report_id: UUID
    title: str
    # Primary Human vs AI Values
    citizen_category: ReportCategory
    ai_category: Optional[ReportCategory] = None
    authority_verified_category: Optional[ReportCategory] = None
    effective_category: ReportCategory

    citizen_severity: ReportSeverity
    ai_severity: Optional[ReportSeverity] = None
    authority_verified_severity: Optional[ReportSeverity] = None
    effective_severity: ReportSeverity

    # Summary Scores
    primary_category_confidence: float = 0.0
    primary_severity_confidence: float = 0.0
    average_quality_score: float = 100.0
    quality_status: str = "GOOD"  # GOOD, ACCEPTABLE, POOR, CORRUPT
    overall_recommendation: Optional[str] = None

    # Human-in-the-loop audit flags
    has_overrides: bool = False
    images_analyzed: int = 0
    images: List[AIAnalysisImageItem] = []
