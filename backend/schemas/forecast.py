"""
Forecast schemas for predicting upcoming grant opportunities.
"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ForecastGrant(BaseModel):
    """Schema for a predicted grant opportunity."""

    id: Optional[UUID] = Field(None, description="Grant ID if based on historical grant")
    funder_name: str = Field(..., description="Funding agency/organization name")
    predicted_open_date: date = Field(..., description="Predicted opening date")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    historical_amount_min: Optional[int] = Field(None, description="Historical minimum funding")
    historical_amount_max: Optional[int] = Field(None, description="Historical maximum funding")
    focus_areas: list[str] = Field(default_factory=list, description="Research focus areas")
    title: Optional[str] = Field(None, description="Grant title or predicted title")
    historical_deadline_month: Optional[int] = Field(
        None, ge=1, le=12, description="Historical deadline month"
    )
    recurrence_pattern: str = Field(
        default="annual", description="Pattern: annual, biannual, quarterly"
    )
    last_seen_date: Optional[date] = Field(None, description="Last time this grant was seen")
    source: Optional[str] = Field(None, description="Data source (nih, nsf, grants_gov)")
    match_score: Optional[float] = Field(
        None, ge=0, le=1, description="Match score with user profile"
    )
    reasoning: Optional[str] = Field(None, description="Why this grant is recommended")

    class Config:
        from_attributes = True


class SeasonalTrend(BaseModel):
    """Schema for seasonal grant availability trends."""

    month: int = Field(..., ge=1, le=12, description="Month number (1-12)")
    month_name: str = Field(..., description="Month name (January, February, etc.)")
    grant_count: int = Field(..., ge=0, description="Number of grants typically available")
    avg_amount: Optional[float] = Field(None, description="Average funding amount")
    top_categories: list[str] = Field(
        default_factory=list, max_length=5, description="Top grant categories"
    )
    top_funders: list[str] = Field(
        default_factory=list, max_length=5, description="Top funding agencies"
    )

    class Config:
        from_attributes = True


class ForecastUpcomingResponse(BaseModel):
    """Response schema for upcoming grant forecast."""

    forecasts: list[ForecastGrant] = Field(..., description="List of predicted grants")
    total: int = Field(..., description="Total number of forecasts")
    generated_at: datetime = Field(..., description="When this forecast was generated")
    lookahead_months: int = Field(..., description="Number of months looked ahead")


class SeasonalTrendResponse(BaseModel):
    """Response schema for seasonal trends."""

    trends: list[SeasonalTrend] = Field(..., description="Monthly trends")
    year_total: int = Field(..., description="Total grants for the year")
    peak_months: list[int] = Field(
        default_factory=list, description="Months with highest activity"
    )
    generated_at: datetime = Field(..., description="When this analysis was generated")


class RecommendationGrant(BaseModel):
    """Schema for AI-powered recommendation."""

    grant: ForecastGrant = Field(..., description="Forecast grant details")
    match_score: float = Field(..., ge=0, le=1, description="Match score with user profile")
    match_reasons: list[str] = Field(
        default_factory=list, description="Reasons for the recommendation"
    )
    profile_overlap: list[str] = Field(
        default_factory=list, description="Overlapping profile areas"
    )


class RecommendationsResponse(BaseModel):
    """Response schema for AI recommendations."""

    recommendations: list[RecommendationGrant] = Field(
        ..., description="Personalized recommendations"
    )
    total: int = Field(..., description="Total recommendations")
    profile_complete: bool = Field(..., description="Whether user profile is complete")
    generated_at: datetime = Field(..., description="When recommendations were generated")
