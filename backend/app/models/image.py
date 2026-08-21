import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportImage(Base):
    __tablename__ = "report_images"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    report_id = Column(
        UUID(as_uuid=True),
        ForeignKey("reports.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500), nullable=True)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    uploaded_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    report = relationship("RoadReport", back_populates="images")
    classification = relationship(
        "ImageClassification",
        back_populates="image",
        uselist=False,
        cascade="all, delete-orphan"
    )
