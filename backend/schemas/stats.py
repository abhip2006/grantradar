"""
Statistics schemas for dashboard data.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class UpcomingDeadline(BaseModel):
    """Schema for upcoming deadline info."""

    grant_id: UUID = Field(..., description="Grant ID")
    match_id: UUID = Field(..., description="Match ID")
    grant_title: str = Field(..., description="Grant title")
    deadline: datetime = Field(..., description="Application deadline")
    match_score: float = Field(..., description="Match score")
    days_remaining: int = Field(..., description="Days until deadline")


class RecentMatch(BaseModel):
    """Schema for recent match info."""

    match_id: UUID = Field(..., description="Match ID")
    grant_id: UUID = Field(..., description="Grant ID")
    grant_title: str = Field(..., description="Grant title")
    match_score: float = Field(..., description="Match score")
    created_at: datetime = Field(..., description="Match creation time")
    grant_agency: Optional[str] = Field(None, description="Funding agency")


class MatchScoreDistribution(BaseModel):
    """Schema for match score distribution."""

    excellent: int = Field(..., description="Matches with score >= 0.8")
    good: int = Field(..., description="Matches with score 0.6-0.8")
    moderate: int = Field(..., description="Matches with score 0.4-0.6")
    low: int = Field(..., description="Matches with score < 0.4")


class DashboardStats(BaseModel):
    """Schema for dashboard statistics response."""

    # Counts
    total_matches: int = Field(..., description="Total number of matches")
    saved_grants: int = Field(..., description="Number of saved grants")
    dismissed_grants: int = Field(..., description="Number of dismissed grants")
    new_matches_today: int = Field(..., description="New matches in last 24 hours")
    new_matches_week: int = Field(..., description="New matches in last 7 days")

    # Score distribution
    score_distribution: MatchScoreDistribution = Field(..., description="Distribution of match scores")

    # Average score
    average_match_score: Optional[float] = Field(None, description="Average match score")

    # Upcoming deadlines
    upcoming_deadlines: list[UpcomingDeadline] = Field(
        default_factory=list, description="Grants with upcoming deadlines"
    )

    # Recent matches
    recent_matches: list[RecentMatch] = Field(default_factory=list, description="Most recent matches")

    # Profile status
    profile_complete: bool = Field(..., description="Whether profile is complete")
    profile_has_embedding: bool = Field(..., description="Whether profile has been embedded")
