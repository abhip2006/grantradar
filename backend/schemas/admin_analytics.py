"""
Admin Analytics Schemas
Pydantic models for admin platform-wide analytics responses.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# =============================================================================
# Platform Overview Models
# =============================================================================


class PlatformOverviewResponse(BaseModel):
    """Platform-wide metrics for admins."""

    total_users: int = Field(..., description="Total registered users")
    active_users_24h: int = Field(..., description="Users active in last 24 hours")
    active_users_7d: int = Field(..., description="Users active in last 7 days")
    total_grants: int = Field(..., description="Total grants in database")
    total_applications: int = Field(..., description="Total grant applications")
    ai_requests_today: int = Field(..., description="AI feature requests today")


# =============================================================================
# User Analytics Models
# =============================================================================


class DailySignup(BaseModel):
    """Daily user signup count."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of signups on this date")


class DailyActiveUsers(BaseModel):
    """Daily active user count."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of active users on this date")


class TopUserByActivity(BaseModel):
    """User ranked by activity level."""

    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    name: Optional[str] = Field(None, description="User name")
    activity_score: int = Field(..., description="Activity score (actions count)")
    last_active: Optional[datetime] = Field(None, description="Last activity timestamp")


class UserAnalyticsResponse(BaseModel):
    """User growth and engagement metrics."""

    signups_by_day: list[DailySignup] = Field(default_factory=list, description="Daily signup counts")
    active_users_by_day: list[DailyActiveUsers] = Field(default_factory=list, description="Daily active user counts")
    retention_rate: float = Field(..., description="7-day retention rate as percentage (0-100)", ge=0, le=100)
    top_users_by_activity: list[TopUserByActivity] = Field(default_factory=list, description="Top 10 users by activity")


# =============================================================================
# AI Usage Models
# =============================================================================


class DailyChatSessions(BaseModel):
    """Daily chat session count."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of chat sessions on this date")


class AIUsageResponse(BaseModel):
    """AI feature usage metrics."""

    chat_sessions_by_day: list[DailyChatSessions] = Field(default_factory=list, description="Daily chat session counts")
    insights_generated: int = Field(..., description="Total grant insights generated")
    writing_analyses: int = Field(..., description="Total writing analyses performed")
    research_sessions: int = Field(..., description="Total deep research sessions")
    tokens_used_estimate: int = Field(..., description="Estimated total tokens used (approximate)")


# =============================================================================
# Grant Analytics Models
# =============================================================================


class GrantsBySource(BaseModel):
    """Grant count by source."""

    source: str = Field(..., description="Grant source (e.g., 'nih', 'nsf', 'grants_gov')")
    count: int = Field(..., description="Number of grants from this source")


class GrantsByAgency(BaseModel):
    """Grant count by funding agency."""

    agency: str = Field(..., description="Funding agency name")
    count: int = Field(..., description="Number of grants from this agency")


class ApplicationsByStatus(BaseModel):
    """Application count by status."""

    status: str = Field(..., description="Application stage/status")
    count: int = Field(..., description="Number of applications in this status")


class MatchScoreBucket(BaseModel):
    """Match score distribution bucket."""

    range_label: str = Field(..., description="Score range label (e.g., '80-100%')")
    min_score: float = Field(..., description="Minimum score in range")
    max_score: float = Field(..., description="Maximum score in range")
    count: int = Field(..., description="Number of matches in this range")


class GrantAnalyticsResponse(BaseModel):
    """Grant discovery and application metrics."""

    grants_by_source: list[GrantsBySource] = Field(default_factory=list, description="Grant counts by source")
    grants_by_agency: list[GrantsByAgency] = Field(default_factory=list, description="Grant counts by top agencies")
    applications_by_status: list[ApplicationsByStatus] = Field(
        default_factory=list, description="Application counts by status"
    )
    match_score_distribution: list[MatchScoreBucket] = Field(
        default_factory=list, description="Distribution of match scores"
    )


# =============================================================================
# Team Analytics Models
# =============================================================================


class DailyComments(BaseModel):
    """Daily comment count."""

    date: str = Field(..., description="Date in YYYY-MM-DD format")
    count: int = Field(..., description="Number of comments on this date")


class TeamAnalyticsResponse(BaseModel):
    """Team collaboration metrics."""

    total_teams: int = Field(..., description="Total number of lab teams/groups")
    avg_team_size: float = Field(..., description="Average team size")
    active_collaborations: int = Field(..., description="Active collaborations (teams with recent activity)")
    comments_per_day: list[DailyComments] = Field(default_factory=list, description="Daily team comment counts")


# =============================================================================
# Date Range Filter
# =============================================================================


class DateRangeParams(BaseModel):
    """Date range parameters for filtering analytics."""

    start_date: Optional[datetime] = Field(None, description="Start date for filtering (inclusive)")
    end_date: Optional[datetime] = Field(None, description="End date for filtering (inclusive)")
