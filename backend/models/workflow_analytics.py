"""
Workflow Analytics Models

SQLAlchemy ORM models for tracking workflow events and analytics
in the grant application pipeline.

JSONB Field Types:
- metadata_: WorkflowEventMetadataDict - see backend.schemas.jsonb_types for structure
- metrics: WorkflowMetricsDict - see backend.schemas.jsonb_types for structure
"""
import uuid
from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import Date, ForeignKey, Index, String, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models import Base, GUID, JSONB


class WorkflowEvent(Base):
    """
    Workflow event tracking for grant applications.

    Records individual events in the application workflow such as:
    - Stage transitions (stage_enter, stage_exit)
    - User actions (note_added, subtask_completed, etc.)
    - Milestones (submission, review_completed, etc.)

    Used for calculating time spent in each stage and identifying bottlenecks.
    """

    __tablename__ = "workflow_events"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the workflow event",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    event_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of event: 'stage_enter', 'stage_exit', 'action', 'milestone'",
    )
    stage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Stage name associated with this event (e.g., 'researching', 'writing')",
    )
    previous_stage: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Previous stage (for stage transition events)",
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional event metadata: WorkflowEventMetadataDict",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id"),
        nullable=True,
        doc="User who triggered the event (null for system events)",
    )
    occurred_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the event occurred",
    )

    # Relationships
    application = relationship(
        "GrantApplication",
        foreign_keys=[kanban_card_id],
        doc="The grant application this event belongs to",
    )
    user = relationship(
        "User",
        foreign_keys=[user_id],
        doc="User who triggered the event",
    )

    __table_args__ = (
        Index("ix_workflow_events_kanban_card_id", kanban_card_id),
        Index("ix_workflow_events_event_type", event_type),
        Index("ix_workflow_events_stage", stage),
        Index("ix_workflow_events_occurred_at", occurred_at.desc()),
        Index("ix_workflow_events_user_id", user_id),
    )

    def __repr__(self) -> str:
        return f"<WorkflowEvent(id={self.id}, type='{self.event_type}', stage='{self.stage}')>"


class WorkflowAnalytics(Base):
    """
    Aggregated workflow analytics for a user over a time period.

    Stores pre-computed metrics to avoid expensive real-time calculations:
    - Average time per stage
    - Bottleneck identification
    - Completion rates
    - Success rates by workflow pattern

    Generated periodically by Celery tasks.
    """

    __tablename__ = "workflow_analytics"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the analytics record",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the user",
    )
    period_start: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="Start of the analytics period",
    )
    period_end: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        doc="End of the analytics period",
    )
    period_type: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="weekly",
        doc="Type of period: 'daily', 'weekly', 'monthly', 'quarterly'",
    )
    metrics: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Aggregated metrics: WorkflowMetricsDict - {avg_time_per_stage, bottlenecks, completion_rate, ...}",
    )
    generated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When these analytics were generated",
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        doc="User these analytics belong to",
    )

    __table_args__ = (
        Index("ix_workflow_analytics_user_id", user_id),
        Index("ix_workflow_analytics_period", period_start, period_end),
        Index("ix_workflow_analytics_period_type", period_type),
        Index("ix_workflow_analytics_generated_at", generated_at.desc()),
        UniqueConstraint(
            "user_id",
            "period_start",
            "period_end",
            "period_type",
            name="uq_workflow_analytics_user_period",
        ),
    )

    def __repr__(self) -> str:
        return f"<WorkflowAnalytics(id={self.id}, user_id={self.user_id}, period={self.period_start} to {self.period_end})>"


# Event type constants for consistency
class WorkflowEventType:
    """Constants for workflow event types."""

    STAGE_ENTER = "stage_enter"
    STAGE_EXIT = "stage_exit"
    ACTION = "action"
    MILESTONE = "milestone"
    NOTE_ADDED = "note_added"
    SUBTASK_COMPLETED = "subtask_completed"
    SUBTASK_ADDED = "subtask_added"
    ATTACHMENT_ADDED = "attachment_added"
    PRIORITY_CHANGED = "priority_changed"
    DEADLINE_SET = "deadline_set"
    ASSIGNEE_ADDED = "assignee_added"
    ASSIGNEE_REMOVED = "assignee_removed"


# Stage constants
class WorkflowStage:
    """Constants for workflow stages."""

    RESEARCHING = "researching"
    WRITING = "writing"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    REJECTED = "rejected"

    @classmethod
    def all_stages(cls) -> list[str]:
        """Get all stages in order."""
        return [cls.RESEARCHING, cls.WRITING, cls.SUBMITTED, cls.AWARDED, cls.REJECTED]

    @classmethod
    def active_stages(cls) -> list[str]:
        """Get stages that are still in progress."""
        return [cls.RESEARCHING, cls.WRITING, cls.SUBMITTED]

    @classmethod
    def terminal_stages(cls) -> list[str]:
        """Get terminal stages (outcomes)."""
        return [cls.AWARDED, cls.REJECTED]


__all__ = [
    "WorkflowEvent",
    "WorkflowAnalytics",
    "WorkflowEventType",
    "WorkflowStage",
]
