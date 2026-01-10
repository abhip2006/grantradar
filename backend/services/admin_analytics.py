"""
Admin Analytics Service
Query logic for platform-wide admin analytics with caching support.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    ChatMessage,
    ChatSession,
    Grant,
    GrantApplication,
    LabMember,
    Match,
    ResearchSession,
    TeamComment,
    User,
)
from backend.schemas.admin_analytics import (
    AIUsageResponse,
    ApplicationsByStatus,
    DailyActiveUsers,
    DailyChatSessions,
    DailyComments,
    DailySignup,
    GrantAnalyticsResponse,
    GrantsByAgency,
    GrantsBySource,
    MatchScoreBucket,
    PlatformOverviewResponse,
    TeamAnalyticsResponse,
    TopUserByActivity,
    UserAnalyticsResponse,
)
from backend.services.cache import cache_key, get_cached, set_cached

logger = logging.getLogger(__name__)

# Cache TTL in minutes (1 hour for admin analytics)
ADMIN_ANALYTICS_CACHE_TTL = 60


# =============================================================================
# Platform Overview
# =============================================================================


async def get_platform_overview(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> PlatformOverviewResponse:
    """
    Get platform-wide overview metrics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        PlatformOverviewResponse with aggregate metrics
    """
    # Generate cache key
    key = f"admin_analytics:overview:{cache_key(str(start_date), str(end_date))}"
    cached_result = get_cached(key, ADMIN_ANALYTICS_CACHE_TTL)
    if cached_result:
        return PlatformOverviewResponse(**cached_result)

    now = datetime.now(timezone.utc)
    yesterday = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    # Total users
    total_users_result = await db.execute(select(func.count(User.id)))
    total_users = total_users_result.scalar() or 0

    # Active users in last 24 hours (based on chat sessions or research sessions)
    active_24h_query = select(func.count(distinct(ChatSession.user_id))).where(ChatSession.updated_at >= yesterday)
    active_24h_result = await db.execute(active_24h_query)
    active_users_24h = active_24h_result.scalar() or 0

    # Active users in last 7 days
    active_7d_query = select(func.count(distinct(ChatSession.user_id))).where(ChatSession.updated_at >= week_ago)
    active_7d_result = await db.execute(active_7d_query)
    active_users_7d = active_7d_result.scalar() or 0

    # Total grants
    total_grants_result = await db.execute(select(func.count(Grant.id)))
    total_grants = total_grants_result.scalar() or 0

    # Total applications
    total_apps_result = await db.execute(select(func.count(GrantApplication.id)))
    total_applications = total_apps_result.scalar() or 0

    # AI requests today (chat messages + research sessions created today)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    chat_today_query = select(func.count(ChatMessage.id)).where(ChatMessage.created_at >= today_start)
    chat_today_result = await db.execute(chat_today_query)
    chat_today = chat_today_result.scalar() or 0

    research_today_query = select(func.count(ResearchSession.id)).where(ResearchSession.created_at >= today_start)
    research_today_result = await db.execute(research_today_query)
    research_today = research_today_result.scalar() or 0

    ai_requests_today = chat_today + research_today

    result = PlatformOverviewResponse(
        total_users=total_users,
        active_users_24h=active_users_24h,
        active_users_7d=active_users_7d,
        total_grants=total_grants,
        total_applications=total_applications,
        ai_requests_today=ai_requests_today,
    )

    # Cache result
    set_cached(key, result.model_dump())
    return result


# =============================================================================
# User Analytics
# =============================================================================


async def get_user_analytics(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: int = 30,
) -> UserAnalyticsResponse:
    """
    Get user growth and engagement metrics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter
        days: Number of days to look back for daily metrics

    Returns:
        UserAnalyticsResponse with user analytics
    """
    key = f"admin_analytics:users:{cache_key(str(start_date), str(end_date), days)}"
    cached_result = get_cached(key, ADMIN_ANALYTICS_CACHE_TTL)
    if cached_result:
        return UserAnalyticsResponse(**cached_result)

    now = datetime.now(timezone.utc)
    cutoff_date = start_date or (now - timedelta(days=days))
    end = end_date or now

    # Daily signups
    signups_query = (
        select(
            func.date(User.created_at).label("date"),
            func.count(User.id).label("count"),
        )
        .where(and_(User.created_at >= cutoff_date, User.created_at <= end))
        .group_by(func.date(User.created_at))
        .order_by(func.date(User.created_at))
    )
    signups_result = await db.execute(signups_query)
    signups_by_day = [DailySignup(date=str(row.date), count=row.count) for row in signups_result.fetchall()]

    # Daily active users (based on chat session activity)
    active_query = (
        select(
            func.date(ChatSession.updated_at).label("date"),
            func.count(distinct(ChatSession.user_id)).label("count"),
        )
        .where(and_(ChatSession.updated_at >= cutoff_date, ChatSession.updated_at <= end))
        .group_by(func.date(ChatSession.updated_at))
        .order_by(func.date(ChatSession.updated_at))
    )
    active_result = await db.execute(active_query)
    active_users_by_day = [DailyActiveUsers(date=str(row.date), count=row.count) for row in active_result.fetchall()]

    # Retention rate (users who signed up 7+ days ago and were active in last 7 days)
    week_ago = now - timedelta(days=7)
    now - timedelta(days=14)

    # Users who signed up more than 7 days ago
    eligible_users_query = select(func.count(User.id)).where(User.created_at <= week_ago)
    eligible_result = await db.execute(eligible_users_query)
    eligible_users = eligible_result.scalar() or 0

    # Of those, how many were active in the last 7 days
    retained_query = (
        select(func.count(distinct(ChatSession.user_id)))
        .join(User, ChatSession.user_id == User.id)
        .where(
            and_(
                User.created_at <= week_ago,
                ChatSession.updated_at >= week_ago,
            )
        )
    )
    retained_result = await db.execute(retained_query)
    retained_users = retained_result.scalar() or 0

    retention_rate = round((retained_users / eligible_users) * 100, 1) if eligible_users > 0 else 0.0

    # Top users by activity (chat messages + applications)
    activity_query = (
        select(
            User.id,
            User.email,
            User.name,
            (
                func.coalesce(func.count(distinct(ChatSession.id)), 0)
                + func.coalesce(func.count(distinct(GrantApplication.id)), 0)
            ).label("activity_score"),
            func.max(ChatSession.updated_at).label("last_active"),
        )
        .outerjoin(ChatSession, User.id == ChatSession.user_id)
        .outerjoin(GrantApplication, User.id == GrantApplication.user_id)
        .group_by(User.id, User.email, User.name)
        .order_by(
            (
                func.coalesce(func.count(distinct(ChatSession.id)), 0)
                + func.coalesce(func.count(distinct(GrantApplication.id)), 0)
            ).desc()
        )
        .limit(10)
    )
    activity_result = await db.execute(activity_query)
    top_users_by_activity = [
        TopUserByActivity(
            user_id=str(row.id),
            email=row.email,
            name=row.name,
            activity_score=row.activity_score,
            last_active=row.last_active,
        )
        for row in activity_result.fetchall()
    ]

    result = UserAnalyticsResponse(
        signups_by_day=signups_by_day,
        active_users_by_day=active_users_by_day,
        retention_rate=retention_rate,
        top_users_by_activity=top_users_by_activity,
    )

    set_cached(key, result.model_dump())
    return result


# =============================================================================
# AI Usage Analytics
# =============================================================================


async def get_ai_usage(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: int = 30,
) -> AIUsageResponse:
    """
    Get AI feature usage metrics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter
        days: Number of days to look back

    Returns:
        AIUsageResponse with AI usage metrics
    """
    key = f"admin_analytics:ai_usage:{cache_key(str(start_date), str(end_date), days)}"
    cached_result = get_cached(key, ADMIN_ANALYTICS_CACHE_TTL)
    if cached_result:
        return AIUsageResponse(**cached_result)

    now = datetime.now(timezone.utc)
    cutoff_date = start_date or (now - timedelta(days=days))
    end = end_date or now

    # Daily chat sessions
    chat_sessions_query = (
        select(
            func.date(ChatSession.created_at).label("date"),
            func.count(ChatSession.id).label("count"),
        )
        .where(and_(ChatSession.created_at >= cutoff_date, ChatSession.created_at <= end))
        .group_by(func.date(ChatSession.created_at))
        .order_by(func.date(ChatSession.created_at))
    )
    chat_sessions_result = await db.execute(chat_sessions_query)
    chat_sessions_by_day = [
        DailyChatSessions(date=str(row.date), count=row.count) for row in chat_sessions_result.fetchall()
    ]

    # Total insights generated (eligibility chat sessions)
    insights_query = select(func.count(ChatSession.id)).where(ChatSession.session_type == "eligibility")
    insights_result = await db.execute(insights_query)
    insights_generated = insights_result.scalar() or 0

    # Writing analyses (chat sessions of type 'writing' if it exists, or estimate from sessions)
    writing_query = select(func.count(ChatSession.id)).where(ChatSession.session_type.in_(["writing", "analysis"]))
    writing_result = await db.execute(writing_query)
    writing_analyses = writing_result.scalar() or 0

    # Research sessions
    research_query = select(func.count(ResearchSession.id))
    research_result = await db.execute(research_query)
    research_sessions = research_result.scalar() or 0

    # Estimate tokens used (rough estimate: avg 500 tokens per message)
    messages_query = select(func.count(ChatMessage.id))
    messages_result = await db.execute(messages_query)
    total_messages = messages_result.scalar() or 0
    tokens_used_estimate = total_messages * 500  # Rough estimate

    result = AIUsageResponse(
        chat_sessions_by_day=chat_sessions_by_day,
        insights_generated=insights_generated,
        writing_analyses=writing_analyses,
        research_sessions=research_sessions,
        tokens_used_estimate=tokens_used_estimate,
    )

    set_cached(key, result.model_dump())
    return result


# =============================================================================
# Grant Analytics
# =============================================================================


async def get_grant_analytics(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> GrantAnalyticsResponse:
    """
    Get grant discovery and application metrics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter

    Returns:
        GrantAnalyticsResponse with grant metrics
    """
    key = f"admin_analytics:grants:{cache_key(str(start_date), str(end_date))}"
    cached_result = get_cached(key, ADMIN_ANALYTICS_CACHE_TTL)
    if cached_result:
        return GrantAnalyticsResponse(**cached_result)

    # Grants by source
    source_query = (
        select(Grant.source, func.count(Grant.id).label("count"))
        .group_by(Grant.source)
        .order_by(func.count(Grant.id).desc())
    )
    source_result = await db.execute(source_query)
    grants_by_source = [
        GrantsBySource(source=row.source or "unknown", count=row.count) for row in source_result.fetchall()
    ]

    # Grants by agency (top 10)
    agency_query = (
        select(Grant.agency, func.count(Grant.id).label("count"))
        .where(Grant.agency.isnot(None))
        .group_by(Grant.agency)
        .order_by(func.count(Grant.id).desc())
        .limit(10)
    )
    agency_result = await db.execute(agency_query)
    grants_by_agency = [GrantsByAgency(agency=row.agency, count=row.count) for row in agency_result.fetchall()]

    # Applications by status
    status_query = (
        select(GrantApplication.stage, func.count(GrantApplication.id).label("count"))
        .group_by(GrantApplication.stage)
        .order_by(func.count(GrantApplication.id).desc())
    )
    status_result = await db.execute(status_query)
    applications_by_status = [
        ApplicationsByStatus(status=row.stage.value if hasattr(row.stage, "value") else str(row.stage), count=row.count)
        for row in status_result.fetchall()
    ]

    # Match score distribution
    score_ranges = [
        ("0-20%", 0.0, 0.2),
        ("20-40%", 0.2, 0.4),
        ("40-60%", 0.4, 0.6),
        ("60-80%", 0.6, 0.8),
        ("80-100%", 0.8, 1.0),
    ]

    match_score_distribution = []
    for label, min_score, max_score in score_ranges:
        count_query = select(func.count(Match.id)).where(
            and_(Match.score >= min_score, Match.score < max_score)
            if max_score < 1.0
            else and_(Match.score >= min_score, Match.score <= max_score)
        )
        count_result = await db.execute(count_query)
        count = count_result.scalar() or 0
        match_score_distribution.append(
            MatchScoreBucket(
                range_label=label,
                min_score=min_score,
                max_score=max_score,
                count=count,
            )
        )

    result = GrantAnalyticsResponse(
        grants_by_source=grants_by_source,
        grants_by_agency=grants_by_agency,
        applications_by_status=applications_by_status,
        match_score_distribution=match_score_distribution,
    )

    set_cached(key, result.model_dump())
    return result


# =============================================================================
# Team Analytics
# =============================================================================


async def get_team_analytics(
    db: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    days: int = 30,
) -> TeamAnalyticsResponse:
    """
    Get team collaboration metrics.

    Args:
        db: Database session
        start_date: Optional start date filter
        end_date: Optional end date filter
        days: Number of days to look back for daily metrics

    Returns:
        TeamAnalyticsResponse with team metrics
    """
    key = f"admin_analytics:teams:{cache_key(str(start_date), str(end_date), days)}"
    cached_result = get_cached(key, ADMIN_ANALYTICS_CACHE_TTL)
    if cached_result:
        return TeamAnalyticsResponse(**cached_result)

    now = datetime.now(timezone.utc)
    cutoff_date = start_date or (now - timedelta(days=days))
    end = end_date or now
    week_ago = now - timedelta(days=7)

    # Total teams (distinct lab owners with members)
    teams_query = select(func.count(distinct(LabMember.lab_owner_id)))
    teams_result = await db.execute(teams_query)
    total_teams = teams_result.scalar() or 0

    # Average team size
    if total_teams > 0:
        total_members_query = select(func.count(LabMember.id)).where(LabMember.invitation_status == "accepted")
        total_members_result = await db.execute(total_members_query)
        total_members = total_members_result.scalar() or 0
        avg_team_size = round(total_members / total_teams, 1) if total_teams > 0 else 0.0
    else:
        avg_team_size = 0.0

    # Active collaborations (teams with activity in last 7 days)
    active_collab_query = select(func.count(distinct(TeamComment.lab_owner_id))).where(
        TeamComment.created_at >= week_ago
    )
    active_collab_result = await db.execute(active_collab_query)
    active_collaborations = active_collab_result.scalar() or 0

    # Daily comments
    comments_query = (
        select(
            func.date(TeamComment.created_at).label("date"),
            func.count(TeamComment.id).label("count"),
        )
        .where(and_(TeamComment.created_at >= cutoff_date, TeamComment.created_at <= end))
        .group_by(func.date(TeamComment.created_at))
        .order_by(func.date(TeamComment.created_at))
    )
    comments_result = await db.execute(comments_query)
    comments_per_day = [DailyComments(date=str(row.date), count=row.count) for row in comments_result.fetchall()]

    result = TeamAnalyticsResponse(
        total_teams=total_teams,
        avg_team_size=avg_team_size,
        active_collaborations=active_collaborations,
        comments_per_day=comments_per_day,
    )

    set_cached(key, result.model_dump())
    return result


# =============================================================================
# Cache Invalidation
# =============================================================================


def invalidate_admin_analytics_cache() -> int:
    """
    Invalidate all admin analytics cache entries.

    Returns:
        Number of cache entries invalidated
    """
    from backend.services.cache import invalidate_by_prefix

    return invalidate_by_prefix("admin_analytics:")
