import uuid
import enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Enum, ForeignKey, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
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
    REOPENED = "REOPENED"
    REJECTED = "REJECTED"


class RoadReport(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_lat_long", "latitude", "longitude"),
        Index("idx_reports_status_created", "status", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[ReportSeverity] = mapped_column(
        Enum(ReportSeverity),
        nullable=False,
        index=True
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    location_accuracy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(25), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    reporter: Mapped["User"] = relationship("User", back_populates="reports")
    issue_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    issue: Mapped[Optional["Issue"]] = relationship("Issue", back_populates="reports")
    road_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("road_segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    road_segment: Mapped[Optional["RoadSegment"]] = relationship("RoadSegment", back_populates="reports")
    images: Mapped[List["ReportImage"]] = relationship(
        "ReportImage",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="ReportImage.uploaded_at"
    )
