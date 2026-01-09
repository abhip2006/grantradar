"""
Compliance Scanner Database Models
SQLAlchemy ORM models for compliance rules and scan results.

JSONB Field Types:
- rules: List[ComplianceRuleItemDict] - see backend.schemas.jsonb_types for structure
- results: List[ComplianceScanResultDict] - see backend.schemas.jsonb_types for structure
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base classes and type decorators from the main models module
import backend.models as models_module

Base = models_module.Base
GUID = models_module.GUID
JSONB = models_module.JSONB


class ComplianceRule(Base):
    """
    Compliance rule set for funder requirements validation.

    Stores rules for checking document compliance against funder-specific
    requirements such as page limits, font sizes, margins, required sections, etc.
    """

    __tablename__ = "compliance_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the compliance rule set",
    )
    funder: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Funding organization (e.g., 'NIH', 'NSF', 'DOE')",
    )
    mechanism: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Grant mechanism type (e.g., 'R01', 'R21', 'K99')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Name of the compliance rule set",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Description of what this rule set validates",
    )
    rules: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="List of rules: List[ComplianceRuleItemDict] - [{type, name, params, severity, message}]",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether this rule set is active and available for use",
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        doc="Whether this is a system-defined rule set (read-only)",
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who created this rule set (null for system rules)",
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
    scans: Mapped[List["ComplianceScan"]] = relationship(
        "ComplianceScan",
        back_populates="rule_set",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_compliance_rules_funder_mechanism", funder, mechanism),
        Index("ix_compliance_rules_is_active", is_active),
        Index("ix_compliance_rules_is_system", is_system),
    )

    def __repr__(self) -> str:
        return f"<ComplianceRule(id={self.id}, funder='{self.funder}', name='{self.name}')>"


class ComplianceScan(Base):
    """
    Compliance scan result for a grant application document.

    Stores the results of running compliance checks against uploaded
    documents, including pass/fail status for each rule.
    """

    __tablename__ = "compliance_scans"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the compliance scan",
    )
    kanban_card_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("grant_applications.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant application (kanban card)",
    )
    rule_set_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("compliance_rules.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to the compliance rule set used",
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Type of document scanned (e.g., 'specific_aims', 'research_strategy', 'budget')",
    )
    file_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="Original filename of the scanned document",
    )
    file_content_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 hash of file content for duplicate detection",
    )
    results: Mapped[List[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        doc="Scan results: List[ComplianceScanResultDict] - [{rule_id, rule_name, passed, severity, message, location, details}]",
    )
    passed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of rules passed",
    )
    failed_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of rules failed (errors)",
    )
    warning_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Number of rules with warnings",
    )
    overall_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        doc="Overall scan status: 'pending', 'passed', 'failed', 'warning'",
    )
    scanned_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="User who initiated the scan",
    )
    scanned_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="When the scan was performed",
    )

    # Relationships
    rule_set: Mapped[Optional["ComplianceRule"]] = relationship(
        "ComplianceRule",
        back_populates="scans",
    )

    __table_args__ = (
        Index("ix_compliance_scans_kanban_card_id", kanban_card_id),
        Index("ix_compliance_scans_rule_set_id", rule_set_id),
        Index("ix_compliance_scans_document_type", document_type),
        Index("ix_compliance_scans_overall_status", overall_status),
        Index("ix_compliance_scans_scanned_at", scanned_at),
    )

    def __repr__(self) -> str:
        return f"<ComplianceScan(id={self.id}, document_type='{self.document_type}', status='{self.overall_status}')>"
