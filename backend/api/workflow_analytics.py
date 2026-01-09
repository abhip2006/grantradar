"""
Workflow Analytics API Endpoints

API endpoints for workflow analytics including:
- GET /api/analytics/workflow - Get workflow analytics summary
- GET /api/analytics/workflow/bottlenecks - Identify bottlenecks
- GET /api/analytics/workflow/time-per-stage - Time analysis by stage
- GET /api/kanban/{card_id}/events - Get events for an application
- POST /api/analytics/workflow/refresh - Force cache refresh
"""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError, ValidationError
from backend.models import GrantApplication
from backend.schemas.workflow_analytics import (
    BottlenecksResponse,
    CompletionRatesResponse,
    DeadlineRiskForecastResponse,
    TimePerStageResponse,
    WorkflowAnalyticsResponse,
    WorkflowEventsListResponse,
)
from backend.services.cache import get_cache_stats
from backend.services.workflow_analytics import (
    CACHE_TTL_BOTTLENECKS,
    CACHE_TTL_COMPLETION_RATES,
    CACHE_TTL_SUMMARY,
    CACHE_TTL_TIME_PER_STAGE,
    calculate_completion_rates_cached,
    calculate_time_per_stage_cached,
    forecast_deadline_risks,
    get_application_events,
    get_workflow_analytics_summary,
    identify_bottlenecks_cached,
    invalidate_and_refresh_cache,
    invalidate_user_analytics_cache,
)

router = APIRouter(tags=["Workflow Analytics"])


# =============================================================================
# Workflow Analytics Endpoints
# =============================================================================


@router.get(
    "/api/analytics/workflow",
    response_model=WorkflowAnalyticsResponse,
    summary="Get workflow analytics summary",
    description="Get comprehensive workflow analytics including time per stage, bottlenecks, and deadline risks.",
)
async def get_workflow_analytics(
    response: Response,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(
        None,
        description="Start date for analysis period (defaults to 90 days ago)",
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date for analysis period (defaults to today)",
    ),
) -> WorkflowAnalyticsResponse:
    """
    Get comprehensive workflow analytics for the current user.

    Includes:
    - Summary metrics (total applications, completion rates, etc.)
    - Time spent in each pipeline stage
    - Identified bottlenecks with recommendations
    - Deadline risk assessment

    Response is cached for up to 10 minutes.
    """
    # Add cache headers
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL_SUMMARY * 60}"
    response.headers["X-Cache-TTL"] = str(CACHE_TTL_SUMMARY)

    return await get_workflow_analytics_summary(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/api/analytics/workflow/bottlenecks",
    response_model=BottlenecksResponse,
    summary="Identify workflow bottlenecks",
    description="Identify stages where applications are getting stuck.",
)
async def get_workflow_bottlenecks(
    response: Response,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> BottlenecksResponse:
    """
    Identify workflow bottlenecks where applications are stuck.

    Returns:
    - List of bottlenecks sorted by severity
    - Number of applications at risk
    - Recommendations for each bottleneck
    - Overall workflow health status

    Response is cached for up to 15 minutes.
    """
    # Add cache headers
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL_BOTTLENECKS * 60}"
    response.headers["X-Cache-TTL"] = str(CACHE_TTL_BOTTLENECKS)

    return await identify_bottlenecks_cached(db=db, user_id=current_user.id)


