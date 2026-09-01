import uuid
import enum
from typing import Optional, List
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Enum, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class RoadType(str, enum.Enum):
    HIGHWAY = "HIGHWAY"
    ARTERIAL = "ARTERIAL"
    COLLECTOR = "COLLECTOR"
    LOCAL = "LOCAL"
    RESIDENTIAL = "RESIDENTIAL"


class RoadImportance(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RoadSegment(Base):
    """
    Represents a discrete municipal road corridor / street segment with start and end coordinates,
    road hierarchy classification, and priority importance weighting.
    """
    __tablename__ = "road_segments"
    __table_args__ = (
        Index("idx_road_segments_start", "start_latitude", "start_longitude"),
        Index("idx_road_segments_end", "end_latitude", "end_longitude"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    start_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    start_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    end_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    end_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    road_type: Mapped[RoadType] = mapped_column(
        Enum(RoadType),
        default=RoadType.ARTERIAL,
        nullable=False,
        index=True
    )
    importance: Mapped[RoadImportance] = mapped_column(
        Enum(RoadImportance),
        default=RoadImportance.MEDIUM,
        nullable=False,
        index=True
    )
    speed_limit_kmh: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=50)
    length_meters: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    reports: Mapped[List["RoadReport"]] = relationship("RoadReport", back_populates="road_segment")
    issues: Mapped[List["Issue"]] = relationship("Issue", back_populates="road_segment")
