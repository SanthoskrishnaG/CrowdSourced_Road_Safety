import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.report import ReportCategory


class ImageClassification(Base):
    """
    Tracks AI machine learning image classification results, confidence scores,
    and human-in-the-loop overrides (citizen suggestion vs AI vs authority verification).
    """
    __tablename__ = "image_classifications"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    image_id = Column(
        UUID(as_uuid=True),
        ForeignKey("report_images.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    predicted_category = Column(
        Enum(ReportCategory),
        nullable=False
    )
    confidence = Column(
        Float,
        nullable=False
    )
    model_version = Column(
        String(50),
        default="road-vision-v1.0",
        nullable=False
    )
    probabilities_json = Column(
        Text,
        nullable=True
    )

    # Human Override & Verification Fields
    user_suggested_category = Column(
        Enum(ReportCategory),
        nullable=True
    )
    authority_verified_category = Column(
        Enum(ReportCategory),
        nullable=True
    )
    is_corrected = Column(
        Boolean,
        default=False,
        nullable=False
    )
    corrected_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    corrected_at = Column(
        DateTime(timezone=True),
        nullable=True
    )
    correction_notes = Column(
        Text,
        nullable=True
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    image = relationship("ReportImage", back_populates="classification")
    corrected_by = relationship("User", foreign_keys=[corrected_by_user_id])
