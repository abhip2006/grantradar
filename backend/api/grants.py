"""
Grant API Endpoints
List, filter, search, and get grant details.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select, text
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, OptionalUser
from backend.models import Grant, Match
from backend.schemas.grants import GrantDetail, GrantList, GrantResponse, GrantSearch

router = APIRouter(prefix="/api/grants", tags=["Grants"])


@router.get(
    "",
    response_model=GrantList,
    summary="List grants",
    description="Get paginated list of grants with optional filtering."
)
async def list_grants(
    db: AsyncSessionDep,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    source: Optional[str] = Query(default=None, description="Filter by source (nih, nsf, grants_gov)"),
    category: Optional[str] = Query(default=None, description="Filter by category"),
    min_amount: Optional[int] = Query(default=None, ge=0, description="Minimum funding amount"),
    max_amount: Optional[int] = Query(default=None, ge=0, description="Maximum funding amount"),
    deadline_after: Optional[datetime] = Query(default=None, description="Deadline after date"),
    deadline_before: Optional[datetime] = Query(default=None, description="Deadline before date"),
    active_only: bool = Query(default=True, description="Only show grants with future deadlines"),
) -> GrantList:
    """
    Get a paginated list of grants.

    Supports filtering by source, category, funding amount, and deadline.
    By default, only shows grants with deadlines in the future.
    """
    # Build base query
    query = select(Grant)
    count_query = select(func.count(Grant.id))

    # Apply filters
    filters = []

    if source:
        filters.append(Grant.source == source)

    if category:
        filters.append(Grant.categories.contains([category]))

    if min_amount is not None:
        filters.append(
            or_(
                Grant.amount_min >= min_amount,
                Grant.amount_max >= min_amount
            )
        )

    if max_amount is not None:
        filters.append(
            or_(
                Grant.amount_max <= max_amount,
                Grant.amount_min <= max_amount
            )
        )

    if deadline_after:
        filters.append(Grant.deadline >= deadline_after)

    if deadline_before:
        filters.append(Grant.deadline <= deadline_before)

    if active_only:
        filters.append(
            or_(
                Grant.deadline.is_(None),
                Grant.deadline > datetime.now(timezone.utc)
            )
        )

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(Grant.posted_at.desc().nulls_last())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    grants = result.scalars().all()

    # Convert to response models
    grant_responses = [
        GrantResponse(
            id=g.id,
            source=g.source,
            external_id=g.external_id,
            title=g.title,
            agency=g.agency,
            amount_min=g.amount_min,
            amount_max=g.amount_max,
            deadline=g.deadline,
            posted_at=g.posted_at,
            url=g.url,
            categories=g.categories,
        )
        for g in grants
    ]

    return GrantList(
        grants=grant_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(grants)) < total
    )


@router.get(
    "/search",
    response_model=GrantList,
    summary="Search grants",
    description="Search grants by text query."
)
async def search_grants(
    db: AsyncSessionDep,
    q: str = Query(..., min_length=1, max_length=500, description="Search query"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of results"),
) -> GrantList:
    """
    Search grants by title, description, and agency.

    Uses PostgreSQL full-text search with:
    - Weighted ranking (title > agency > description)
    - Relevance-based result ordering using ts_rank
    - GIN-indexed tsvector for fast queries
    """
    # Convert search query to tsquery format
    # plainto_tsquery handles plain text and converts to proper tsquery
    # websearch_to_tsquery supports quoted phrases and - for exclusion
    search_query = func.websearch_to_tsquery('english', q)

    # Build full-text search query using @@ operator
    # Results are ranked by relevance using ts_rank with normalization
    # Normalization flag 32 divides rank by (1 + document length) to prefer shorter docs
    rank_expression = func.ts_rank(
        Grant.search_vector,
        search_query,
        32  # normalization: divide by 1 + document length
    )

    query = (
        select(Grant, rank_expression.label("rank"))
        .where(Grant.search_vector.op("@@")(search_query))
        .order_by(text("rank DESC"))
        .limit(limit)
    )

    count_query = (
        select(func.count(Grant.id))
        .where(Grant.search_vector.op("@@")(search_query))
    )

    # Execute queries
    result = await db.execute(query)
    rows = result.all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Convert to response models (extract Grant from (Grant, rank) tuples)
    grant_responses = [
        GrantResponse(
            id=g.id,
            source=g.source,
            external_id=g.external_id,
            title=g.title,
            agency=g.agency,
            amount_min=g.amount_min,
            amount_max=g.amount_max,
            deadline=g.deadline,
            posted_at=g.posted_at,
            url=g.url,
            categories=g.categories,
        )
        for g, rank in rows
    ]

    return GrantList(
        grants=grant_responses,
        total=total,
        page=1,
        page_size=limit,
        has_more=len(grant_responses) < total
    )


@router.get(
    "/{grant_id}",
    response_model=GrantDetail,
    summary="Get grant details",
    description="Get detailed information about a specific grant."
)
async def get_grant(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: OptionalUser,
) -> GrantDetail:
    """
    Get detailed information about a grant.

    If authenticated, includes match information for the current user.
    """
    # Fetch grant
    result = await db.execute(
        select(Grant).where(Grant.id == grant_id)
    )
    grant = result.scalar_one_or_none()

    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found"
        )

    # Get match info if user is authenticated
    match_score = None
    match_reasoning = None
    user_action = None

    if current_user:
        match_result = await db.execute(
            select(Match).where(
                and_(
                    Match.grant_id == grant_id,
                    Match.user_id == current_user.id
                )
            )
        )
        match = match_result.scalar_one_or_none()

        if match:
            match_score = match.match_score
            match_reasoning = match.reasoning
            user_action = match.user_action

    return GrantDetail(
        id=grant.id,
        source=grant.source,
        external_id=grant.external_id,
        title=grant.title,
        description=grant.description,
        agency=grant.agency,
        amount_min=grant.amount_min,
        amount_max=grant.amount_max,
        deadline=grant.deadline,
        posted_at=grant.posted_at,
        url=grant.url,
        eligibility=grant.eligibility,
        categories=grant.categories,
        created_at=grant.created_at,
        match_score=match_score,
        match_reasoning=match_reasoning,
        user_action=user_action,
    )
