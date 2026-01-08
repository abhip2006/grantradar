"""
Forecast API Endpoints
Predict upcoming grant opportunities based on historical patterns.
"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query

from backend.api.deps import AsyncSessionDep, CurrentUser, OptionalUser
from backend.schemas.forecast import (
    DeadlineHistoryRecord,
    DeadlineHistoryResponse,
    DeadlineHistoryStatsResponse,
    FiscalCalendarInfo,
    FiscalCalendarResponse,
    ForecastGrant,
    ForecastUpcomingResponse,
    FunderPrediction,
    FunderPredictionResponse,
    MLPrediction,
    MLPredictionResponse,
    RecommendationGrant,
    RecommendationsResponse,
    SeasonalTrend,
    SeasonalTrendResponse,
)
from backend.services.deadline_history import (
    get_deadline_history_stats,
    get_funder_deadline_history,
    predict_next_deadline,
)
from backend.services.forecast import (
    get_recommendations,
    get_seasonal_trends,
    get_upcoming_forecasts,
)
from backend.services.ml_forecast import GrantDeadlinePredictor
from backend.utils.fiscal_calendar import FiscalCalendar, is_federal_funder


router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


@router.get(
    "/upcoming",
    response_model=ForecastUpcomingResponse,
    summary="Get upcoming grant forecasts",
    description="Predict grants likely to open soon based on historical patterns.",
)
async def get_upcoming(
    db: AsyncSessionDep,
    user: OptionalUser,
    lookahead_months: int = Query(
        default=6, ge=1, le=12, description="Months to look ahead"
    ),
    limit: int = Query(default=20, ge=1, le=50, description="Maximum results"),
) -> ForecastUpcomingResponse:
    """
    Get predicted upcoming grant opportunities.

    Analyzes historical grant cycles to predict when funders will release
    similar grants. Uses patterns like:
    - Annual recurring grants
    - Funder release schedules
    - Seasonal trends

    If authenticated, results are sorted by relevance to user profile.
    """
    user_id = user.id if user else None

    forecasts = await get_upcoming_forecasts(
        db=db,
        user_id=user_id,
        lookahead_months=lookahead_months,
        limit=limit,
    )

    forecast_grants = [
        ForecastGrant(
            id=f.grant_id,
            funder_name=f.funder_name,
            predicted_open_date=f.predicted_open_date,
            confidence=f.confidence,
            historical_amount_min=f.historical_amount_min,
            historical_amount_max=f.historical_amount_max,
            focus_areas=f.focus_areas,
            title=f.title,
            historical_deadline_month=f.historical_deadline_month,
            recurrence_pattern=f.recurrence_pattern,
            last_seen_date=f.last_seen_date,
            source=f.source,
            fiscal_quarter=f.fiscal_quarter,
            is_federal_funder=f.is_federal_funder,
        )
        for f in forecasts
    ]

    return ForecastUpcomingResponse(
        forecasts=forecast_grants,
        total=len(forecast_grants),
        generated_at=datetime.utcnow(),
        lookahead_months=lookahead_months,
    )


@router.get(
    "/seasonal",
    response_model=SeasonalTrendResponse,
    summary="Get seasonal grant trends",
    description="Show grant availability patterns by month/quarter.",
)
async def get_seasonal(
    db: AsyncSessionDep,
    user: OptionalUser,
) -> SeasonalTrendResponse:
    """
    Analyze grant availability by month.

    Returns aggregated data showing:
    - Number of grants typically available each month
    - Average funding amounts
    - Top categories and funders by month

    If authenticated, filters by user's focus areas.
    """
    # Get user focus areas if authenticated
    user_focus_areas = None
    if user:
        from sqlalchemy import select
        from backend.models import LabProfile

        profile_result = await db.execute(
            select(LabProfile.research_areas).where(LabProfile.user_id == user.id)
        )
        profile_row = profile_result.first()
        if profile_row and profile_row.research_areas:
            user_focus_areas = profile_row.research_areas

    trends = await get_seasonal_trends(
        db=db,
        user_focus_areas=user_focus_areas,
    )

    seasonal_trends = [
        SeasonalTrend(
            month=t.month,
            month_name=t.month_name,
            grant_count=t.grant_count,
            avg_amount=t.avg_amount,
            top_categories=t.top_categories,
            top_funders=t.top_funders,
        )
        for t in trends
    ]

    # Calculate year total and peak months
    year_total = sum(t.grant_count for t in trends)
    max_count = max(t.grant_count for t in trends) if trends else 0
    peak_months = [t.month for t in trends if t.grant_count == max_count and max_count > 0]

    return SeasonalTrendResponse(
        trends=seasonal_trends,
        year_total=year_total,
        peak_months=peak_months,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/recommendations",
    response_model=RecommendationsResponse,
    summary="Get personalized recommendations",
    description="AI-powered recommendations based on user profile match.",
)
async def get_recommendation_list(
    db: AsyncSessionDep,
    user: CurrentUser,
    limit: int = Query(default=10, ge=1, le=30, description="Maximum results"),
) -> RecommendationsResponse:
    """
    Get personalized grant recommendations.

    Uses the user's research profile to:
    - Match upcoming forecasts to research areas
    - Score relevance based on profile overlap
    - Provide reasoning for each recommendation

    Requires authentication and a completed profile for best results.
    """
    from sqlalchemy import select
    from backend.models import LabProfile

    # Check if user has profile
    profile_result = await db.execute(
        select(LabProfile).where(LabProfile.user_id == user.id)
    )
    profile = profile_result.scalar_one_or_none()
    profile_complete = profile is not None and bool(profile.research_areas)

    recommendations = await get_recommendations(
        db=db,
        user_id=user.id,
        limit=limit,
    )

    recommendation_grants = [
        RecommendationGrant(
            grant=ForecastGrant(
                id=r.forecast.grant_id,
                funder_name=r.forecast.funder_name,
                predicted_open_date=r.forecast.predicted_open_date,
                confidence=r.forecast.confidence,
                historical_amount_min=r.forecast.historical_amount_min,
                historical_amount_max=r.forecast.historical_amount_max,
                focus_areas=r.forecast.focus_areas,
                title=r.forecast.title,
                historical_deadline_month=r.forecast.historical_deadline_month,
                recurrence_pattern=r.forecast.recurrence_pattern,
                last_seen_date=r.forecast.last_seen_date,
                source=r.forecast.source,
                match_score=r.match_score,
            ),
            match_score=r.match_score,
            match_reasons=r.match_reasons,
            profile_overlap=r.profile_overlap,
        )
        for r in recommendations
    ]

    return RecommendationsResponse(
        recommendations=recommendation_grants,
        total=len(recommendation_grants),
        profile_complete=profile_complete,
        generated_at=datetime.utcnow(),
    )


# =============================================================================
# Deadline History Endpoints
# =============================================================================


@router.get(
    "/history/stats",
    response_model=DeadlineHistoryStatsResponse,
    summary="Get deadline history statistics",
    description="Get aggregate statistics about historical deadline data.",
)
async def get_history_stats(
    db: AsyncSessionDep,
) -> DeadlineHistoryStatsResponse:
    """
    Get statistics about the deadline history database.

    Returns counts, date ranges, and top funders from historical data.
    """
    stats = await get_deadline_history_stats(db)

    return DeadlineHistoryStatsResponse(
        total_records=stats.get("total_records", 0),
        unique_funders=stats.get("unique_funders", 0),
        earliest_deadline=stats.get("earliest_deadline"),
        latest_deadline=stats.get("latest_deadline"),
        top_funders=stats.get("top_funders", []),
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/history/{funder_name}",
    response_model=DeadlineHistoryResponse,
    summary="Get deadline history for a funder",
    description="Get historical deadline records for a specific funding agency.",
)
async def get_funder_history(
    db: AsyncSessionDep,
    funder_name: str = Path(..., description="Name of the funding agency"),
) -> DeadlineHistoryResponse:
    """
    Get historical deadline records for a specific funder.

    Returns all known historical deadlines for the specified funding agency.
    """
    records = await get_funder_deadline_history(db, funder_name)

    history_records = [
        DeadlineHistoryRecord(
            id=r.id,
            grant_id=r.grant_id,
            funder_name=r.funder_name,
            grant_title=r.grant_title,
            deadline_date=r.deadline_date,
            open_date=r.open_date,
            fiscal_year=r.fiscal_year,
            amount_min=r.amount_min,
            amount_max=r.amount_max,
            categories=r.categories or [],
            source=r.source,
            created_at=r.created_at,
        )
        for r in records
    ]

    return DeadlineHistoryResponse(
        records=history_records,
        total=len(history_records),
        funder_name=funder_name,
    )


@router.get(
    "/predict/{funder_name}",
    response_model=FunderPredictionResponse,
    summary="Predict next deadline for a funder",
    description="Get day-level prediction for a funder's next deadline.",
)
async def get_funder_prediction(
    db: AsyncSessionDep,
    funder_name: str = Path(..., description="Name of the funding agency"),
) -> FunderPredictionResponse:
    """
    Predict the next deadline for a specific funding agency.

    Uses historical patterns to predict:
    - The specific date of the next deadline
    - Typical day of month for deadlines
    - Confidence score based on data quality
    """
    prediction = await predict_next_deadline(db, funder_name)

    if not prediction:
        raise HTTPException(
            status_code=404,
            detail=f"No historical data available for funder: {funder_name}",
        )

    return FunderPredictionResponse(
        prediction=FunderPrediction(
            funder_name=prediction["funder_name"],
            predicted_deadline=prediction["predicted_deadline"].date()
            if hasattr(prediction["predicted_deadline"], "date")
            else prediction["predicted_deadline"],
            confidence=prediction["confidence"],
            typical_day_of_month=prediction.get("typical_day_of_month"),
            typical_months=prediction.get("typical_months", []),
            based_on_records=prediction.get("based_on_records", 0),
            avg_cycle_days=prediction.get("avg_cycle_days"),
            last_known_deadline=prediction.get("last_known_deadline"),
            grant_titles=prediction.get("grant_titles", [])[:10],
        ),
        generated_at=datetime.utcnow(),
    )


# =============================================================================
# ML Forecast Endpoints
# =============================================================================


@router.get(
    "/ml/{funder_name}",
    response_model=MLPredictionResponse,
    summary="Get ML-based prediction for a funder",
    description="Get machine learning (Prophet) based deadline prediction.",
)
async def get_ml_prediction(
    db: AsyncSessionDep,
    funder_name: str = Path(..., description="Name of the funding agency"),
) -> MLPredictionResponse:
    """
    Get ML-based deadline prediction for a funder.

    Uses Prophet time-series forecasting when sufficient historical data exists.
    Falls back to rule-based prediction for funders with limited data.

    Returns:
    - Predicted deadline date
    - Confidence score
    - Prediction method (ml or rule_based)
    - Uncertainty range
    """
    predictor = GrantDeadlinePredictor(min_data_points=4)
    result = await predictor.get_prediction_with_fallback(db, funder_name)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Unable to generate prediction for funder: {funder_name}",
        )

    return MLPredictionResponse(
        prediction=MLPrediction(
            funder_name=funder_name,
            predicted_date=result["predicted_date"],
            confidence=result["confidence"],
            method=result["method"],
            uncertainty_days=result["uncertainty_days"],
            lower_bound=result.get("lower_bound"),
            upper_bound=result.get("upper_bound"),
        ),
        model_trained=result["method"] == "ml",
        data_points=result.get("data_points"),
        generated_at=datetime.utcnow(),
    )


# =============================================================================
# Fiscal Calendar Endpoints
# =============================================================================


@router.get(
    "/fiscal-calendar",
    response_model=FiscalCalendarResponse,
    summary="Get fiscal calendar information",
    description="Get current federal fiscal year and quarter information.",
)
async def get_fiscal_calendar(
    for_date: Optional[date] = Query(
        None, description="Date to get fiscal info for (defaults to today)"
    ),
) -> FiscalCalendarResponse:
    """
    Get federal fiscal calendar information.

    Returns current fiscal year, quarter, and related timing information.
    Useful for planning grant submissions around federal budget cycles.
    """
    target_date = for_date or date.today()

    fiscal_year = FiscalCalendar.get_fiscal_year(target_date)
    fiscal_quarter = FiscalCalendar.get_fiscal_quarter(target_date)
    quarter_end = FiscalCalendar.get_next_quarter_end(target_date)
    days_to_quarter_end = (quarter_end - target_date).days

    return FiscalCalendarResponse(
        fiscal_info=FiscalCalendarInfo(
            current_fiscal_year=fiscal_year,
            current_fiscal_quarter=fiscal_quarter,
            quarter_end_date=quarter_end,
            days_until_quarter_end=days_to_quarter_end,
            is_year_end_period=FiscalCalendar.is_fiscal_year_end_period(target_date),
            is_year_start_period=FiscalCalendar.is_fiscal_year_start_period(target_date),
        ),
        for_date=target_date,
        generated_at=datetime.utcnow(),
    )


@router.get(
    "/is-federal/{funder_name}",
    summary="Check if funder is federal",
    description="Check if a funding agency is a federal agency.",
)
async def check_federal_funder(
    funder_name: str = Path(..., description="Name of the funding agency"),
) -> dict:
    """
    Check if a funding agency is a federal agency.

    Federal agencies follow the federal fiscal year calendar (Oct 1 - Sep 30)
    and often have deadlines aligned with fiscal quarters.
    """
    is_federal = is_federal_funder(funder_name)

    return {
        "funder_name": funder_name,
        "is_federal": is_federal,
        "note": "Federal funders follow fiscal year Oct 1 - Sep 30" if is_federal else None,
    }
