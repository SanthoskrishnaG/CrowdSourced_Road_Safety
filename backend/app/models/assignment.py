import uuid
import enum
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base


class AuthorityDepartment(str, enum.Enum):
    ROAD_DEPARTMENT = "ROAD_DEPARTMENT"
    ELECTRICAL_DEPARTMENT = "ELECTRICAL_DEPARTMENT"
    SANITATION_DEPARTMENT = "SANITATION_DEPARTMENT"
    TRAFFIC_DEPARTMENT = "TRAFFIC_DEPARTMENT"
    DRAINAGE_DEPARTMENT = "DRAINAGE_DEPARTMENT"
    GENERAL_WORKS = "GENERAL_WORKS"


class IssueAssignment(Base):
    """
    Tracks municipal department assignments and responsible officers for an issue.
    """
    __tablename__ = "issue_assignments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    issue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    department: Mapped[AuthorityDepartment] = mapped_column(
        Enum(AuthorityDepartment),
        nullable=False
    )
    assigned_to_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    issue: Mapped["Issue"] = relationship("Issue", back_populates="assignments")
    assigned_to: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_to_user_id])
    assigned_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_by_user_id])
