import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

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

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    category = Column(
        Enum(ReportCategory),
        nullable=False,
        index=True
    )
    title = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    address = Column(String(255), nullable=True)
    severity = Column(
        Enum(ReportSeverity),
        nullable=False,
        index=True
    )
    status = Column(
        Enum(ReportStatus),
        default=ReportStatus.REPORTED,
        nullable=False,
        index=True
    )
    priority_score = Column(Float, default=0.0, nullable=False, index=True)
    priority_level = Column(
        Enum(PriorityLevel),
        default=PriorityLevel.LOW,
        nullable=False,
        index=True
    )
    report_count = Column(Integer, default=1, nullable=False)

    # Multi-factor priority context fields
    traffic_density = Column(
        Enum(TrafficDensity),
        default=TrafficDensity.MEDIUM,
        nullable=False
    )
    location_zone = Column(
        Enum(LocationZone),
        default=LocationZone.RESIDENTIAL,
        nullable=False
    )
    assigned_department = Column(
        Enum(AuthorityDepartment),
        nullable=True,
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
    reports = relationship(
        "RoadReport",
        back_populates="issue",
        order_by="desc(RoadReport.created_at)"
    )
    assignments = relationship(
        "IssueAssignment",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="desc(IssueAssignment.assigned_at)"
    )
    status_history = relationship(
        "IssueStatusHistory",
        back_populates="issue",
        cascade="all, delete-orphan",
        order_by="asc(IssueStatusHistory.created_at)"
    )
