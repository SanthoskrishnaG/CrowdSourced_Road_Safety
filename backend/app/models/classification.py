import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.report import ReportCategory


class ImageClassification(Base):
    """
    Tracks AI machine learning image classification results, confidence scores,
    and human-in-the-loop overrides (citizen suggestion vs AI vs authority verification).
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

    # Human Override & Verification Fields
    user_suggested_category: Mapped[Optional[ReportCategory]] = mapped_column(
        Enum(ReportCategory),
        nullable=True
    )
    authority_verified_category: Mapped[Optional[ReportCategory]] = mapped_column(
        Enum(ReportCategory),
        nullable=True
    )
    is_corrected: Mapped[bool] = mapped_column(
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
