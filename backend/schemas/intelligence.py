"""
Intelligence Graph schemas for API responses.
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MechanismSummary(BaseModel):
    """Summary of a grant mechanism for list views."""

    id: UUID = Field(..., description="Mechanism UUID")
    code: str = Field(..., description="Mechanism code (e.g., R01, K01)")
    name: str = Field(..., description="Full mechanism name")
    funding_agency: Optional[str] = Field(None, description="Funding agency")
    category: Optional[str] = Field(None, description="Category (research, career, etc.)")
    success_rate_overall: Optional[float] = Field(None, description="Overall success rate (0.0 to 1.0)")
    competition_level: Optional[str] = Field(None, description="Competition level")


class MechanismDetail(BaseModel):
    """Detailed information about a grant mechanism."""

    id: UUID = Field(..., description="Mechanism UUID")
    code: str = Field(..., description="Mechanism code")
    name: str = Field(..., description="Full mechanism name")
    description: Optional[str] = Field(None, description="Detailed description")
    funding_agency: Optional[str] = Field(None, description="Funding agency")
    category: Optional[str] = Field(None, description="Category")
    typical_duration_months: Optional[int] = Field(None, description="Typical duration")
    typical_budget_min: Optional[int] = Field(None, description="Typical min budget")
    typical_budget_max: Optional[int] = Field(None, description="Typical max budget")
    success_rate_overall: Optional[float] = Field(None, description="Overall success rate")
    success_rate_new: Optional[float] = Field(None, description="New application success rate")
    success_rate_renewal: Optional[float] = Field(None, description="Renewal success rate")
    success_rate_resubmission: Optional[float] = Field(None, description="Resubmission success rate")
    avg_review_score_funded: Optional[float] = Field(None, description="Average review score for funded")
    competition_level: Optional[str] = Field(None, description="Competition level")
    estimated_applicants_per_cycle: Optional[int] = Field(None, description="Estimated applicants per cycle")
    review_criteria: Optional[dict[str, Any]] = Field(None, description="Review criteria")
    eligibility_notes: Optional[str] = Field(None, description="Eligibility notes")
    tips: Optional[list[str]] = Field(None, description="Tips for applicants")
    last_updated: Optional[datetime] = Field(None, description="Last update timestamp")

    # Computed fields from funded projects
    funded_projects_count: int = Field(0, description="Number of funded projects in database")
    avg_award_amount: Optional[float] = Field(None, description="Average award amount")


class MechanismListResponse(BaseModel):
    """Response for mechanism list endpoint."""

    mechanisms: list[MechanismSummary] = Field(..., description="List of mechanisms")
    total: int = Field(..., description="Total number of mechanisms")


class FundedProjectSummary(BaseModel):
    """Summary of a funded project."""

    id: UUID = Field(..., description="Project UUID")
    external_id: str = Field(..., description="External project ID")
    title: str = Field(..., description="Project title")
    mechanism: Optional[str] = Field(None, description="Grant mechanism")
    pi_name: Optional[str] = Field(None, description="PI name")
    pi_institution: Optional[str] = Field(None, description="PI institution")
    award_amount: Optional[int] = Field(None, description="Award amount")
    fiscal_year: Optional[int] = Field(None, description="Fiscal year")
    is_new: Optional[bool] = Field(None, description="Is new grant")


class TopInstitute(BaseModel):
    """Top institute by funding."""

    institution: str = Field(..., description="Institution name")
    funded_count: int = Field(..., description="Number of funded projects")
    total_funding: Optional[int] = Field(None, description="Total funding amount")


class CompetitionFactor(BaseModel):
    """A factor contributing to competition level."""

    factor: str = Field(..., description="Factor description")
    impact: Optional[str] = Field(None, description="Impact level (positive, negative, neutral)")


class CompetitionData(BaseModel):
    """Competition data for a grant."""

    grant_id: UUID = Field(..., description="Grant UUID")
    mechanism_code: Optional[str] = Field(None, description="Grant mechanism code")
    competition_score: Optional[float] = Field(
        None, description="Competition score (0.0 to 1.0, higher = more competitive)"
    )
    estimated_applicants: Optional[int] = Field(None, description="Estimated number of applicants")
    similar_grants_count: Optional[int] = Field(None, description="Number of similar open grants")
    success_rate: Optional[float] = Field(None, description="Historical success rate for this mechanism")
    competition_level: Optional[str] = Field(None, description="Competition level (low, medium, high, very_high)")
    factors: list[str] = Field(default_factory=list, description="Factors affecting competition")

    # Mechanism details if available
    mechanism: Optional[MechanismSummary] = Field(None, description="Mechanism details if available")


class CompetitionSnapshotResponse(BaseModel):
    """Response for competition snapshot."""

    id: UUID = Field(..., description="Snapshot UUID")
    grant_id: Optional[UUID] = Field(None, description="Grant UUID")
    mechanism_id: Optional[UUID] = Field(None, description="Mechanism UUID")
    snapshot_date: datetime = Field(..., description="Snapshot date")
    estimated_applicants: Optional[int] = Field(None, description="Estimated applicants")
    similar_grants_count: Optional[int] = Field(None, description="Similar grants count")
    competition_score: Optional[float] = Field(None, description="Competition score")
    factors: Optional[dict[str, Any]] = Field(None, description="Competition factors")
    created_at: datetime = Field(..., description="Creation timestamp")
