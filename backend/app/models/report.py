import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Enum, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class ReportCategory(str, enum.Enum):
    POTHOLE = "POTHOLE"
    ROAD_DAMAGE = "ROAD_DAMAGE"
    BROKEN_STREETLIGHT = "BROKEN_STREETLIGHT"
    BLOCKED_ROAD = "BLOCKED_ROAD"
    GARBAGE = "GARBAGE"
    FLOODING = "FLOODING"
    DAMAGED_SIGN = "DAMAGED_SIGN"
    OBSTRUCTION = "OBSTRUCTION"
    OTHER = "OTHER"


class ReportSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ReportStatus(str, enum.Enum):
    REPORTED = "REPORTED"
    VERIFIED = "VERIFIED"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    FIXED = "FIXED"
    CLOSED = "CLOSED"
    REJECTED = "REJECTED"


class RoadReport(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_lat_long", "latitude", "longitude"),
        Index("idx_reports_status_created", "status", "created_at"),
    )

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    category = Column(
        Enum(ReportCategory),
        nullable=False,
        index=True
    )
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(
        Enum(ReportSeverity),
        nullable=False,
        index=True
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    location_accuracy = Column(Float, nullable=True)
    status = Column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False,
        index=True
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    reporter = relationship("User", back_populates="reports")
    issue_id = Column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    issue = relationship("Issue", back_populates="reports")
    images = relationship(
        "ReportImage",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportImage.uploaded_at"
    )


