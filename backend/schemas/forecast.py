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
    fiscal_quarter: Optional[int] = Field(
        None, ge=1, le=4, description="Federal fiscal quarter (1-4)"
    )
    is_federal_funder: bool = Field(
        default=False, description="Whether this is a federal funding agency"
    )

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


# =============================================================================
# Deadline History Schemas
# =============================================================================


class DeadlineHistoryRecord(BaseModel):
    """Schema for a historical deadline record."""

    id: UUID = Field(..., description="Record ID")
    grant_id: Optional[UUID] = Field(None, description="Associated grant ID")
    funder_name: str = Field(..., description="Funding agency name")
    grant_title: Optional[str] = Field(None, description="Grant title")
    deadline_date: datetime = Field(..., description="Historical deadline date")
    open_date: Optional[datetime] = Field(None, description="Grant open date")
    fiscal_year: Optional[int] = Field(None, description="Federal fiscal year")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    categories: list[str] = Field(default_factory=list, description="Grant categories")
    source: Optional[str] = Field(None, description="Data source")
    created_at: datetime = Field(..., description="When record was created")

    class Config:
        from_attributes = True


class DeadlineHistoryStatsResponse(BaseModel):
    """Response schema for deadline history statistics."""

    total_records: int = Field(..., description="Total historical records")
    unique_funders: int = Field(..., description="Number of unique funders")
    earliest_deadline: Optional[datetime] = Field(None, description="Earliest deadline date")
    latest_deadline: Optional[datetime] = Field(None, description="Latest deadline date")
    top_funders: list[dict] = Field(
        default_factory=list, description="Top funders by record count"
    )
    generated_at: datetime = Field(..., description="When stats were generated")


class DeadlineHistoryResponse(BaseModel):
    """Response schema for deadline history list."""

    records: list[DeadlineHistoryRecord] = Field(..., description="Historical records")
    total: int = Field(..., description="Total matching records")
    funder_name: Optional[str] = Field(None, description="Funder filter applied")


class FunderPrediction(BaseModel):
    """Schema for funder-specific deadline prediction."""

    funder_name: str = Field(..., description="Funding agency name")
    predicted_deadline: date = Field(..., description="Predicted next deadline")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    typical_day_of_month: Optional[int] = Field(
        None, ge=1, le=31, description="Typical day of month for deadlines"
    )
    typical_months: list[int] = Field(
        default_factory=list, description="Months when deadlines typically occur"
    )
    based_on_records: int = Field(..., description="Number of records used for prediction")
    avg_cycle_days: Optional[float] = Field(None, description="Average days between deadlines")
    last_known_deadline: Optional[datetime] = Field(None, description="Most recent known deadline")
    grant_titles: list[str] = Field(
        default_factory=list, description="Sample grant titles"
    )


class FunderPredictionResponse(BaseModel):
    """Response schema for funder prediction."""

    prediction: FunderPrediction = Field(..., description="Prediction details")
    generated_at: datetime = Field(..., description="When prediction was generated")


# =============================================================================
# ML Forecast Schemas
# =============================================================================


class MLPrediction(BaseModel):
    """Schema for ML-based deadline prediction."""

    funder_name: str = Field(..., description="Funding agency name")
    predicted_date: date = Field(..., description="ML-predicted deadline date")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score")
    method: str = Field(..., description="Prediction method: 'ml' or 'rule_based'")
    uncertainty_days: int = Field(..., ge=0, description="Uncertainty in days (+/-)")
    lower_bound: Optional[date] = Field(None, description="Lower bound of prediction range")
    upper_bound: Optional[date] = Field(None, description="Upper bound of prediction range")


class MLPredictionResponse(BaseModel):
    """Response schema for ML prediction."""

    prediction: MLPrediction = Field(..., description="ML prediction details")
    model_trained: bool = Field(..., description="Whether an ML model was used")
    data_points: Optional[int] = Field(None, description="Training data points used")
    generated_at: datetime = Field(..., description="When prediction was generated")


class FiscalCalendarInfo(BaseModel):
    """Schema for fiscal calendar information."""

    current_fiscal_year: int = Field(..., description="Current federal fiscal year")
    current_fiscal_quarter: int = Field(..., ge=1, le=4, description="Current fiscal quarter")
    quarter_end_date: date = Field(..., description="Current quarter end date")
    days_until_quarter_end: int = Field(..., description="Days until quarter ends")
    is_year_end_period: bool = Field(..., description="Whether in fiscal year-end period")
    is_year_start_period: bool = Field(..., description="Whether in fiscal year-start period")


class FiscalCalendarResponse(BaseModel):
    """Response schema for fiscal calendar info."""

    fiscal_info: FiscalCalendarInfo = Field(..., description="Fiscal calendar details")
    for_date: date = Field(..., description="Date this info applies to")
    generated_at: datetime = Field(..., description="When info was generated")
