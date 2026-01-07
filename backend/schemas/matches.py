"""
Match schemas for grant-researcher match results.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class MatchResponse(BaseModel):
    """Schema for match list item response."""

    id: UUID = Field(..., description="Match ID")
    grant_id: UUID = Field(..., description="Grant ID")
    match_score: float = Field(..., ge=0, le=1, description="Match score (0-1)")
    predicted_success: Optional[float] = Field(None, description="Predicted success probability")
    user_action: Optional[str] = Field(None, description="User action")
    created_at: datetime = Field(..., description="Match creation timestamp")

    # Embedded grant info
    grant_title: str = Field(..., description="Grant title")
    grant_agency: Optional[str] = Field(None, description="Funding agency")
    grant_deadline: Optional[datetime] = Field(None, description="Application deadline")
    grant_amount_min: Optional[int] = Field(None, description="Minimum funding")
    grant_amount_max: Optional[int] = Field(None, description="Maximum funding")

    class Config:
        from_attributes = True


class MatchDetail(BaseModel):
    """Schema for detailed match response with reasoning."""

    id: UUID = Field(..., description="Match ID")
    grant_id: UUID = Field(..., description="Grant ID")
    user_id: UUID = Field(..., description="User ID")
    match_score: float = Field(..., ge=0, le=1, description="Match score")
    reasoning: Optional[str] = Field(None, description="AI-generated match reasoning")
    predicted_success: Optional[float] = Field(None, description="Success probability")
    user_action: Optional[str] = Field(None, description="User action")
    user_feedback: Optional[dict[str, Any]] = Field(None, description="User feedback")
    created_at: datetime = Field(..., description="Match timestamp")

    # Full grant details
    grant_title: str = Field(..., description="Grant title")
    grant_description: Optional[str] = Field(None, description="Grant description")
    grant_agency: Optional[str] = Field(None, description="Funding agency")
    grant_deadline: Optional[datetime] = Field(None, description="Deadline")
    grant_amount_min: Optional[int] = Field(None, description="Min funding")
    grant_amount_max: Optional[int] = Field(None, description="Max funding")
    grant_url: Optional[str] = Field(None, description="Grant URL")
    grant_eligibility: Optional[dict[str, Any]] = Field(None, description="Eligibility")
    grant_categories: Optional[list[str]] = Field(None, description="Categories")

    class Config:
        from_attributes = True


class MatchFilter(BaseModel):
    """Schema for match list filtering."""

    min_score: Optional[float] = Field(None, ge=0, le=1, description="Minimum match score")
    max_score: Optional[float] = Field(None, ge=0, le=1, description="Maximum match score")
    user_action: Optional[str] = Field(None, description="Filter by user action")
    has_deadline: Optional[bool] = Field(None, description="Only grants with deadlines")


class MatchAction(BaseModel):
    """Schema for user action on a match."""

    action: str = Field(
        ...,
        description="Action type",
        pattern="^(saved|dismissed|applied|interested)$"
    )


class MatchFeedback(BaseModel):
    """Schema for user feedback on a match."""

    relevance_rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Relevance rating (1-5)"
    )
    would_apply: bool = Field(..., description="Would user apply for this grant")
    feedback_text: Optional[str] = Field(
        None,
        max_length=1000,
        description="Additional feedback text"
    )
    match_quality_issues: Optional[list[str]] = Field(
        None,
        description="List of quality issues (e.g., 'wrong_field', 'ineligible', 'too_small')"
    )


class MatchList(BaseModel):
    """Schema for paginated match list response."""

    matches: list[MatchResponse] = Field(..., description="List of matches")
    total: int = Field(..., description="Total number of matches")
    page: int = Field(..., description="Current page")
    page_size: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more pages exist")
