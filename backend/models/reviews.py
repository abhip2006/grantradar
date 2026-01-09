"""
Internal Review Workflow Models
SQLAlchemy ORM models for the review workflow system.

JSONB Field Types:
- stages: List[WorkflowStageDict] - see backend.schemas.jsonb_types for structure
- permissions: TeamMemberPermissionsDict - see backend.schemas.jsonb_types for structure
- metadata_: ReviewActionMetadataDict - see backend.schemas.jsonb_types for structure
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    TIMESTAMP,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base classes and type decorators from the main models module
import backend.models as models_module

Base = models_module.Base
GUID = models_module.GUID
JSONB = models_module.JSONB


class ReviewWorkflow(Base):
    """
    Review workflow template configuration.

    Defines the stages and rules for an internal review process
    that applications can follow.
    """

    __tablename__ = "review_workflows"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the workflow",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Workflow name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Workflow description",
    )
    stages: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        doc="Workflow stages: List[WorkflowStageDict] - [{order, name, required_role, sla_hours, auto_escalate}]",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is the default workflow for the user",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this workflow is active and can be used",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    reviews: Mapped[List["ApplicationReview"]] = relationship(
        "ApplicationReview",
        back_populates="workflow",
    )

    __table_args__ = (
        Index("ix_review_workflows_user_id", user_id),
        Index("ix_review_workflows_is_default", is_default),
        Index("ix_review_workflows_is_active", is_active),
    )

    def __repr__(self) -> str:
        return f"<ReviewWorkflow(id={self.id}, name='{self.name}')>"


class ApplicationReview(Base):
    """
    Active review process for an application.

    Tracks the current state of a review process attached
    to a kanban card/grant application.
    """

    __tablename__ = "application_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the review",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    workflow_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("review_workflows.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to the workflow being used",
    )
    current_stage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Current stage index in the workflow",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        nullable=False,
        doc="Review status: pending, in_review, approved, rejected, escalated",
    )
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who started the review",
    )
    started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the review was started",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the review was completed",
    )
    stage_started_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the current stage was started (for SLA tracking)",
    )
    escalation_sent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether escalation notification has been sent for current stage",
    )

    # Relationships
    application: Mapped["GrantApplication"] = relationship(
        "GrantApplication",
        foreign_keys=[kanban_card_id],
    )
    workflow: Mapped[Optional["ReviewWorkflow"]] = relationship(
        "ReviewWorkflow",
        back_populates="reviews",
    )
    starter: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[started_by],
    )
    actions: Mapped[List["ReviewStageAction"]] = relationship(
        "ReviewStageAction",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewStageAction.acted_at",
    )

    __table_args__ = (
        Index("ix_application_reviews_kanban_card_id", kanban_card_id),
        Index("ix_application_reviews_workflow_id", workflow_id),
        Index("ix_application_reviews_status", status),
        Index("ix_application_reviews_current_stage", current_stage),
    )

    def __repr__(self) -> str:
        return f"<ApplicationReview(id={self.id}, status='{self.status}', stage={self.current_stage})>"


class ReviewStageAction(Base):
    """
    Action taken at a review stage.

    Records approvals, rejections, comments, and other actions
    taken by reviewers during the review process.
    """

    __tablename__ = "review_stage_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the action",
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("application_reviews.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the review",
    )
    stage_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Stage index when action was taken",
    )
    stage_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Name of the stage when action was taken",
    )
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who performed the action",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Action type: approved, rejected, returned, commented",
    )
    comments: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Comments or feedback provided with the action",
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional action metadata: ReviewActionMetadataDict",
    )
    acted_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the action was taken",
    )

    # Relationships
    review: Mapped["ApplicationReview"] = relationship(
        "ApplicationReview",
        back_populates="actions",
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewer_id],
    )

    __table_args__ = (
        Index("ix_review_stage_actions_review_id", review_id),
        Index("ix_review_stage_actions_reviewer_id", reviewer_id),
        Index("ix_review_stage_actions_stage_order", stage_order),
        Index("ix_review_stage_actions_action", action),
        Index("ix_review_stage_actions_acted_at", acted_at),
    )

    def __repr__(self) -> str:
        return f"<ReviewStageAction(id={self.id}, action='{self.action}', stage={self.stage_order})>"


class ApplicationTeamMember(Base):
    """
    Team member assigned to work on an application.

    Tracks role-based access and permissions for team members
    working on a specific grant application.
    """

    __tablename__ = "application_team_members"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the team member assignment",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the team member user",
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Role in the application: pi, co_i, grant_writer, reviewer, admin",
    )
    permissions: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Permissions: TeamMemberPermissionsDict - {can_edit, can_approve, can_submit, sections: [...]}",
    )
    added_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who added this team member",
    )
    added_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the team member was added",
    )

    # Relationships
    application: Mapped["GrantApplication"] = relationship(
        "GrantApplication",
        foreign_keys=[kanban_card_id],
    )
    user: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
    )
    added_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[added_by],
    )

    __table_args__ = (
        UniqueConstraint("kanban_card_id", "user_id", name="uq_application_team_member"),
        Index("ix_application_team_members_kanban_card_id", kanban_card_id),
        Index("ix_application_team_members_user_id", user_id),
        Index("ix_application_team_members_role", role),
    )

    def __repr__(self) -> str:
        return f"<ApplicationTeamMember(id={self.id}, role='{self.role}')>"


# Type hints for relationships (to avoid circular imports)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from backend.models import User, GrantApplication
