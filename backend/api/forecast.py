"""
Forecast API Endpoints
Predict upcoming grant opportunities based on historical patterns.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from backend.api.deps import AsyncSessionDep, CurrentUser, OptionalUser
from backend.schemas.forecast import (
    ForecastGrant,
    ForecastUpcomingResponse,
    RecommendationGrant,
    RecommendationsResponse,
    SeasonalTrend,
    SeasonalTrendResponse,
)
from backend.services.forecast import (
    get_recommendations,
    get_seasonal_trends,
    get_upcoming_forecasts,
)


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
