import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

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

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    issue_id = Column(
        UUID(as_uuid=True),
        ForeignKey("issues.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    department = Column(
        Enum(AuthorityDepartment),
        nullable=False
    )
    assigned_to_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    notes = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    issue = relationship("Issue", back_populates="assignments")
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_user_id])
