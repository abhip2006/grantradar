"""
Analytics schemas for tracking application success rates and funding trends.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SuccessRateByCategory(BaseModel):
    """Success rate for a specific category."""

    category: str = Field(..., description="Grant category name")
    total: int = Field(..., description="Total applications in this category")
    submitted: int = Field(..., description="Applications submitted")
    awarded: int = Field(..., description="Applications awarded")
    rejected: int = Field(..., description="Applications rejected")
    success_rate: float = Field(
        ...,
        description="Win rate as percentage (0-100)",
        ge=0,
        le=100
    )


class SuccessRateByFunder(BaseModel):
    """Success rate for a specific funder/agency."""

    funder: str = Field(..., description="Funder/agency name")
    total: int = Field(..., description="Total applications")
    submitted: int = Field(..., description="Applications submitted")
    awarded: int = Field(..., description="Applications awarded")
    rejected: int = Field(..., description="Applications rejected")
    success_rate: float = Field(
        ...,
        description="Win rate as percentage (0-100)",
        ge=0,
        le=100
    )


class SuccessRateByStage(BaseModel):
    """Count of applications at each stage."""

    stage: str = Field(..., description="Pipeline stage name")
    count: int = Field(..., description="Number of applications at this stage")


class SuccessRatesResponse(BaseModel):
    """Success rates response with breakdowns by stage, category, and funder."""

    total_applications: int = Field(..., description="Total tracked applications")
    overall_success_rate: float = Field(
        ...,
        description="Overall win rate as percentage (0-100)",
        ge=0,
        le=100
    )
    by_stage: list[SuccessRateByStage] = Field(
        default_factory=list,
        description="Application counts by stage"
    )
    by_category: list[SuccessRateByCategory] = Field(
        default_factory=list,
        description="Success rates by grant category"
    )
    by_funder: list[SuccessRateByFunder] = Field(
        default_factory=list,
        description="Success rates by funder/agency"
    )


class FundingDataPoint(BaseModel):
    """Single data point for funding trends."""

    period: str = Field(..., description="Time period (e.g., '2024-01' for monthly)")
    applied_amount: float = Field(
        ...,
        description="Total amount of grants applied for"
    )
    awarded_amount: float = Field(
        ...,
        description="Total amount of grants awarded"
    )
    applied_count: int = Field(..., description="Number of applications submitted")
    awarded_count: int = Field(..., description="Number of grants awarded")


class FundingTrendsResponse(BaseModel):
    """Funding trends over time."""

    data_points: list[FundingDataPoint] = Field(
        default_factory=list,
        description="Funding data points over time"
    )
    total_applied_amount: float = Field(
        ...,
        description="Total amount applied for across all time"
    )
    total_awarded_amount: float = Field(
        ...,
        description="Total amount awarded across all time"
    )
    total_applied_count: int = Field(
        ...,
        description="Total applications submitted"
    )
    total_awarded_count: int = Field(
        ...,
        description="Total grants awarded"
    )
    period_type: str = Field(
        default="monthly",
        description="Type of period grouping (monthly, quarterly, yearly)"
    )


class PipelineStageMetric(BaseModel):
    """Metric for a single pipeline stage in the funnel."""

    stage: str = Field(..., description="Stage name")
    count: int = Field(..., description="Number of applications at this stage")
    conversion_rate: Optional[float] = Field(
        None,
        description="Conversion rate from previous stage (0-100)",
        ge=0,
        le=100
    )
    avg_days_in_stage: Optional[float] = Field(
        None,
        description="Average days applications spend in this stage"
    )


class PipelineMetricsResponse(BaseModel):
    """Pipeline conversion funnel metrics."""

    stages: list[PipelineStageMetric] = Field(
        default_factory=list,
        description="Metrics for each pipeline stage"
    )
    total_in_pipeline: int = Field(
        ...,
        description="Total applications in pipeline"
    )
    overall_conversion_rate: float = Field(
        ...,
        description="Overall conversion from researching to awarded (0-100)",
        ge=0,
        le=100
    )
    avg_time_to_award: Optional[float] = Field(
        None,
        description="Average days from researching to awarded"
    )


class CategoryBreakdownItem(BaseModel):
    """Breakdown for a single category."""

    category: str = Field(..., description="Category name")
    total: int = Field(..., description="Total applications")
    researching: int = Field(default=0, description="In researching stage")
    writing: int = Field(default=0, description="In writing stage")
    submitted: int = Field(default=0, description="Submitted")
    awarded: int = Field(default=0, description="Awarded")
    rejected: int = Field(default=0, description="Rejected")
    success_rate: float = Field(
        ...,
        description="Win rate (0-100)",
        ge=0,
        le=100
    )
    avg_funding_amount: Optional[float] = Field(
        None,
        description="Average funding amount for this category"
    )


class CategoryBreakdownResponse(BaseModel):
    """Success rates broken down by grant category/focus area."""

    categories: list[CategoryBreakdownItem] = Field(
        default_factory=list,
        description="Breakdown by category"
    )
    total_categories: int = Field(
        ...,
        description="Total unique categories"
    )


class AnalyticsSummaryResponse(BaseModel):
    """Dashboard summary statistics for analytics."""

    total_applications: int = Field(..., description="Total tracked applications")
    total_in_pipeline: int = Field(..., description="Applications currently in pipeline")
    total_submitted: int = Field(..., description="Total applications submitted")
    total_awarded: int = Field(..., description="Total grants awarded")
    total_rejected: int = Field(..., description="Total applications rejected")
    overall_success_rate: float = Field(
        ...,
        description="Overall win rate as percentage (0-100)",
        ge=0,
        le=100
    )
    total_funding_applied: float = Field(
        ...,
        description="Total funding amount applied for"
    )
    total_funding_awarded: float = Field(
        ...,
        description="Total funding amount awarded"
    )
    avg_funding_per_award: Optional[float] = Field(
        None,
        description="Average funding amount per awarded grant"
    )
    pipeline_conversion_rate: float = Field(
        ...,
        description="Overall pipeline conversion rate (0-100)",
        ge=0,
        le=100
    )
    top_funder: Optional[str] = Field(
        None,
        description="Most successful funder by win rate"
    )
    top_category: Optional[str] = Field(
        None,
        description="Most successful category by win rate"
    )


# =============================================================================
# Time to Award Schemas
# =============================================================================


class StageTimingData(BaseModel):
    """Timing metrics for a specific pipeline stage."""

    stage: str = Field(..., description="Pipeline stage name")
    avg_days: float = Field(..., description="Average days spent in this stage")
    median_days: float = Field(..., description="Median days spent in this stage")
    min_days: int = Field(..., description="Minimum days spent in this stage")
    max_days: int = Field(..., description="Maximum days spent in this stage")
    count: int = Field(..., description="Number of applications that passed through")


class TimeToAwardResponse(BaseModel):
    """Metrics on time from submission to award."""

    overall_avg_days: float = Field(
        ...,
        description="Overall average days from creation to award"
    )
    overall_median_days: float = Field(
        ...,
        description="Overall median days from creation to award"
    )
    by_stage: list[StageTimingData] = Field(
        default_factory=list,
        description="Timing breakdown by pipeline stage"
    )
    by_category: dict[str, float] = Field(
        default_factory=dict,
        description="Average days to award by category"
    )
    by_funder: dict[str, float] = Field(
        default_factory=dict,
        description="Average days to award by funder"
    )
    trend: list[dict] = Field(
        default_factory=list,
        description="Monthly trend of time to award"
    )


# =============================================================================
# Funder Leaderboard Schemas
# =============================================================================


class FunderRanking(BaseModel):
    """Ranking entry for a specific funder."""

    rank: int = Field(..., description="Leaderboard position")
    funder: str = Field(..., description="Funder/agency name")
    success_rate: float = Field(
        ...,
        description="Win rate as percentage (0-100)",
        ge=0,
        le=100
    )
    total_awarded: float = Field(..., description="Total funding amount awarded")
    total_applications: int = Field(..., description="Total applications submitted")
    awarded_count: int = Field(..., description="Number of grants awarded")
    avg_award_amount: float = Field(..., description="Average award amount")
    trend: str = Field(
        ...,
        description="Performance trend: 'up', 'down', or 'stable'"
    )


class FunderLeaderboardResponse(BaseModel):
    """Top funders ranked by success rate and total awarded."""

    rankings: list[FunderRanking] = Field(
        default_factory=list,
        description="Funder rankings"
    )
    total_funders: int = Field(..., description="Total unique funders in dataset")
    period_months: int = Field(..., description="Time period analyzed in months")


# =============================================================================
# Match Quality Schemas
# =============================================================================


class ScoreRangeBucket(BaseModel):
    """Match quality metrics for a specific score range."""

    range_start: float = Field(..., description="Score range start (0.0-1.0)")
    range_end: float = Field(..., description="Score range end (0.0-1.0)")
    count: int = Field(..., description="Number of matches in this range")
    saved_rate: float = Field(
        ...,
        description="Percentage of matches saved",
        ge=0,
        le=100
    )
    applied_rate: float = Field(
        ...,
        description="Percentage of matches that led to applications",
        ge=0,
        le=100
    )
    awarded_rate: float = Field(
        ...,
        description="Percentage of matches that led to awards",
        ge=0,
        le=100
    )


class MatchQualityResponse(BaseModel):
    """Match algorithm quality metrics."""

    total_matches: int = Field(..., description="Total matches analyzed")
    avg_score: float = Field(..., description="Average match score (0.0-1.0)")
    score_distribution: list[ScoreRangeBucket] = Field(
        default_factory=list,
        description="Score distribution histogram buckets"
    )
    action_breakdown: dict[str, int] = Field(
        default_factory=dict,
        description="Count by user action (saved, dismissed, applied, none)"
    )
    conversion_by_score: list[dict] = Field(
        default_factory=list,
        description="Conversion rates by score range"
    )


# =============================================================================
# Deadline Heatmap Schemas
# =============================================================================


class DayData(BaseModel):
    """Deadline data for a single day."""

    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    count: int = Field(..., description="Number of deadlines on this day")
    applications: int = Field(
        ...,
        description="Number of active applications for these deadlines"
    )
    intensity: str = Field(
        ...,
        description="Visual intensity: 'low', 'medium', 'high', 'critical'"
    )


class DeadlineHeatmapResponse(BaseModel):
    """Deadline density for calendar heatmap visualization."""

    days: list[DayData] = Field(
        default_factory=list,
        description="Deadline data for each day"
    )
    max_count: int = Field(..., description="Maximum deadlines on any single day")
    total_deadlines: int = Field(..., description="Total deadlines in the period")


# =============================================================================
# Activity Timeline Schemas
# =============================================================================


class DailyActivity(BaseModel):
    """Activity metrics for a single day."""

    date: str = Field(..., description="Date in ISO format (YYYY-MM-DD)")
    applications_created: int = Field(
        ...,
        description="Number of applications created on this day"
    )
    stage_changes: int = Field(
        ...,
        description="Number of stage changes on this day"
    )
    matches_saved: int = Field(
        ...,
        description="Number of matches saved on this day"
    )
    total_actions: int = Field(
        ...,
        description="Total actions performed on this day"
    )


class ActivityTimelineResponse(BaseModel):
    """User activity over time for sparklines/charts."""

    daily: list[DailyActivity] = Field(
        default_factory=list,
        description="Daily activity metrics"
    )
    totals: dict[str, int] = Field(
        default_factory=dict,
        description="Total counts for each activity type"
    )
    avg_daily: dict[str, float] = Field(
        default_factory=dict,
        description="Average daily counts for each activity type"
    )
