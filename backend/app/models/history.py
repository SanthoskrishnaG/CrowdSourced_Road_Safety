import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.report import ReportStatus


class IssueStatusHistory(Base):
    """
    Immutable audit trail recording every state change and comment on an issue.
    """
    __tablename__ = "issue_status_history"

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
    previous_status = Column(
        Enum(ReportStatus),
        nullable=True
    )
    new_status = Column(
        Enum(ReportStatus),
        nullable=False
    )
    changed_by_user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    comment = Column(Text, nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    issue = relationship("Issue", back_populates="status_history")
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])
