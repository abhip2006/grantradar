"""
Grant Mechanisms and Intelligence Graph Database Models
SQLAlchemy ORM models for grant mechanism information and competition data.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, Float, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base classes and type decorators from the main models file
from backend.models import Base, GUID, JSONB

if TYPE_CHECKING:
    from backend.models import Grant


class GrantMechanism(Base):
    """
    Grant mechanism reference data.

    Stores information about grant mechanisms from various funding agencies
    (NIH, NSF, etc.) including typical budgets, success rates, and
    application tips for each mechanism type.
    """

    __tablename__ = "grant_mechanisms"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the mechanism",
    )
    code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        doc="Grant mechanism code (e.g., 'R01', 'R21', 'K99')",
    )
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Grant mechanism name/title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed description of the mechanism",
    )
    funding_agency: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Funding agency (e.g., 'NIH', 'NSF')",
    )
    category: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Mechanism category (e.g., 'research', 'career', 'training', 'fellowship')",
    )
    typical_duration_months: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Typical project duration in months",
    )
    typical_budget_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Typical minimum annual budget in USD",
    )
    typical_budget_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Typical maximum annual budget in USD",
    )
    success_rate_overall: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Overall success rate (0.0 to 1.0)",
    )
    success_rate_new: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Success rate for new applications (0.0 to 1.0)",
    )
    success_rate_renewal: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Success rate for renewal applications (0.0 to 1.0)",
    )
    success_rate_resubmission: Mapped[Optional[float]] = mapped_column(
        nullable=True,
        doc="Success rate for resubmitted applications (0.0 to 1.0)",
    )
    avg_review_score_funded: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Average review score for funded applications",
    )
    competition_level: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        doc="Competitiveness level: 'low', 'medium', 'high', 'very_high'",
    )
    estimated_applicants_per_cycle: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated number of applicants per funding cycle",
    )
    review_criteria: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Review criteria and their order of importance",
    )
    eligibility_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Notes about eligibility requirements",
    )
    tips: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Application tips and best practices",
    )
    last_updated: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the mechanism data was last updated",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    # Relationships
    competition_snapshots: Mapped[list["CompetitionSnapshot"]] = relationship(
        "CompetitionSnapshot",
        back_populates="mechanism",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_grant_mechanisms_code", code),
        Index("ix_grant_mechanisms_funding_agency", funding_agency),
        Index("ix_grant_mechanisms_category", category),
        Index("ix_grant_mechanisms_competition_level", competition_level),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"<GrantMechanism(code='{self.code}', name='{self.name[:30]}...')>"


class FundedProject(Base):
    """
    Historical funded grants from NIH Reporter and other sources.

    Stores data about successfully funded projects to enable analysis
    of success patterns, competition metrics, and reviewer preferences.
    """

    __tablename__ = "funded_projects"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the funded project",
    )
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Data source (e.g., 'nih', 'nsf')",
    )
    external_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        doc="Unique identifier from the source system (e.g., NIH project number)",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Project title",
    )
    abstract: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Project abstract/summary",
    )
    mechanism: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Grant mechanism (e.g., R01, R21, K01)",
    )
    activity_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="NIH activity code",
    )
    funding_agency: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Primary funding agency (NIH, NSF, etc.)",
    )
    funding_institute: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Specific institute (e.g., NCI, NHLBI for NIH)",
    )
    award_amount: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Total award amount in USD",
    )
    award_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Date of award",
    )
    project_start: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Project start date",
    )
    project_end: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Project end date",
    )
    pi_name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Principal Investigator name",
    )
    pi_institution: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="PI's institution name",
    )
    pi_institution_type: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Type of institution (university, research_institute, etc.)",
    )
    fiscal_year: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Fiscal year of the award",
    )
    is_new: Mapped[Optional[bool]] = mapped_column(
        Boolean,
        nullable=True,
        doc="Whether this is a new grant vs renewal",
    )
    keywords: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Keywords and MeSH terms associated with the project",
    )
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Raw data from source for debugging/auditing",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    __table_args__ = (
        Index("ix_funded_projects_mechanism", mechanism),
        Index("ix_funded_projects_fiscal_year", fiscal_year),
        Index("ix_funded_projects_funding_institute", funding_institute),
        Index("ix_funded_projects_source", source),
    )

    def __repr__(self) -> str:
        return f"<FundedProject(id={self.id}, external_id='{self.external_id}', mechanism='{self.mechanism}')>"


class CompetitionSnapshot(Base):
    """
    Periodic snapshot of competition data for a grant.

    Captures point-in-time competition metrics for grants to track
    how competition levels change over time and relative to other
    open opportunities.
    """

    __tablename__ = "competition_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the snapshot",
    )
    grant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=True,
        doc="Reference to the grant",
    )
    mechanism_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("grant_mechanisms.id", ondelete="SET NULL"),
        nullable=True,
        doc="Reference to the grant mechanism",
    )
    snapshot_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        doc="Date of the snapshot",
    )
    estimated_applicants: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Estimated number of applicants",
    )
    similar_grants_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of similar grants currently open",
    )
    competition_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Competition score (0.0 to 1.0, higher = more competitive)",
    )
    factors: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Explanation of competition factors",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    # Relationships
    grant: Mapped[Optional["Grant"]] = relationship(
        "Grant",
    )
    mechanism: Mapped[Optional["GrantMechanism"]] = relationship(
        "GrantMechanism",
        back_populates="competition_snapshots",
    )

    __table_args__ = (
        Index("ix_competition_snapshots_grant_id", grant_id),
        Index("ix_competition_snapshots_mechanism_id", mechanism_id),
        Index("ix_competition_snapshots_snapshot_date", snapshot_date),
    )

    def __repr__(self) -> str:
        return f"<CompetitionSnapshot(id={self.id}, grant_id={self.grant_id}, competition_score={self.competition_score})>"
