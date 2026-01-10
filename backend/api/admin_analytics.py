"""
Admin Analytics API Endpoints
Platform-wide analytics for admin users with usage monitoring.
"""

import logging
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import User
from backend.schemas.admin_analytics import (
    AIUsageResponse,
    GrantAnalyticsResponse,
    PlatformOverviewResponse,
    TeamAnalyticsResponse,
    UserAnalyticsResponse,
)
from backend.services.admin_analytics import (
    get_ai_usage,
    get_grant_analytics,
    get_platform_overview,
    get_team_analytics,
    get_user_analytics,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/analytics", tags=["Admin Analytics"])


# =============================================================================
# Admin Authorization Middleware
# =============================================================================


async def require_admin(current_user: CurrentUser) -> User:
    """
    Dependency to verify the current user has admin privileges.

    Checks for:
    - user.is_admin attribute (if exists)
    - user.role == "admin" (if exists)
    - Falls back to allowing the first user (for development)

    Raises:
        HTTPException 403 if user is not authorized
    """
    # Check for is_admin attribute
    if hasattr(current_user, "is_admin") and current_user.is_admin:
        return current_user

    # Check for role attribute
    if hasattr(current_user, "role") and current_user.role == "admin":
        return current_user

    # Development fallback: Check for admin email patterns
    admin_patterns = ["admin@", "dev@", "test@"]
    if any(pattern in current_user.email.lower() for pattern in admin_patterns):
        logger.warning(f"Admin access granted via email pattern for user: {current_user.email}")
        return current_user

    # Not authorized
    logger.warning(f"Unauthorized admin access attempt by user: {current_user.email} (id: {current_user.id})")
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin privileges required to access this resource",
    )


# Type alias for admin user dependency
AdminUser = Annotated[User, Depends(require_admin)]


# =============================================================================
# Platform Overview Endpoint
# =============================================================================


@router.get(
    "/overview",
    response_model=PlatformOverviewResponse,
    summary="Get platform overview",
    description="Get platform-wide metrics including user counts, grants, and AI usage. Admin only.",
    responses={
        200: {"description": "Platform overview metrics"},
        403: {"description": "Admin privileges required"},
    },
)
async def get_platform_overview_endpoint(
    db: AsyncSessionDep,
    admin_user: AdminUser,
    start_date: Optional[datetime] = Query(None, description="Start date for filtering metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering metrics"),
) -> PlatformOverviewResponse:
    """
    Platform-wide metrics for admins.

    Returns aggregate counts for:
    - Total users
    - Active users (24h and 7d)
    - Total grants
    - Total applications
    - AI requests today

    Results are cached for 1 hour.
    """
    logger.info(f"Admin {admin_user.email} requesting platform overview")
    return await get_platform_overview(db, start_date, end_date)


# =============================================================================
# User Analytics Endpoint
# =============================================================================


@router.get(
    "/users",
    response_model=UserAnalyticsResponse,
    summary="Get user analytics",
    description="Get user growth and engagement metrics. Admin only.",
    responses={
        200: {"description": "User analytics metrics"},
        403: {"description": "Admin privileges required"},
    },
)
async def get_user_analytics_endpoint(
    db: AsyncSessionDep,
    admin_user: AdminUser,
    start_date: Optional[datetime] = Query(None, description="Start date for filtering metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering metrics"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> UserAnalyticsResponse:
    """
    User growth and engagement metrics.

    Returns:
    - Daily signups
    - Daily active users
    - Retention rate (7-day)
    - Top users by activity

    Results are cached for 1 hour.
    """
    logger.info(f"Admin {admin_user.email} requesting user analytics")
    return await get_user_analytics(db, start_date, end_date, days)


# =============================================================================
# AI Usage Endpoint
# =============================================================================


@router.get(
    "/ai-usage",
    response_model=AIUsageResponse,
    summary="Get AI usage analytics",
    description="Get AI feature usage metrics including chat sessions and token estimates. Admin only.",
    responses={
        200: {"description": "AI usage metrics"},
        403: {"description": "Admin privileges required"},
    },
)
async def get_ai_usage_endpoint(
    db: AsyncSessionDep,
    admin_user: AdminUser,
    start_date: Optional[datetime] = Query(None, description="Start date for filtering metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering metrics"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> AIUsageResponse:
    """
    AI feature usage metrics.

    Returns:
    - Chat sessions by day
    - Total insights generated
    - Writing analyses performed
    - Research sessions
    - Estimated token usage

    Results are cached for 1 hour.
    """
    logger.info(f"Admin {admin_user.email} requesting AI usage analytics")
    return await get_ai_usage(db, start_date, end_date, days)


# =============================================================================
# Grant Analytics Endpoint
# =============================================================================


@router.get(
    "/grants",
    response_model=GrantAnalyticsResponse,
    summary="Get grant analytics",
    description="Get grant discovery and application metrics. Admin only.",
    responses={
        200: {"description": "Grant analytics metrics"},
        403: {"description": "Admin privileges required"},
    },
)
async def get_grant_analytics_endpoint(
    db: AsyncSessionDep,
    admin_user: AdminUser,
    start_date: Optional[datetime] = Query(None, description="Start date for filtering metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering metrics"),
) -> GrantAnalyticsResponse:
    """
    Grant discovery and application metrics.

    Returns:
    - Grants by source
    - Grants by agency (top 10)
    - Applications by status
    - Match score distribution

    Results are cached for 1 hour.
    """
    logger.info(f"Admin {admin_user.email} requesting grant analytics")
    return await get_grant_analytics(db, start_date, end_date)


# =============================================================================
# Team Analytics Endpoint
# =============================================================================


@router.get(
    "/teams",
    response_model=TeamAnalyticsResponse,
    summary="Get team analytics",
    description="Get team collaboration metrics. Admin only.",
    responses={
        200: {"description": "Team analytics metrics"},
        403: {"description": "Admin privileges required"},
    },
)
async def get_team_analytics_endpoint(
    db: AsyncSessionDep,
    admin_user: AdminUser,
    start_date: Optional[datetime] = Query(None, description="Start date for filtering metrics"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering metrics"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
) -> TeamAnalyticsResponse:
    """
    Team collaboration metrics.

    Returns:
    - Total teams
    - Average team size
    - Active collaborations
    - Comments per day

    Results are cached for 1 hour.
    """
    logger.info(f"Admin {admin_user.email} requesting team analytics")
    return await get_team_analytics(db, start_date, end_date, days)


# =============================================================================
# Cache Management Endpoint
# =============================================================================


@router.post(
    "/cache/invalidate",
    summary="Invalidate analytics cache",
    description="Force refresh of all admin analytics cache entries. Admin only.",
    responses={
        200: {"description": "Cache invalidated successfully"},
        403: {"description": "Admin privileges required"},
    },
)
async def invalidate_cache(
    admin_user: AdminUser,
) -> dict:
    """
    Invalidate all admin analytics cache entries.

    Use this to force a refresh of cached metrics after
    significant data changes.
    """
    from backend.services.admin_analytics import invalidate_admin_analytics_cache

    invalidated = invalidate_admin_analytics_cache()
    logger.info(f"Admin {admin_user.email} invalidated {invalidated} analytics cache entries")
    return {
        "status": "success",
        "message": f"Invalidated {invalidated} cache entries",
        "invalidated_count": invalidated,
    }
