"""
Funder Insights schemas for analytics and historical data.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class FunderSummary(BaseModel):
    """Summary statistics for a funder in list view."""

    funder_name: str = Field(..., description="Name of the funder/agency")
    total_grants: int = Field(..., description="Total number of grants from this funder")
    avg_amount_min: Optional[float] = Field(None, description="Average minimum funding amount")
    avg_amount_max: Optional[float] = Field(None, description="Average maximum funding amount")
    focus_areas: list[str] = Field(default_factory=list, description="Common focus areas/categories")
    active_grants: int = Field(default=0, description="Number of currently active grants")

    class Config:
        from_attributes = True


class FunderListResponse(BaseModel):
    """Response for listing all funders."""

    funders: list[FunderSummary] = Field(..., description="List of funders with summary stats")
    total: int = Field(..., description="Total number of funders")


class DeadlineMonth(BaseModel):
    """Grant deadline seasonality data."""

    month: int = Field(..., ge=1, le=12, description="Month number (1-12)")
    month_name: str = Field(..., description="Month name")
    grant_count: int = Field(..., description="Number of grants with deadlines in this month")


class UserFunderHistory(BaseModel):
    """User's history with a specific funder."""

    total_applications: int = Field(default=0, description="Total applications to this funder")
    awarded_count: int = Field(default=0, description="Number of awards from this funder")
    rejected_count: int = Field(default=0, description="Number of rejections from this funder")
    pending_count: int = Field(default=0, description="Number of pending applications")
    success_rate: Optional[float] = Field(None, description="Success rate (awarded / total decided)")
    applications: list["UserApplication"] = Field(default_factory=list, description="Recent applications")


class UserApplication(BaseModel):
    """Summary of a user's application to a grant."""

    grant_id: UUID = Field(..., description="Grant ID")
    grant_title: str = Field(..., description="Grant title")
    stage: str = Field(..., description="Application stage")
    applied_at: Optional[datetime] = Field(None, description="When applied")


class FunderInsightsResponse(BaseModel):
    """Detailed analytics for a specific funder."""

    funder_name: str = Field(..., description="Name of the funder/agency")
    total_grants: int = Field(..., description="Total grants from this funder")
    active_grants: int = Field(default=0, description="Currently active grants")

    # Funding statistics
    avg_amount_min: Optional[float] = Field(None, description="Average minimum funding")
    avg_amount_max: Optional[float] = Field(None, description="Average maximum funding")
    min_amount: Optional[int] = Field(None, description="Lowest funding amount offered")
    max_amount: Optional[int] = Field(None, description="Highest funding amount offered")

    # Focus areas
    focus_areas: list[str] = Field(default_factory=list, description="Most common focus areas")
    focus_area_counts: dict[str, int] = Field(default_factory=dict, description="Count per focus area")

    # Seasonality
    deadline_months: list[DeadlineMonth] = Field(
        default_factory=list, description="Distribution of deadlines by month"
    )
    typical_deadline_months: list[str] = Field(
        default_factory=list, description="Most common deadline months"
    )

    # User-specific data (if authenticated)
    user_history: Optional[UserFunderHistory] = Field(
        None, description="User's history with this funder"
    )

    class Config:
        from_attributes = True


class FunderGrantResponse(BaseModel):
    """Grant summary in funder grants list."""

    id: UUID = Field(..., description="Grant ID")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(None, description="Grant description (truncated)")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    posted_at: Optional[datetime] = Field(None, description="When posted")
    categories: Optional[list[str]] = Field(None, description="Grant categories")
    url: Optional[str] = Field(None, description="Grant URL")
    is_active: bool = Field(default=True, description="Whether deadline hasn't passed")

    class Config:
        from_attributes = True


class FunderGrantsResponse(BaseModel):
    """Response for listing grants from a specific funder."""

    funder_name: str = Field(..., description="Name of the funder")
    grants: list[FunderGrantResponse] = Field(..., description="Grants from this funder")
    total: int = Field(..., description="Total number of grants")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")


# Update forward reference
UserFunderHistory.model_rebuild()
