"""
Funder Insights API Endpoints
Historical data on funders including average award sizes, success rates, and grant patterns.
"""

from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, case, distinct, func, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, OptionalUser
from backend.models import ApplicationStage, Grant, GrantApplication
from backend.schemas.funder_insights import (
    DeadlineMonth,
    FunderGrantResponse,
    FunderGrantsResponse,
    FunderInsightsResponse,
    FunderListResponse,
    FunderSummary,
    UserApplication,
    UserFunderHistory,
)

router = APIRouter(prefix="/api/funders", tags=["Funder Insights"])

# Month names for display
MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def is_grant_active(deadline: Optional[datetime]) -> bool:
    """Check if a grant is still active (deadline hasn't passed)."""
    if not deadline:
        return True  # No deadline means potentially still active
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return deadline > now


@router.get(
    "",
    response_model=FunderListResponse,
    summary="List all funders",
    description="Get all funders with summary statistics.",
)
async def list_funders(
    db: AsyncSessionDep,
    search: Optional[str] = Query(None, description="Search funders by name"),
    limit: int = Query(default=50, ge=1, le=200, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
) -> FunderListResponse:
    """
    List all funders with summary statistics.

    Returns unique funder names (agencies) with:
    - Total grants offered
    - Average funding amounts
    - Common focus areas
    - Number of active grants
    """
    now = datetime.now(timezone.utc)

    # Base query for aggregating by agency
    base_query = (
        select(
            Grant.agency,
            func.count(Grant.id).label("total_grants"),
            func.avg(Grant.amount_min).label("avg_amount_min"),
            func.avg(Grant.amount_max).label("avg_amount_max"),
            func.count(case((Grant.deadline > now, 1), else_=None)).label("active_grants"),
        )
        .where(Grant.agency.isnot(None))
        .where(Grant.agency != "")
    )

    # Apply search filter
    if search:
        base_query = base_query.where(Grant.agency.ilike(f"%{search}%"))

    # Group and order
    base_query = base_query.group_by(Grant.agency).order_by(func.count(Grant.id).desc()).limit(limit).offset(offset)

    result = await db.execute(base_query)
    rows = result.all()

    # Get total count
    count_query = select(func.count(distinct(Grant.agency))).where(Grant.agency.isnot(None)).where(Grant.agency != "")
    if search:
        count_query = count_query.where(Grant.agency.ilike(f"%{search}%"))

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get focus areas for each funder
    funders = []
    for row in rows:
        agency_name = row.agency
        if not agency_name:
            continue

        # Get top focus areas for this funder
        categories_query = (
            select(func.unnest(Grant.categories).label("category"))
            .where(Grant.agency == agency_name)
            .where(Grant.categories.isnot(None))
        )
        categories_subquery = categories_query.subquery()

        focus_areas_query = (
            select(categories_subquery.c.category, func.count().label("cnt"))
            .group_by(categories_subquery.c.category)
            .order_by(func.count().desc())
            .limit(5)
        )
        focus_result = await db.execute(focus_areas_query)
        focus_areas = [r.category for r in focus_result.all() if r.category]

        funders.append(
            FunderSummary(
                funder_name=agency_name,
                total_grants=row.total_grants,
                avg_amount_min=float(row.avg_amount_min) if row.avg_amount_min else None,
                avg_amount_max=float(row.avg_amount_max) if row.avg_amount_max else None,
                focus_areas=focus_areas,
                active_grants=row.active_grants or 0,
            )
        )

    return FunderListResponse(funders=funders, total=total)


@router.get(
    "/top",
    response_model=FunderListResponse,
    summary="Get top funders",
    description="Get top funders ranked by grant count or total funding amount.",
)
async def get_top_funders(
    db: AsyncSessionDep,
    sort_by: str = Query(
        default="grant_count",
        regex="^(grant_count|funding_amount)$",
        description="Sort by 'grant_count' or 'funding_amount'",
    ),
    limit: int = Query(default=10, ge=1, le=50, description="Number of top funders to return"),
) -> FunderListResponse:
    """
    Get top funders ranked by grant count or total funding amount.

    Returns the top funders with summary statistics, sorted by either:
    - grant_count: Total number of grants offered (default)
    - funding_amount: Total maximum funding amount available
    """
    now = datetime.now(timezone.utc)

    # Determine order column
    if sort_by == "funding_amount":
        order_col = func.sum(func.coalesce(Grant.amount_max, Grant.amount_min, 0)).desc()
    else:
        order_col = func.count(Grant.id).desc()

    # Base query for aggregating by agency
    base_query = (
        select(
            Grant.agency,
            func.count(Grant.id).label("total_grants"),
            func.avg(Grant.amount_min).label("avg_amount_min"),
            func.avg(Grant.amount_max).label("avg_amount_max"),
            func.sum(func.coalesce(Grant.amount_max, Grant.amount_min, 0)).label("total_funding"),
            func.count(case((Grant.deadline > now, 1), else_=None)).label("active_grants"),
        )
        .where(Grant.agency.isnot(None))
        .where(Grant.agency != "")
        .group_by(Grant.agency)
        .order_by(order_col)
        .limit(limit)
    )

    result = await db.execute(base_query)
    rows = result.all()

    # Get focus areas for each funder
    funders = []
    for row in rows:
        agency_name = row.agency
        if not agency_name:
            continue

        # Get top focus areas for this funder
        categories_query = (
            select(func.unnest(Grant.categories).label("category"))
            .where(Grant.agency == agency_name)
            .where(Grant.categories.isnot(None))
        )
        categories_subquery = categories_query.subquery()

        focus_areas_query = (
            select(categories_subquery.c.category, func.count().label("cnt"))
            .group_by(categories_subquery.c.category)
            .order_by(func.count().desc())
            .limit(5)
        )
        focus_result = await db.execute(focus_areas_query)
        focus_areas = [r.category for r in focus_result.all() if r.category]

        funders.append(
            FunderSummary(
                funder_name=agency_name,
                total_grants=row.total_grants,
                avg_amount_min=float(row.avg_amount_min) if row.avg_amount_min else None,
                avg_amount_max=float(row.avg_amount_max) if row.avg_amount_max else None,
                focus_areas=focus_areas,
                active_grants=row.active_grants or 0,
            )
        )

    return FunderListResponse(funders=funders, total=len(funders))


@router.get(
    "/{funder_name}/insights",
    response_model=FunderInsightsResponse,
    summary="Get funder insights",
    description="Get detailed analytics for a specific funder.",
)
async def get_funder_insights(
    funder_name: str,
    db: AsyncSessionDep,
    current_user: OptionalUser,
) -> FunderInsightsResponse:
    """
    Get detailed analytics for a specific funder.

    Includes:
    - Average/min/max funding amounts
    - Number of grants offered
    - Common focus areas with counts
    - Typical deadline months (seasonality)
    - User's history with this funder (if authenticated)
    """
    # Decode URL-encoded funder name
    decoded_name = unquote(funder_name)
    datetime.now(timezone.utc)

    # Get all grants from this funder
    grants_query = select(Grant).where(Grant.agency == decoded_name)
    result = await db.execute(grants_query)
    grants = result.scalars().all()

    if not grants:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No grants found for funder: {decoded_name}",
        )

    # Calculate statistics
    total_grants = len(grants)
    active_grants = sum(1 for g in grants if is_grant_active(g.deadline))

    amounts_min = [g.amount_min for g in grants if g.amount_min]
    amounts_max = [g.amount_max for g in grants if g.amount_max]

    avg_amount_min = sum(amounts_min) / len(amounts_min) if amounts_min else None
    avg_amount_max = sum(amounts_max) / len(amounts_max) if amounts_max else None
    min_amount = min(amounts_min) if amounts_min else None
    max_amount = max(amounts_max) if amounts_max else None

    # Focus areas analysis
    focus_area_counts: dict[str, int] = defaultdict(int)
    for grant in grants:
        if grant.categories:
            for category in grant.categories:
                focus_area_counts[category] += 1

    # Sort by count and get top focus areas
    sorted_focus_areas = sorted(focus_area_counts.items(), key=lambda x: x[1], reverse=True)
    top_focus_areas = [area for area, _ in sorted_focus_areas[:10]]

    # Deadline seasonality
    month_counts: dict[int, int] = defaultdict(int)
    for grant in grants:
        if grant.deadline:
            month_counts[grant.deadline.month] += 1

    deadline_months = [
        DeadlineMonth(
            month=month,
            month_name=MONTH_NAMES[month],
            grant_count=count,
        )
        for month, count in sorted(month_counts.items())
    ]

    # Find typical deadline months (top 3)
    sorted_months = sorted(month_counts.items(), key=lambda x: x[1], reverse=True)
    typical_deadline_months = [MONTH_NAMES[m] for m, _ in sorted_months[:3]]

    # User history with this funder
    user_history = None
    if current_user:
        # Get user's applications for grants from this funder
        apps_query = (
            select(GrantApplication)
            .options(joinedload(GrantApplication.grant))
            .where(
                and_(
                    GrantApplication.user_id == current_user.id,
                    GrantApplication.grant_id.in_([g.id for g in grants]),
                )
            )
            .order_by(GrantApplication.updated_at.desc())
        )
        apps_result = await db.execute(apps_query)
        applications = apps_result.unique().scalars().all()

        total_applications = len(applications)
        awarded_count = sum(1 for a in applications if a.stage == ApplicationStage.AWARDED)
        rejected_count = sum(1 for a in applications if a.stage == ApplicationStage.REJECTED)
        pending_count = total_applications - awarded_count - rejected_count

        decided = awarded_count + rejected_count
        success_rate = (awarded_count / decided) if decided > 0 else None

        user_apps = [
            UserApplication(
                grant_id=app.grant_id,
                grant_title=app.grant.title,
                stage=app.stage.value,
                applied_at=app.created_at,
            )
            for app in applications[:5]  # Last 5 applications
        ]

        user_history = UserFunderHistory(
            total_applications=total_applications,
            awarded_count=awarded_count,
            rejected_count=rejected_count,
            pending_count=pending_count,
            success_rate=success_rate,
            applications=user_apps,
        )

    return FunderInsightsResponse(
        funder_name=decoded_name,
        total_grants=total_grants,
        active_grants=active_grants,
        avg_amount_min=avg_amount_min,
        avg_amount_max=avg_amount_max,
        min_amount=min_amount,
        max_amount=max_amount,
        focus_areas=top_focus_areas,
        focus_area_counts=dict(focus_area_counts),
        deadline_months=deadline_months,
        typical_deadline_months=typical_deadline_months,
        user_history=user_history,
    )


