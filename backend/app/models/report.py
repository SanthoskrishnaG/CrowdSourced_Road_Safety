import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Enum, ForeignKey, DateTime, Text
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

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    reporter_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    category = Column(
        Enum(ReportCategory),
        nullable=False
    )
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(
        Enum(ReportSeverity),
        nullable=False
    )
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    status = Column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False
    )
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
    reporter = relationship("User", back_populates="reports")
