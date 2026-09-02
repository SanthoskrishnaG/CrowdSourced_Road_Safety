import uuid
import enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, Text, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.report import ReportCategory, ReportSeverity, ReportStatus
from app.models.assignment import AuthorityDepartment


class PriorityLevel(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class LocationZone(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    SCHOOL = "SCHOOL"
    MAIN_ROAD = "MAIN_ROAD"
    JUNCTION = "JUNCTION"
    RESIDENTIAL = "RESIDENTIAL"
    OTHER = "OTHER"


class TrafficDensity(str, enum.Enum):
    HEAVY = "HEAVY"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class Issue(Base):
    __tablename__ = "issues"
    __table_args__ = (
        Index("idx_issues_lat_long", "latitude", "longitude"),
        Index("idx_issues_status_priority", "status", "priority_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    category: Mapped[ReportCategory] = mapped_column(
        Enum(ReportCategory),
        nullable=False,
        index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severity: Mapped[ReportSeverity] = mapped_column(
        Enum(ReportSeverity),
        nullable=False,
        index=True
    )
    status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False,
        index=True
    )
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False, index=True)
    priority_level: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel),
        default=PriorityLevel.LOW,
        nullable=False,
        index=True
    )
    report_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Multi-factor priority context fields
    traffic_density: Mapped[TrafficDensity] = mapped_column(
        Enum(TrafficDensity),
        default=TrafficDensity.MEDIUM,
        nullable=False
    )
    location_zone: Mapped[LocationZone] = mapped_column(
        Enum(LocationZone),
        default=LocationZone.RESIDENTIAL,
        nullable=False
    )
    assigned_department: Mapped[Optional[AuthorityDepartment]] = mapped_column(
        Enum(AuthorityDepartment),
        nullable=True,
        index=True
    )
    road_segment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("road_segments.id", ondelete="SET NULL"),
        nullable=True,
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

    confirmations_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    road_segment: Mapped[Optional["RoadSegment"]] = relationship("RoadSegment", back_populates="issues")
    reports: Mapped[List["RoadReport"]] = relationship(
        "RoadReport",
        back_populates="issue",
        order_by="desc(RoadReport.created_at)"
    )
    assignments: Mapped[List["IssueAssignment"]] = relationship(
        "IssueAssignment",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(IssueAssignment.assigned_at)"
    )
    status_history: Mapped[List["IssueStatusHistory"]] = relationship(
        "IssueStatusHistory",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="asc(IssueStatusHistory.created_at)"
    )
    priority_history: Mapped[List["PriorityHistory"]] = relationship(
        "PriorityHistory",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(PriorityHistory.created_at)"
    )

