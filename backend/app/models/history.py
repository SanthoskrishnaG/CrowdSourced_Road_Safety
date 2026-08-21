import uuid
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import Column, Enum, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.report import ReportStatus


class IssueStatusHistory(Base):
    """
    Immutable audit trail recording every state change and comment on an issue.
    """
    __tablename__ = "issue_status_history"

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
    previous_status: Mapped[Optional[ReportStatus]] = mapped_column(
        Enum(ReportStatus),
        nullable=True
    )
    new_status: Mapped[ReportStatus] = mapped_column(
        Enum(ReportStatus),
        nullable=False
    )
    changed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    issue: Mapped["Issue"] = relationship("Issue", back_populates="status_history")
    changed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[changed_by_user_id])