@router.get(
    "/api/analytics/workflow/time-per-stage",
    response_model=TimePerStageResponse,
    summary="Get time per stage analysis",
    description="Analyze average time spent in each pipeline stage.",
)
async def get_time_per_stage(
    response: Response,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    start_date: Optional[date] = Query(
        None,
        description="Start date for analysis (defaults to 90 days ago)",
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date for analysis (defaults to today)",
    ),
) -> TimePerStageResponse:
    """
    Get time analysis for each pipeline stage.

    Returns:
    - Average, median, min, and max hours per stage
    - Number of applications that passed through each stage
    - Current count in each stage
    - Overall completion time statistics

    Response is cached for up to 5 minutes.
    """
    # Add cache headers
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL_TIME_PER_STAGE * 60}"
    response.headers["X-Cache-TTL"] = str(CACHE_TTL_TIME_PER_STAGE)

    return await calculate_time_per_stage_cached(
        db=db,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/api/analytics/workflow/completion-rates",
    response_model=CompletionRatesResponse,
    summary="Get completion rate trends",
    description="Track submission and success rates over time.",
)
async def get_completion_rates(
    response: Response,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    period_type: str = Query(
        default="monthly",
        description="Period grouping: 'monthly' or 'quarterly'",
    ),
    periods: int = Query(
        default=6,
        ge=1,
        le=24,
        description="Number of periods to analyze",
    ),
) -> CompletionRatesResponse:
    """
    Get completion rate trends over time.

    Returns:
    - Submission and success rates by period
    - Overall rates
    - Trend direction (improving, declining, stable)

    Response is cached for up to 30 minutes.
    """
    if period_type not in ["monthly", "quarterly"]:
        raise ValidationError("period_type must be 'monthly' or 'quarterly'")

    # Add cache headers
    response.headers["Cache-Control"] = f"private, max-age={CACHE_TTL_COMPLETION_RATES * 60}"
    response.headers["X-Cache-TTL"] = str(CACHE_TTL_COMPLETION_RATES)

    return await calculate_completion_rates_cached(
        db=db,
        user_id=current_user.id,
        period_type=period_type,
        periods=periods,
    )


@router.get(
    "/api/analytics/workflow/deadline-risks",
    response_model=DeadlineRiskForecastResponse,
    summary="Forecast deadline risks",
    description="Identify applications at risk of missing deadlines.",
)
async def get_deadline_risks(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> DeadlineRiskForecastResponse:
    """
    Forecast deadline risks based on historical performance.

    Returns:
    - Applications at risk with risk scores
    - Estimated time to complete
    - Recommended actions
    - Risk level counts
    """
    return await forecast_deadline_risks(db=db, user_id=current_user.id)


# =============================================================================
# Application Events Endpoints
# =============================================================================


@router.get(
    "/api/kanban/{card_id}/events",
    response_model=WorkflowEventsListResponse,
    summary="Get application events",
    description="Get workflow events for a specific grant application.",
)
async def get_kanban_card_events(
    card_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(
        default=100,
        ge=1,
        le=500,
        description="Maximum number of events to return",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of events to skip",
    ),
) -> WorkflowEventsListResponse:
    """
    Get workflow events for a specific application (kanban card).

    Returns:
    - List of events ordered by occurrence time (newest first)
    - Total event count
    """
    # Verify the user owns this application
    result = await db.execute(
        select(GrantApplication).where(
            GrantApplication.id == card_id,
            GrantApplication.user_id == current_user.id,
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise NotFoundError("Application")

    return await get_application_events(
        db=db,
        kanban_card_id=card_id,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Cache Management Endpoints
# =============================================================================


@router.post(
    "/api/analytics/workflow/refresh",
    summary="Force cache refresh",
    description="Invalidate cached analytics and optionally pre-warm with fresh data.",
)
async def refresh_analytics_cache(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    warm_cache: bool = Query(
        default=True,
        description="Whether to pre-warm cache with fresh data after invalidation",
    ),
) -> dict:
    """
    Force refresh of analytics cache for the current user.

    This endpoint:
    1. Invalidates all cached analytics data for the user
    2. Optionally pre-calculates and caches fresh data

    Use this after significant data changes or when stale data is suspected.

    Args:
        warm_cache: If True, pre-calculates and caches fresh data

    Returns:
        Status of the cache refresh operation
    """
    user_id_str = str(current_user.id)

    # Invalidate existing cache
    entries_invalidated = invalidate_user_analytics_cache(user_id_str)

    result = {
        "status": "success",
        "user_id": user_id_str,
        "entries_invalidated": entries_invalidated,
        "cache_warmed": False,
    }

    # Optionally pre-warm cache
    if warm_cache:
        try:
            await invalidate_and_refresh_cache(db, current_user.id)
            result["cache_warmed"] = True
        except Exception as e:
            result["cache_warm_error"] = str(e)

    return result


@router.get(
    "/api/analytics/workflow/cache-status",
    summary="Get cache statistics",
    description="Get information about the current cache state.",
)
async def get_analytics_cache_status(
    current_user: CurrentUser,
) -> dict:
    """
    Get cache statistics for monitoring and debugging.

    Returns:
    - Total number of cache entries
    - Number of valid vs stale entries
    - Oldest and newest entry timestamps

    Note: This returns global cache stats, not user-specific stats.
    """
    stats = get_cache_stats()
    return {
        "status": "success",
        "cache_stats": stats,
    }


__all__ = ["router"]