@router.get(
    "/{funder_name}/grants",
    response_model=FunderGrantsResponse,
    summary="Get funder grants",
    description="Get all grants from a specific funder.",
)
async def get_funder_grants(
    funder_name: str,
    db: AsyncSessionDep,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(default=False, description="Only show active grants"),
) -> FunderGrantsResponse:
    """
    Get all grants from a specific funder.

    Supports pagination and filtering by active status.
    """
    # Decode URL-encoded funder name
    decoded_name = unquote(funder_name)
    now = datetime.now(timezone.utc)

    # Base query
    base_query = select(Grant).where(Grant.agency == decoded_name)

    # Filter active only
    if active_only:
        base_query = base_query.where((Grant.deadline.is_(None)) | (Grant.deadline > now))

    # Get total count
    count_query = select(func.count()).select_from(base_query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    grants_query = (
        base_query.order_by(Grant.deadline.asc().nullslast(), Grant.posted_at.desc()).limit(page_size).offset(offset)
    )

    result = await db.execute(grants_query)
    grants = result.scalars().all()

    # Convert to response
    grant_responses = [
        FunderGrantResponse(
            id=grant.id,
            title=grant.title,
            description=grant.description[:300] if grant.description else None,
            amount_min=grant.amount_min,
            amount_max=grant.amount_max,
            deadline=grant.deadline,
            posted_at=grant.posted_at,
            categories=grant.categories,
            url=grant.url,
            is_active=is_grant_active(grant.deadline),
        )
        for grant in grants
    ]

    return FunderGrantsResponse(
        funder_name=decoded_name,
        grants=grant_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(grants)) < total,
    )
