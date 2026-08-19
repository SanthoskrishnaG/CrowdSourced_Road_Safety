from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.schemas.image import ReportImageResponse


class ReportBase(BaseModel):
    category: ReportCategory
    title: str = Field(..., max_length=100)
    description: str
    severity: ReportSeverity
    latitude: float = Field(..., ge=-90, le=90, description="Latitude must be between -90 and 90.")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude must be between -180 and 180.")
    address: Optional[str] = Field(None, max_length=255)
    location_accuracy: Optional[float] = Field(None, ge=0, description="Location accuracy in meters")


class ReportCreate(ReportBase):
    pass


class ReportUpdate(BaseModel):
    category: Optional[ReportCategory] = None
    title: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    severity: Optional[ReportSeverity] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    address: Optional[str] = Field(None, max_length=255)
    location_accuracy: Optional[float] = Field(None, ge=0)
    status: Optional[ReportStatus] = None


class ReportResponse(ReportBase):
    id: UUID
    reporter_id: UUID
    status: ReportStatus
    created_at: datetime
    updated_at: datetime
    images: List[ReportImageResponse] = []

    model_config = ConfigDict(from_attributes=True)



class PaginationMetadata(BaseModel):
    total: int
    page: int
    page_size: int
    pages: int


class ReportPaginationResponse(BaseModel):
    items: List[ReportResponse]
    metadata: PaginationMetadata
