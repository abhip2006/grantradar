"""
Document Component Library Database Models
SQLAlchemy ORM models for reusable document components and version control.
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base classes and type decorators from the main models file
from backend.models import Base, GUID, JSONB


class DocumentComponent(Base):
    """
    Reusable document component for grant applications.

    Stores frequently used content like facilities descriptions, biosketches,
    boilerplate text for human subjects, vertebrate animals, etc.
    Supports versioning through parent_id chain.
    """

    __tablename__ = "document_components"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the document component",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Component category: 'facilities', 'equipment', 'biosketch', 'boilerplate', 'institution'",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="User-defined name for the component",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Optional description of the component",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="The actual content of the component",
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional structured metadata (e.g., author info for biosketch)",
    )
    tags: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Searchable tags for the component",
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
        doc="Version number of the component",
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this is the current/active version",
    )
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("document_components.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to previous version (for version chain)",
    )
    is_archived: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether the component is archived (soft delete)",
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
    usages: Mapped[List["ComponentUsage"]] = relationship(
        "ComponentUsage",
        back_populates="component",
        cascade="all, delete-orphan",
    )
    # Self-referential relationship for versioning
    parent: Mapped[Optional["DocumentComponent"]] = relationship(
        "DocumentComponent",
        remote_side="DocumentComponent.id",
        back_populates="children",
        foreign_keys=[parent_id],
    )
    children: Mapped[List["DocumentComponent"]] = relationship(
        "DocumentComponent",
        back_populates="parent",
        foreign_keys="DocumentComponent.parent_id",
    )

    __table_args__ = (
        Index("ix_document_components_user_id", user_id),
        Index("ix_document_components_category", category),
        Index("ix_document_components_is_current", is_current),
        Index("ix_document_components_is_archived", is_archived),
        Index("ix_document_components_parent_id", parent_id),
    )

    def __repr__(self) -> str:
        return f"<DocumentComponent(id={self.id}, name='{self.name}', category='{self.category}')>"


class ComponentUsage(Base):
    """
    Tracks where document components are used in grant applications.

    Records each instance where a component is inserted into an application,
    enabling usage analytics and tracking which applications use which components.
    """

    __tablename__ = "component_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the usage record",
    )
    component_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("document_components.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the document component",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    section: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Which section of the application the component was used in",
    )
    inserted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who inserted the component",
    )
    used_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the component was used",
    )

    # Relationships
    component: Mapped["DocumentComponent"] = relationship(
        "DocumentComponent",
        back_populates="usages",
    )

    __table_args__ = (
        Index("ix_component_usage_component_id", component_id),
        Index("ix_component_usage_kanban_card_id", kanban_card_id),
        Index("ix_component_usage_used_at", used_at),
    )

    def __repr__(self) -> str:
        return f"<ComponentUsage(id={self.id}, component_id={self.component_id}, card_id={self.kanban_card_id})>"


class DocumentVersion(Base):
    """
    Version snapshot for grant application documents.

    Stores versioned content for application sections, enabling
    document history tracking, diff viewing, and restore functionality.
    """

    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the document version",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    section: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Section name (e.g., 'specific_aims', 'research_strategy', 'budget')",
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Sequential version number within the card/section",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="The versioned content",
    )
    snapshot_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="User-defined name for named snapshots (e.g., 'Pre-review draft')",
    )
    change_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Description of what changed in this version",
    )
    file_path: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="Path to attached file if any",
    )
    file_size: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="File size in bytes",
    )
    file_type: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="MIME type or file extension",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created this version",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the version was created",
    )

    __table_args__ = (
        Index("ix_document_versions_kanban_card_id", kanban_card_id),
        Index("ix_document_versions_section", section),
        Index("ix_document_versions_version_number", kanban_card_id, section, version_number),
        Index("ix_document_versions_created_at", created_at),
        UniqueConstraint("kanban_card_id", "section", "version_number", name="uq_document_versions_card_section_version"),
    )

    def __repr__(self) -> str:
        return f"<DocumentVersion(id={self.id}, card_id={self.kanban_card_id}, section='{self.section}', v{self.version_number})>"
