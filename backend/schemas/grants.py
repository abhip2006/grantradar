"""
Grant schemas for listing, filtering, and detailed responses.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class GrantResponse(BaseModel):
    """Schema for grant list item response."""

    id: UUID = Field(..., description="Grant ID")
    source: str = Field(..., description="Data source (nih, nsf, grants_gov)")
    external_id: str = Field(..., description="External identifier")
    title: str = Field(..., description="Grant title")
    agency: Optional[str] = Field(None, description="Funding agency")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    posted_at: Optional[datetime] = Field(None, description="Posted date")
    url: Optional[str] = Field(None, description="Grant URL")
    categories: Optional[list[str]] = Field(None, description="Grant categories")

    class Config:
        from_attributes = True


class GrantDetail(BaseModel):
    """Schema for detailed grant response with match info."""

    id: UUID = Field(..., description="Grant ID")
    source: str = Field(..., description="Data source")
    external_id: str = Field(..., description="External identifier")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(None, description="Full description")
    agency: Optional[str] = Field(None, description="Funding agency")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    posted_at: Optional[datetime] = Field(None, description="Posted date")
    url: Optional[str] = Field(None, description="Grant URL")
    eligibility: Optional[dict[str, Any]] = Field(None, description="Eligibility criteria")
    categories: Optional[list[str]] = Field(None, description="Grant categories")
    created_at: datetime = Field(..., description="Record creation timestamp")

    # Match info (if user is authenticated)
    match_score: Optional[float] = Field(None, description="Match score for current user")
    match_reasoning: Optional[str] = Field(None, description="Match reasoning")
    user_action: Optional[str] = Field(None, description="User action on this grant")

    class Config:
        from_attributes = True


class GrantFilter(BaseModel):
    """Schema for grant list filtering."""

    source: Optional[str] = Field(None, description="Filter by source")
    category: Optional[str] = Field(None, description="Filter by category")
    min_amount: Optional[int] = Field(None, ge=0, description="Minimum funding amount")
    max_amount: Optional[int] = Field(None, ge=0, description="Maximum funding amount")
    deadline_after: Optional[datetime] = Field(None, description="Deadline after date")
    deadline_before: Optional[datetime] = Field(None, description="Deadline before date")


class GrantSearch(BaseModel):
    """Schema for grant search query."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results")


class GrantList(BaseModel):
    """Schema for paginated grant list response."""

    grants: list[GrantResponse] = Field(..., description="List of grants")
    total: int = Field(..., description="Total number of grants")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")
