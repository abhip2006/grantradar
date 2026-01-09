"""
Checklist models for grant application workflow management.
Provides SQLAlchemy ORM models for checklist templates and application checklists.

JSONB Field Types:
- items: List[ChecklistItemDict] - see backend.schemas.jsonb_types for structure
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base classes and type decorators from the main models module
import backend.models as models_module

Base = models_module.Base
GUID = models_module.GUID
JSONB = models_module.JSONB


class ChecklistTemplate(Base):
    """
    Checklist template for funder-specific requirements.

    Stores reusable checklist templates with items that can be applied
    to grant applications. Templates can be system-wide (e.g., NIH, NSF)
    or user-created for custom workflows.
    """

    __tablename__ = "checklist_templates"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the template",
    )
    funder: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Funding organization (e.g., 'NIH', 'NSF', 'DOE')",
    )
    mechanism: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Grant mechanism type (e.g., 'R01', 'R21', 'CAREER')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Template name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Template description",
    )
    items: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="Checklist items: List[ChecklistItemDict] - [{id, title, description, required, weight, category, dependencies}]",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this is a system template (read-only for users)",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created this template (null for system templates)",
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
    application_checklists: Mapped[List["ApplicationChecklist"]] = relationship(
        "ApplicationChecklist",
        back_populates="template",
    )

    __table_args__ = (
        Index("ix_checklist_templates_funder", funder),
        Index("ix_checklist_templates_mechanism", mechanism),
        Index("ix_checklist_templates_is_system", is_system),
    )

    def __repr__(self) -> str:
        return f"<ChecklistTemplate(id={self.id}, name='{self.name}', funder='{self.funder}')>"


class ApplicationChecklist(Base):
    """
    Checklist instance for a grant application.

    Stores the actual checklist with completion status for each item,
    tracking progress and completion timestamps.
    """

    __tablename__ = "application_checklists"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the checklist",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("checklist_templates.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to the source template (null for custom checklists)",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Checklist name (copied from template or custom)",
    )
    items: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="Checklist items with status: List[ChecklistItemDict] - [{item_id, title, description, required, weight, category, completed, completed_at, completed_by, notes}]",
    )
    progress_percent: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
        doc="Weighted completion percentage (0.0 to 100.0)",
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
    template: Mapped[Optional["ChecklistTemplate"]] = relationship(
        "ChecklistTemplate",
        back_populates="application_checklists",
    )

    __table_args__ = (
        Index("ix_application_checklists_kanban_card_id", kanban_card_id),
        Index("ix_application_checklists_template_id", template_id),
        UniqueConstraint(
            "kanban_card_id",
            "template_id",
            name="uq_application_checklist_card_template",
        ),
    )

    def __repr__(self) -> str:
        return f"<ApplicationChecklist(id={self.id}, name='{self.name}', progress={self.progress_percent:.1f}%)>"

    def calculate_progress(self) -> float:
        """
        Calculate weighted completion percentage.

        Items with weight contribute proportionally to completion.
        Required items must be completed for 100% progress.
        """
        if not self.items:
            return 0.0

        total_weight = sum(item.get("weight", 1.0) for item in self.items)
        if total_weight == 0:
            return 0.0

        completed_weight = sum(
            item.get("weight", 1.0)
            for item in self.items
            if item.get("completed", False)
        )

        return (completed_weight / total_weight) * 100.0
