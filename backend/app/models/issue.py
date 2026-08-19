import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.report import ReportCategory, ReportSeverity, ReportStatus


class Issue(Base):
    __tablename__ = "issues"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    category = Column(
        Enum(ReportCategory),
        nullable=False
    )
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    severity = Column(
        Enum(ReportSeverity),
        nullable=False
    )
    status = Column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False
    )
    priority_score = Column(Float, default=0.0, nullable=False)
    report_count = Column(Integer, default=1, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    reports = relationship(
        "RoadReport",
        back_populates="issue",
        order_by="desc(RoadReport.created_at)"
    )
