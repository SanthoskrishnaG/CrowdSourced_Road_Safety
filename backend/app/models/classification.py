import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.report import ReportCategory, ReportSeverity


class ImageClassification(Base):
    """
    Tracks AI machine learning image classification results, severity estimation,
    image quality diagnostics, confidence scores, and human-in-the-loop overrides
    (citizen suggestion vs AI vs authority verification).
    """
    __tablename__ = "image_classifications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    image_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("report_images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    # AI Category Classification
    predicted_category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory),
        nullable=False
    )
    confidence: Mapped[float] = mapped_column(
        Float,
        nullable=False
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        default="road-vision-v1.0",
        nullable=False
    )
    probabilities_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # AI Severity Estimation (Phase 8)
    predicted_severity: Mapped[Optional[ReportSeverity]] = mapped_column(
        Enum(ReportSeverity),
        nullable=True,
        default=ReportSeverity.MEDIUM
    )
    severity_confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=0.85
    )
    severity_model_version: Mapped[Optional[str]] = mapped_column(
        String(50),
        default="road-severity-v1.0",
        nullable=True
    )
    severity_probabilities_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Image Quality Diagnostics (Phase 8)
    quality_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        default=85.0
    )
    quality_blur_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    quality_brightness_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    quality_contrast_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    quality_resolution_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True
    )
    quality_issues_json: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    quality_recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )

    # Human Override & Verification Fields
    user_suggested_category: Mapped[Optional[ReportCategory]] = mapped_column(
        Enum(ReportCategory),
        nullable=True
    )
    authority_verified_category: Mapped[Optional[ReportCategory]] = mapped_column(
        Enum(ReportCategory),
        nullable=True
    )
    user_suggested_severity: Mapped[Optional[ReportSeverity]] = mapped_column(
        Enum(ReportSeverity),
        nullable=True
    )
    authority_verified_severity: Mapped[Optional[ReportSeverity]] = mapped_column(
        Enum(ReportSeverity),
        nullable=True
    )
    is_corrected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    is_severity_corrected: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    corrected_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    corrected_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    correction_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    image: Mapped["ReportImage"] = relationship("ReportImage", back_populates="classification")
    corrected_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[corrected_by_user_id])
