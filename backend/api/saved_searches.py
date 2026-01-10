"""
Saved Searches API Endpoints
Create, list, update, delete, and apply saved search filters.
"""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, Match, SavedSearch
from backend.schemas.saved_searches import (
    SavedSearchCreate,
    SavedSearchList,
    SavedSearchResponse,
    SavedSearchUpdate,
)
from backend.schemas.matches import MatchList, MatchResponse

router = APIRouter(prefix="/api/saved-searches", tags=["Saved Searches"])


@router.post(
    "",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create saved search",
    description="Save a search filter combination with a name.",
)
async def create_saved_search(
    saved_search: SavedSearchCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> SavedSearchResponse:
    """
    Create a new saved search with the specified filters.

    The filters are stored as JSON and can include source, categories,
    amount ranges, and other search parameters.
    """
    # Create the saved search
    db_saved_search = SavedSearch(
        user_id=current_user.id,
        name=saved_search.name,
        filters=saved_search.filters.model_dump(exclude_none=True),
        alert_enabled=saved_search.alert_enabled,
    )

    db.add(db_saved_search)
    await db.flush()
    await db.refresh(db_saved_search)

    return SavedSearchResponse(
        id=db_saved_search.id,
        name=db_saved_search.name,
        filters=db_saved_search.filters,
        alert_enabled=db_saved_search.alert_enabled,
        created_at=db_saved_search.created_at,
        last_alerted_at=db_saved_search.last_alerted_at,
    )


@router.get(
    "",
    response_model=SavedSearchList,
    summary="List saved searches",
    description="Get all saved searches for the current user.",
)
async def list_saved_searches(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> SavedSearchList:
    """
    Get all saved searches for the authenticated user.

    Results are ordered by creation date (newest first).
    """
    query = select(SavedSearch).where(SavedSearch.user_id == current_user.id).order_by(SavedSearch.created_at.desc())

    result = await db.execute(query)
    saved_searches = result.scalars().all()

    return SavedSearchList(
        saved_searches=[
            SavedSearchResponse(
                id=ss.id,
                name=ss.name,
                filters=ss.filters,
                alert_enabled=ss.alert_enabled,
                created_at=ss.created_at,
                last_alerted_at=ss.last_alerted_at,
            )
            for ss in saved_searches
        ],
        total=len(saved_searches),
    )


@router.get(
    "/{saved_search_id}",
    response_model=SavedSearchResponse,
    summary="Get saved search",
    description="Get a specific saved search by ID.",
)
async def get_saved_search(
    saved_search_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> SavedSearchResponse:
    """
    Get a specific saved search.

    Only returns searches belonging to the authenticated user.
    """
    result = await db.execute(
        select(SavedSearch).where(
            and_(
                SavedSearch.id == saved_search_id,
                SavedSearch.user_id == current_user.id,
            )
        )
    )
    saved_search = result.scalar_one_or_none()

    if not saved_search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    return SavedSearchResponse(
        id=saved_search.id,
        name=saved_search.name,
        filters=saved_search.filters,
        alert_enabled=saved_search.alert_enabled,
        created_at=saved_search.created_at,
        last_alerted_at=saved_search.last_alerted_at,
    )


@router.put(
    "/{saved_search_id}",
    response_model=SavedSearchResponse,
    summary="Update saved search",
    description="Update a saved search's name, filters, or alert settings.",
)
async def update_saved_search(
    saved_search_id: UUID,
    update_data: SavedSearchUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> SavedSearchResponse:
    """
    Update an existing saved search.

    Any field not provided will remain unchanged.
    """
    result = await db.execute(
        select(SavedSearch).where(
            and_(
                SavedSearch.id == saved_search_id,
                SavedSearch.user_id == current_user.id,
            )
        )
    )
    saved_search = result.scalar_one_or_none()

    if not saved_search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    # Update fields if provided
    if update_data.name is not None:
        saved_search.name = update_data.name

    if update_data.filters is not None:
        saved_search.filters = update_data.filters.model_dump(exclude_none=True)

    if update_data.alert_enabled is not None:
        saved_search.alert_enabled = update_data.alert_enabled

    await db.flush()
    await db.refresh(saved_search)

    return SavedSearchResponse(
        id=saved_search.id,
        name=saved_search.name,
        filters=saved_search.filters,
        alert_enabled=saved_search.alert_enabled,
        created_at=saved_search.created_at,
        last_alerted_at=saved_search.last_alerted_at,
    )


@router.delete(
    "/{saved_search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete saved search",
    description="Delete a saved search.",
)
async def delete_saved_search(
    saved_search_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a saved search.

    This action cannot be undone.
    """
    result = await db.execute(
        select(SavedSearch).where(
            and_(
                SavedSearch.id == saved_search_id,
                SavedSearch.user_id == current_user.id,
            )
        )
    )
    saved_search = result.scalar_one_or_none()

    if not saved_search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    await db.delete(saved_search)
    await db.flush()


@router.post(
    "/{saved_search_id}/apply",
    response_model=MatchList,
    summary="Apply saved search",
    description="Get grants matching a saved search's filters.",
)
async def apply_saved_search(
    saved_search_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
) -> MatchList:
    """
    Apply a saved search and return matching grants.

    Uses the filters stored in the saved search to query matches.
    """
    # Get the saved search
    result = await db.execute(
        select(SavedSearch).where(
            and_(
                SavedSearch.id == saved_search_id,
                SavedSearch.user_id == current_user.id,
            )
        )
    )
    saved_search = result.scalar_one_or_none()

    if not saved_search:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved search not found")

    filters = saved_search.filters

    # Build query based on saved filters
    query = select(Match).options(joinedload(Match.grant)).where(Match.user_id == current_user.id)
    count_query = select(func.count(Match.id)).where(Match.user_id == current_user.id)

    # Apply filters from saved search
    filter_conditions = []

    # Minimum score filter (convert from 0-100 to 0-1)
    min_score = filters.get("min_score")
    if min_score is not None:
        filter_conditions.append(Match.match_score >= (min_score / 100))

    # Source filter
    source = filters.get("source")
    if source:
        query = query.join(Grant, Match.grant_id == Grant.id)
        count_query = count_query.join(Grant, Match.grant_id == Grant.id)
        filter_conditions.append(Grant.source == source)

    # Show saved only filter
    show_saved_only = filters.get("show_saved_only")
    if show_saved_only:
        filter_conditions.append(Match.user_action == "saved")
    else:
        # By default, exclude dismissed
        filter_conditions.append(or_(Match.user_action.is_(None), Match.user_action != "dismissed"))

    # Amount filters
    min_amount = filters.get("min_amount")
    max_amount = filters.get("max_amount")
    if min_amount is not None or max_amount is not None:
        if source is None:  # Join not done yet
            query = query.join(Grant, Match.grant_id == Grant.id)
            count_query = count_query.join(Grant, Match.grant_id == Grant.id)

        if min_amount is not None:
            filter_conditions.append(or_(Grant.amount_min >= min_amount, Grant.amount_max >= min_amount))
        if max_amount is not None:
            filter_conditions.append(or_(Grant.amount_max <= max_amount, Grant.amount_min <= max_amount))

    # Active only filter
    active_only = filters.get("active_only")
    if active_only:
        if source is None and min_amount is None and max_amount is None:
            query = query.join(Grant, Match.grant_id == Grant.id)
            count_query = count_query.join(Grant, Match.grant_id == Grant.id)
        filter_conditions.append(or_(Grant.deadline.is_(None), Grant.deadline > datetime.now(timezone.utc)))

    # Apply all filter conditions
    if filter_conditions:
        query = query.where(and_(*filter_conditions))
        count_query = count_query.where(and_(*filter_conditions))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    query = query.order_by(Match.match_score.desc())
    query = query.offset(offset).limit(page_size)

    # Execute query
    result = await db.execute(query)
    matches = result.unique().scalars().all()

    # Convert to response models
    match_responses = [
        MatchResponse(
            id=m.id,
            grant_id=m.grant_id,
            match_score=m.match_score,
            predicted_success=m.predicted_success,
            user_action=m.user_action,
            created_at=m.created_at,
            grant_title=m.grant.title,
            grant_agency=m.grant.agency,
            grant_deadline=m.grant.deadline,
            grant_amount_min=m.grant.amount_min,
            grant_amount_max=m.grant.amount_max,
        )
        for m in matches
    ]

    return MatchList(
        matches=match_responses, total=total, page=page, page_size=page_size, has_more=(offset + len(matches)) < total
    )
