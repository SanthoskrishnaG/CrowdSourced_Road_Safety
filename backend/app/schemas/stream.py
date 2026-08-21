from typing import List, Dict, Optional
from pydantic import BaseModel, Field
from app.models.report import ReportCategory, ReportSeverity


class HazardDetectionEvent(BaseModel):
    timestamp_sec: float = Field(..., description="Timestamp in seconds within video stream")
    frame_index: int = Field(..., description="Sampled frame sequence number")
    category: ReportCategory = Field(..., description="Detected hazard classification")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated prediction confidence")
    severity: ReportSeverity = Field(default=ReportSeverity.MEDIUM, description="Inferred hazard severity")
    bounding_box: List[float] = Field(default=[0.2, 0.4, 0.6, 0.5], description="[x_min, y_min, width, height] normalized")
    estimated_lat: Optional[float] = Field(None, description="Interpolated latitude")
    estimated_lng: Optional[float] = Field(None, description="Interpolated longitude")
    snapshot_base64: Optional[str] = Field(None, description="Optional preview thumbnail")


class VideoStreamAnalysisResponse(BaseModel):
    video_filename: str
    video_duration_sec: float
    total_frames_sampled: int
    detections_count: int
    hazards: List[HazardDetectionEvent]
    summary_by_category: Dict[str, int]
    stream_fps: float = 30.0


class StreamReportConversionRequest(BaseModel):
    category: ReportCategory
    severity: ReportSeverity = ReportSeverity.HIGH
    title: str = Field(..., max_length=100)
    description: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    address: Optional[str] = None
    timestamp_sec: float
    snapshot_base64: Optional[str] = None
