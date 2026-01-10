"""
Match API Endpoints
List matches, get details, perform actions, and submit feedback.
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.types import Text
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, Match
from backend.schemas.matches import (
    MatchAction,
    MatchDetail,
    MatchFeedback,
    MatchList,
    MatchResponse,
    OutcomeUpdate,
)

router = APIRouter(prefix="/api/matches", tags=["Matches"])


@router.get(
    "",
    response_model=MatchList,
    summary="List matches",
    description="Get paginated list of grant matches for the current user.",
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
    # Grant-level filters
    agency: Optional[List[str]] = Query(default=None, description="Filter by funding agencies"),
    source: Optional[str] = Query(default=None, description="Filter by grant source"),
    categories: Optional[List[str]] = Query(default=None, description="Filter by categories"),
    min_amount: Optional[int] = Query(default=None, ge=0, description="Minimum funding amount"),
    max_amount: Optional[int] = Query(default=None, ge=0, description="Maximum funding amount"),
    deadline_after: Optional[datetime] = Query(default=None, description="Deadline on or after date"),
    deadline_before: Optional[datetime] = Query(default=None, description="Deadline on or before date"),
    deadline_proximity: Optional[int] = Query(
        default=None,
        ge=1,
        le=365,
        description="Filter grants with deadlines within X days from now (e.g., 30, 60, 90, 180)",
    ),
) -> MatchList:
    """
    Get a paginated list of grant matches for the authenticated user.

    Matches are sorted by score (highest first) by default.
    Supports filtering by match score, user action, and grant-level attributes.
    """
    # Build base query with grant join
    query = select(Match).join(Match.grant).options(joinedload(Match.grant)).where(Match.user_id == current_user.id)
    count_query = (
        select(func.count(Match.id)).select_from(Match).join(Match.grant).where(Match.user_id == current_user.id)
    )

    # Apply match-level filters
    match_filters = []

    if min_score is not None:
        match_filters.append(Match.match_score >= min_score)

    if max_score is not None:
        match_filters.append(Match.match_score <= max_score)

    if user_action:
        match_filters.append(Match.user_action == user_action)
    elif exclude_dismissed:
        match_filters.append(or_(Match.user_action.is_(None), Match.user_action != "dismissed"))

    # Apply grant-level filters
    grant_filters = []

    if agency:
        grant_filters.append(Grant.agency.in_(agency))

    if source:
        grant_filters.append(Grant.source == source)

    if categories:
        # Match any category in the list using PostgreSQL array overlap operator
        # The && operator checks if two arrays have any elements in common
        # Cast the column type explicitly since StringArray TypeDecorator doesn't expose overlap()
        from sqlalchemy import cast

        grant_filters.append(cast(Grant.categories, ARRAY(Text)).overlap(categories))

    if min_amount is not None:
        # Include grants where either min or max is >= min_amount
        grant_filters.append(or_(Grant.amount_min >= min_amount, Grant.amount_max >= min_amount))

    if max_amount is not None:
        # Include grants where either min or max is <= max_amount
        grant_filters.append(
            or_(Grant.amount_max <= max_amount, and_(Grant.amount_max.is_(None), Grant.amount_min <= max_amount))
        )

    if deadline_after is not None:
        grant_filters.append(Grant.deadline >= deadline_after)

    if deadline_before is not None:
        grant_filters.append(Grant.deadline <= deadline_before)

    # Deadline proximity filter: deadline is between now and now + X days
    if deadline_proximity is not None:
        now = datetime.now(timezone.utc)
        deadline_limit = now + timedelta(days=deadline_proximity)
        grant_filters.append(Grant.deadline >= now)
        grant_filters.append(Grant.deadline <= deadline_limit)

    # Combine all filters
    all_filters = match_filters + grant_filters

    if all_filters:
        query = query.where(and_(*all_filters))
        count_query = count_query.where(and_(*all_filters))

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
            application_status=m.application_status,
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


@router.get(
    "/{match_id}",
    response_model=MatchDetail,
    summary="Get match details",
    description="Get detailed information about a specific match.",
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
        .where(and_(Match.id == match_id, Match.user_id == current_user.id))
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

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
        application_status=match.application_status,
        application_submitted_at=match.application_submitted_at,
        outcome_received_at=match.outcome_received_at,
        award_amount=match.award_amount,
        outcome_notes=match.outcome_notes,
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
    description="Save or dismiss a grant match.",
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
        .where(and_(Match.id == match_id, Match.user_id == current_user.id))
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

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
        application_status=match.application_status,
        application_submitted_at=match.application_submitted_at,
        outcome_received_at=match.outcome_received_at,
        award_amount=match.award_amount,
        outcome_notes=match.outcome_notes,
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
    description="Submit feedback on match quality to improve recommendations.",
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
        .where(and_(Match.id == match_id, Match.user_id == current_user.id))
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

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
        application_status=match.application_status,
        application_submitted_at=match.application_submitted_at,
        outcome_received_at=match.outcome_received_at,
        award_amount=match.award_amount,
        outcome_notes=match.outcome_notes,
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
    "/{match_id}/outcome",
    response_model=MatchDetail,
    summary="Update application outcome",
    description="Track application status and outcome for data improvement.",
)
async def update_outcome(
    match_id: UUID,
    outcome: OutcomeUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MatchDetail:
    """
    Update application outcome for a match.

    Tracks application status and outcome information for the data flywheel.
    Only the match owner can update the outcome.
    """
    # Fetch match with grant
    result = await db.execute(
        select(Match)
        .options(joinedload(Match.grant))
        .where(and_(Match.id == match_id, Match.user_id == current_user.id))
    )
    match = result.unique().scalar_one_or_none()

    if not match:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found")

    # Update outcome fields
    match.application_status = outcome.application_status
    match.application_submitted_at = outcome.application_submitted_at
    match.outcome_received_at = outcome.outcome_received_at
    match.award_amount = outcome.award_amount
    match.outcome_notes = outcome.outcome_notes

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
        application_status=match.application_status,
        application_submitted_at=match.application_submitted_at,
        outcome_received_at=match.outcome_received_at,
        award_amount=match.award_amount,
        outcome_notes=match.outcome_notes,
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
