from uuid import UUID
from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, ConfigDict, Field
from app.models.report import ReportCategory


class CategoryProbability(BaseModel):
    category: str
    probability: float


class ImageClassificationResponse(BaseModel):
    id: UUID
    image_id: UUID
    predicted_category: ReportCategory
    confidence: float
    model_version: str
    probabilities_json: Optional[str] = None
    user_suggested_category: Optional[ReportCategory] = None
    authority_verified_category: Optional[ReportCategory] = None
    is_corrected: bool = False
    corrected_by_user_id: Optional[UUID] = None
    corrected_at: Optional[datetime] = None
    correction_notes: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ImageClassificationOverride(BaseModel):
    verified_category: ReportCategory
    notes: Optional[str] = Field(None, max_length=500, description="Verification / correction justification")


class StandaloneClassifyResponse(BaseModel):
    predicted_category: ReportCategory
    confidence: float
    model_version: str
    probabilities: Dict[str, float]
    message: str = "Image successfully classified by Road Vision ML model."
