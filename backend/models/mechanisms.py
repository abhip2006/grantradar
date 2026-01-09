"""
Grant Mechanisms Database Models
SQLAlchemy ORM models for grant mechanism information (NIH, NSF, etc.).
"""
import uuid
from datetime import datetime
from typing import Any, List, Optional

from sqlalchemy import Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column

# Import base classes and type decorators from the main models file
from backend.models import Base, GUID, JSONB


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
    tips: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Application tips and best practices",
    )
    last_updated: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When the mechanism data was last updated",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    __table_args__ = (
        Index("ix_grant_mechanisms_code", code),
        Index("ix_grant_mechanisms_funding_agency", funding_agency),
        Index("ix_grant_mechanisms_category", category),
        Index("ix_grant_mechanisms_competition_level", competition_level),
    )

    def __repr__(self) -> str:
        return f"<GrantMechanism(code='{self.code}', name='{self.name[:30]}...')>"
