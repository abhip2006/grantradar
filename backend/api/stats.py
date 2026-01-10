"""
Statistics API Endpoints
Dashboard statistics and analytics.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Grant, LabProfile, Match
from backend.schemas.stats import (
    DashboardStats,
    MatchScoreDistribution,
    RecentMatch,
    UpcomingDeadline,
)

router = APIRouter(prefix="/api/stats", tags=["Statistics"])


@router.get(
    "",
    response_model=DashboardStats,
    summary="Get dashboard statistics",
    description="Get aggregated statistics for the user dashboard.",
)
async def get_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> DashboardStats:
    """
    Get comprehensive dashboard statistics for the authenticated user.

    Includes match counts, score distribution, upcoming deadlines,
    and recent matches.
    """
    now = datetime.now(timezone.utc)
    one_day_ago = now - timedelta(days=1)
    one_week_ago = now - timedelta(days=7)

    # Base match query for this user
    user_matches = Match.user_id == current_user.id

    # Total matches count
    total_result = await db.execute(select(func.count(Match.id)).where(user_matches))
    total_matches = total_result.scalar() or 0

    # Saved grants count
    saved_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.user_action == "saved"))
    )
    saved_grants = saved_result.scalar() or 0

    # Dismissed grants count
    dismissed_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.user_action == "dismissed"))
    )
    dismissed_grants = dismissed_result.scalar() or 0

    # New matches today
    today_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.created_at >= one_day_ago))
    )
    new_matches_today = today_result.scalar() or 0

    # New matches this week
    week_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.created_at >= one_week_ago))
    )
    new_matches_week = week_result.scalar() or 0

    # Score distribution
    excellent_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.match_score >= 0.8))
    )
    excellent = excellent_result.scalar() or 0

    good_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.match_score >= 0.6, Match.match_score < 0.8))
    )
    good = good_result.scalar() or 0

    moderate_result = await db.execute(
        select(func.count(Match.id)).where(and_(user_matches, Match.match_score >= 0.4, Match.match_score < 0.6))
    )
    moderate = moderate_result.scalar() or 0

    low_result = await db.execute(select(func.count(Match.id)).where(and_(user_matches, Match.match_score < 0.4)))
    low = low_result.scalar() or 0

    score_distribution = MatchScoreDistribution(
        excellent=excellent,
        good=good,
        moderate=moderate,
        low=low,
    )

    # Average match score
    avg_result = await db.execute(select(func.avg(Match.match_score)).where(user_matches))
    average_match_score = avg_result.scalar()

    # Upcoming deadlines (next 30 days, not dismissed)
    thirty_days_from_now = now + timedelta(days=30)
    deadlines_result = await db.execute(
        select(Match)
        .options(joinedload(Match.grant))
        .where(
            and_(
                user_matches,
                or_(Match.user_action.is_(None), Match.user_action != "dismissed"),
            )
        )
        .join(Match.grant)
        .where(
            and_(
                Grant.deadline.is_not(None),
                Grant.deadline >= now,
                Grant.deadline <= thirty_days_from_now,
            )
        )
        .order_by(Grant.deadline.asc())
        .limit(10)
    )
    deadlines = deadlines_result.unique().scalars().all()

    upcoming_deadlines = [
        UpcomingDeadline(
            grant_id=m.grant.id,
            match_id=m.id,
            grant_title=m.grant.title,
            deadline=m.grant.deadline,
            match_score=m.match_score,
            days_remaining=(m.grant.deadline - now).days,
        )
        for m in deadlines
        if m.grant.deadline
    ]

    # Recent matches (last 10)
    recent_result = await db.execute(
        select(Match).options(joinedload(Match.grant)).where(user_matches).order_by(Match.created_at.desc()).limit(10)
    )
    recent = recent_result.unique().scalars().all()

    recent_matches = [
        RecentMatch(
            match_id=m.id,
            grant_id=m.grant.id,
            grant_title=m.grant.title,
            match_score=m.match_score,
            created_at=m.created_at,
            grant_agency=m.grant.agency,
        )
        for m in recent
    ]

    # Profile status
    profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    profile_complete = profile is not None
    profile_has_embedding = profile.profile_embedding is not None if profile else False

    return DashboardStats(
        total_matches=total_matches,
        saved_grants=saved_grants,
        dismissed_grants=dismissed_grants,
        new_matches_today=new_matches_today,
        new_matches_week=new_matches_week,
        score_distribution=score_distribution,
        average_match_score=float(average_match_score) if average_match_score else None,
        upcoming_deadlines=upcoming_deadlines,
        recent_matches=recent_matches,
        profile_complete=profile_complete,
        profile_has_embedding=profile_has_embedding,
    )
