import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Enum, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.core.database import Base
from app.models.issue import PriorityLevel


class PriorityHistory(Base):
    __tablename__ = "priority_history"
    __table_args__ = (
        Index("idx_priority_history_issue_id", "issue_id"),
        Index("idx_priority_history_created_at", "created_at"),
    )

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
    previous_score: Mapped[float] = mapped_column(Float, nullable=False)
    new_score: Mapped[float] = mapped_column(Float, nullable=False)
    previous_level: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel),
        nullable=False
    )
    new_level: Mapped[PriorityLevel] = mapped_column(
        Enum(PriorityLevel),
        nullable=False
    )
    trigger_event: Mapped[str] = mapped_column(String(100), nullable=False)
    factor_breakdown: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationship
    issue = relationship("Issue", back_populates="priority_history")
