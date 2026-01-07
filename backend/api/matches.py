"""
Match API Endpoints
List matches, get details, perform actions, and submit feedback.
"""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, Match
from backend.schemas.matches import (
    MatchAction,
    MatchDetail,
    MatchFeedback,
    MatchList,
    MatchResponse,
)

router = APIRouter(prefix="/api/matches", tags=["Matches"])


@router.get(
    "",
    response_model=MatchList,
    summary="List matches",
    description="Get paginated list of grant matches for the current user."
)
async def list_matches(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    min_score: Optional[float] = Query(default=None, ge=0, le=1, description="Minimum match score"),
    max_score: Optional[float] = Query(default=None, ge=0, le=1, description="Maximum match score"),
    user_action: Optional[str] = Query(default=None, description="Filter by action (saved, dismissed)"),
    exclude_dismissed: bool = Query(default=True, description="Exclude dismissed matches"),
) -> MatchList:
    """
    Get a paginated list of grant matches for the authenticated user.

    Matches are sorted by score (highest first) by default.
    """
    # Build base query with grant join
    query = (
        select(Match)
        .options(joinedload(Match.grant))
        .where(Match.user_id == current_user.id)
    )
    count_query = (
        select(func.count(Match.id))
        .where(Match.user_id == current_user.id)
    )

    # Apply filters
    filters = []

    if min_score is not None:
        filters.append(Match.match_score >= min_score)

    if max_score is not None:
        filters.append(Match.match_score <= max_score)

    if user_action:
        filters.append(Match.user_action == user_action)
    elif exclude_dismissed:
        filters.append(
            or_(
                Match.user_action.is_(None),
                Match.user_action != "dismissed"
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
        matches=match_responses,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(matches)) < total
    )


# Import or_ for the filter
from sqlalchemy import or_


@router.get(
    "/{match_id}",
    response_model=MatchDetail,
    summary="Get match details",
    description="Get detailed information about a specific match."
)
async def get_match(
    match_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MatchDetail:
    """
    Get detailed information about a match including reasoning.

    Only returns matches belonging to the authenticated user.
    """
    # Fetch match with grant
    result = await db.execute(
        select(Match)
        .options(joinedload(Match.grant))
        .where(
            and_(
                Match.id == match_id,
                Match.user_id == current_user.id
            )
        )
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    return MatchDetail(
        id=match.id,
        grant_id=match.grant_id,
        user_id=match.user_id,
        match_score=match.match_score,
        reasoning=match.reasoning,
        predicted_success=match.predicted_success,
        user_action=match.user_action,
        user_feedback=match.user_feedback,
        created_at=match.created_at,
        grant_title=match.grant.title,
        grant_description=match.grant.description,
        grant_agency=match.grant.agency,
        grant_deadline=match.grant.deadline,
        grant_amount_min=match.grant.amount_min,
        grant_amount_max=match.grant.amount_max,
        grant_url=match.grant.url,
        grant_eligibility=match.grant.eligibility,
        grant_categories=match.grant.categories,
    )


@router.post(
    "/{match_id}/action",
    response_model=MatchDetail,
    summary="Perform action on match",
    description="Save or dismiss a grant match."
)
async def match_action(
    match_id: UUID,
    action: MatchAction,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MatchDetail:
    """
    Perform an action on a match (save, dismiss, apply, interested).

    Updates the user_action field on the match record.
    """
    # Fetch match
    result = await db.execute(
        select(Match)
        .options(joinedload(Match.grant))
        .where(
            and_(
                Match.id == match_id,
                Match.user_id == current_user.id
            )
        )
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Update action
    match.user_action = action.action
    await db.flush()
    await db.refresh(match)

    return MatchDetail(
        id=match.id,
        grant_id=match.grant_id,
        user_id=match.user_id,
        match_score=match.match_score,
        reasoning=match.reasoning,
        predicted_success=match.predicted_success,
        user_action=match.user_action,
        user_feedback=match.user_feedback,
        created_at=match.created_at,
        grant_title=match.grant.title,
        grant_description=match.grant.description,
        grant_agency=match.grant.agency,
        grant_deadline=match.grant.deadline,
        grant_amount_min=match.grant.amount_min,
        grant_amount_max=match.grant.amount_max,
        grant_url=match.grant.url,
        grant_eligibility=match.grant.eligibility,
        grant_categories=match.grant.categories,
    )


@router.post(
    "/{match_id}/feedback",
    response_model=MatchDetail,
    summary="Submit match feedback",
    description="Submit feedback on match quality to improve recommendations."
)
async def match_feedback(
    match_id: UUID,
    feedback: MatchFeedback,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MatchDetail:
    """
    Submit feedback on a match for model improvement.

    Feedback helps improve future match quality.
    """
    # Fetch match
    result = await db.execute(
        select(Match)
        .options(joinedload(Match.grant))
        .where(
            and_(
                Match.id == match_id,
                Match.user_id == current_user.id
            )
        )
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Match not found"
        )

    # Update feedback
    match.user_feedback = {
        "relevance_rating": feedback.relevance_rating,
        "would_apply": feedback.would_apply,
        "feedback_text": feedback.feedback_text,
        "match_quality_issues": feedback.match_quality_issues,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.flush()
    await db.refresh(match)

    return MatchDetail(
        id=match.id,
        grant_id=match.grant_id,
        user_id=match.user_id,
        match_score=match.match_score,
        reasoning=match.reasoning,
        predicted_success=match.predicted_success,
        user_action=match.user_action,
        user_feedback=match.user_feedback,
        created_at=match.created_at,
        grant_title=match.grant.title,
        grant_description=match.grant.description,
        grant_agency=match.grant.agency,
        grant_deadline=match.grant.deadline,
        grant_amount_min=match.grant.amount_min,
        grant_amount_max=match.grant.amount_max,
        grant_url=match.grant.url,
        grant_eligibility=match.grant.eligibility,
        grant_categories=match.grant.categories,
    )
