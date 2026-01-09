"""
Workflow Analytics Service

Service layer for workflow analytics calculations including:
- Event tracking utilities
- Average time per stage calculation
- Bottleneck identification
- Completion rate tracking
- Deadline risk forecasting
- Caching for expensive calculations
"""
import logging
import uuid
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean, median
from typing import Any, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.models import ApplicationStage, Grant, GrantApplication, User
from backend.models.workflow_analytics import (
    WorkflowAnalytics,
    WorkflowEvent,
    WorkflowEventType,
    WorkflowStage,
)
from backend.schemas.workflow_analytics import (
    BottleneckInfo,
    BottlenecksResponse,
    CompletionRateMetrics,
    CompletionRatesResponse,
    DeadlineRiskApplication,
    DeadlineRiskForecastResponse,
    StageTimeMetrics,
    TimePerStageResponse,
    WorkflowAnalyticsResponse,
    WorkflowAnalyticsSummary,
    WorkflowEventCreate,
    WorkflowEventResponse,
    WorkflowEventsListResponse,
)
from backend.schemas.common import PaginationInfo
from backend.services.cache import (
    cache_key,
    get_cached,
    invalidate_user_cache,
    make_user_cache_key,
    set_cached,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Cache TTL Constants (in minutes)
# =============================================================================
CACHE_TTL_TIME_PER_STAGE = 5  # 5 minutes - data changes frequently
CACHE_TTL_BOTTLENECKS = 15  # 15 minutes - less frequent updates
CACHE_TTL_COMPLETION_RATES = 30  # 30 minutes - historical data, changes slowly
CACHE_TTL_SUMMARY = 10  # 10 minutes - aggregate of other metrics


# =============================================================================
# Event Tracking Utilities
# =============================================================================


async def track_workflow_event(
    db: AsyncSession,
    kanban_card_id: uuid.UUID,
    event_type: str,
    stage: Optional[str] = None,
    previous_stage: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    user_id: Optional[uuid.UUID] = None,
) -> WorkflowEvent:
    """
    Track a workflow event for a grant application.

    Args:
        db: Database session
        kanban_card_id: ID of the grant application
        event_type: Type of event (see WorkflowEventType)
        stage: Current stage (if applicable)
        previous_stage: Previous stage (for transitions)
        metadata: Additional event data
        user_id: User who triggered the event

    Returns:
        The created WorkflowEvent
    """
    event = WorkflowEvent(
        id=uuid.uuid4(),
        kanban_card_id=kanban_card_id,
        event_type=event_type,
        stage=stage,
        previous_stage=previous_stage,
        metadata_=metadata,
        user_id=user_id,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event


async def track_stage_transition(
    db: AsyncSession,
    kanban_card_id: uuid.UUID,
    new_stage: str,
    previous_stage: str,
    user_id: Optional[uuid.UUID] = None,
) -> tuple[WorkflowEvent, WorkflowEvent]:
    """
    Track a stage transition with both exit and enter events.

    Args:
        db: Database session
        kanban_card_id: ID of the grant application
        new_stage: New stage
        previous_stage: Previous stage
        user_id: User who triggered the transition

    Returns:
        Tuple of (exit_event, enter_event)
    """
    # Record stage exit
    exit_event = await track_workflow_event(
        db=db,
        kanban_card_id=kanban_card_id,
        event_type=WorkflowEventType.STAGE_EXIT,
        stage=previous_stage,
        previous_stage=None,
        metadata={"new_stage": new_stage},
        user_id=user_id,
    )

    # Record stage enter
    enter_event = await track_workflow_event(
        db=db,
        kanban_card_id=kanban_card_id,
        event_type=WorkflowEventType.STAGE_ENTER,
        stage=new_stage,
        previous_stage=previous_stage,
        metadata=None,
        user_id=user_id,
    )

    return exit_event, enter_event


async def get_application_events(
    db: AsyncSession,
    kanban_card_id: uuid.UUID,
    limit: int = 100,
    offset: int = 0,
) -> WorkflowEventsListResponse:
    """
    Get workflow events for a specific application.

    Args:
        db: Database session
        kanban_card_id: ID of the grant application
        limit: Maximum number of events to return
        offset: Number of events to skip

    Returns:
        List of workflow events
    """
    # Get total count
    count_result = await db.execute(
        select(func.count(WorkflowEvent.id)).where(
            WorkflowEvent.kanban_card_id == kanban_card_id
        )
    )
    total = count_result.scalar() or 0

    # Get events
    result = await db.execute(
        select(WorkflowEvent)
        .where(WorkflowEvent.kanban_card_id == kanban_card_id)
        .order_by(WorkflowEvent.occurred_at.desc())
        .limit(limit)
        .offset(offset)
    )
    events = result.scalars().all()

    has_more = (offset + len(events)) < total

    return WorkflowEventsListResponse(
        data=[
            WorkflowEventResponse(
                id=e.id,
                kanban_card_id=e.kanban_card_id,
                event_type=e.event_type,
                stage=e.stage,
                previous_stage=e.previous_stage,
                metadata=e.metadata_,
                user_id=e.user_id,
                occurred_at=e.occurred_at,
            )
            for e in events
        ],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )


# =============================================================================
# Time Per Stage Calculation
# =============================================================================


async def calculate_time_per_stage(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> TimePerStageResponse:
    """
    Calculate average time spent in each pipeline stage.

    Args:
        db: Database session
        user_id: User ID to analyze
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        Time metrics for each stage
    """
    # Default to last 90 days
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    # Get stage transition events for user's applications
    result = await db.execute(
        select(WorkflowEvent)
        .join(GrantApplication, WorkflowEvent.kanban_card_id == GrantApplication.id)
        .where(
            and_(
                GrantApplication.user_id == user_id,
                WorkflowEvent.event_type.in_([
                    WorkflowEventType.STAGE_ENTER,
                    WorkflowEventType.STAGE_EXIT,
                ]),
                WorkflowEvent.occurred_at >= datetime.combine(start_date, datetime.min.time()),
                WorkflowEvent.occurred_at <= datetime.combine(end_date, datetime.max.time()),
            )
        )
        .order_by(WorkflowEvent.kanban_card_id, WorkflowEvent.occurred_at)
    )
    events = result.scalars().all()

    # Group events by application
    app_events: dict[uuid.UUID, list[WorkflowEvent]] = defaultdict(list)
    for event in events:
        app_events[event.kanban_card_id].append(event)

    # Calculate time in each stage
    stage_times: dict[str, list[float]] = defaultdict(list)

    for app_id, app_event_list in app_events.items():
        stage_enter_times: dict[str, datetime] = {}

        for event in sorted(app_event_list, key=lambda e: e.occurred_at):
            if event.event_type == WorkflowEventType.STAGE_ENTER and event.stage:
                stage_enter_times[event.stage] = event.occurred_at
            elif event.event_type == WorkflowEventType.STAGE_EXIT and event.stage:
                if event.stage in stage_enter_times:
                    duration = event.occurred_at - stage_enter_times[event.stage]
                    hours = duration.total_seconds() / 3600
                    stage_times[event.stage].append(hours)
                    del stage_enter_times[event.stage]

    # Get current stage counts
    current_stage_result = await db.execute(
        select(GrantApplication.stage, func.count(GrantApplication.id))
        .where(GrantApplication.user_id == user_id)
        .group_by(GrantApplication.stage)
    )
    current_stage_counts = dict(current_stage_result.all())

    # Build stage metrics
    stages = []
    for stage in WorkflowStage.all_stages():
        times = stage_times.get(stage, [])
        currently_in = current_stage_counts.get(ApplicationStage(stage), 0) if stage in [s.value for s in ApplicationStage] else 0

        if times:
            stages.append(
                StageTimeMetrics(
                    stage=stage,
                    avg_hours=round(mean(times), 2),
                    median_hours=round(median(times), 2),
                    min_hours=round(min(times), 2),
                    max_hours=round(max(times), 2),
                    applications_count=len(times),
                    currently_in_stage=currently_in,
                )
            )
        else:
            stages.append(
                StageTimeMetrics(
                    stage=stage,
                    avg_hours=0,
                    median_hours=0,
                    min_hours=0,
                    max_hours=0,
                    applications_count=0,
                    currently_in_stage=currently_in,
                )
            )

    # Calculate total completion times
    completion_times = []
    for app_id, app_event_list in app_events.items():
        enter_events = [e for e in app_event_list if e.event_type == WorkflowEventType.STAGE_ENTER]
        exit_events = [e for e in app_event_list if e.event_type == WorkflowEventType.STAGE_EXIT]

        if enter_events and exit_events:
            first_enter = min(e.occurred_at for e in enter_events)
            last_exit = max(e.occurred_at for e in exit_events)
            duration = (last_exit - first_enter).total_seconds() / 3600
            completion_times.append(duration)

    return TimePerStageResponse(
        stages=stages,
        total_avg_time_hours=round(mean(completion_times), 2) if completion_times else 0,
        fastest_completion_hours=round(min(completion_times), 2) if completion_times else None,
        slowest_completion_hours=round(max(completion_times), 2) if completion_times else None,
    )


async def calculate_time_per_stage_cached(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> TimePerStageResponse:
    """
    Calculate average time spent in each pipeline stage with caching.

    Cached version of calculate_time_per_stage with 5-minute TTL.

    Args:
        db: Database session
        user_id: User ID to analyze
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        Time metrics for each stage (from cache if available)
    """
    # Build cache key
    cache_key_str = make_user_cache_key(
        str(user_id),
        f"time_per_stage:{start_date}:{end_date}"
    )

    # Check cache
    cached_result = get_cached(cache_key_str, CACHE_TTL_TIME_PER_STAGE)
    if cached_result is not None:
        logger.debug(f"Cache hit for time_per_stage for user {user_id}")
        return cached_result

    # Calculate and cache
    result = await calculate_time_per_stage(db, user_id, start_date, end_date)
    set_cached(cache_key_str, result)
    logger.debug(f"Cached time_per_stage for user {user_id}")
    return result


# =============================================================================
# Bottleneck Identification
# =============================================================================


# Expected hours per stage (configurable thresholds)
STAGE_TIME_THRESHOLDS = {
    WorkflowStage.RESEARCHING: 72,  # 3 days
    WorkflowStage.WRITING: 168,  # 7 days
    WorkflowStage.SUBMITTED: 720,  # 30 days (waiting for response)
}


async def identify_bottlenecks(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> BottlenecksResponse:
    """
    Identify workflow bottlenecks where applications are stuck.

    Args:
        db: Database session
        user_id: User ID to analyze

    Returns:
        Bottleneck analysis with recommendations
    """
    # Get active applications with their current stage and time in stage
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.user_id == user_id,
                GrantApplication.stage.in_([
                    ApplicationStage.RESEARCHING,
                    ApplicationStage.WRITING,
                    ApplicationStage.SUBMITTED,
                ]),
            )
        )
    )
    applications = result.unique().scalars().all()

    # Get last stage enter event for each application
    stage_entry_times: dict[uuid.UUID, datetime] = {}
    for app in applications:
        event_result = await db.execute(
            select(WorkflowEvent)
            .where(
                and_(
                    WorkflowEvent.kanban_card_id == app.id,
                    WorkflowEvent.event_type == WorkflowEventType.STAGE_ENTER,
                    WorkflowEvent.stage == app.stage.value,
                )
            )
            .order_by(WorkflowEvent.occurred_at.desc())
            .limit(1)
        )
        event = event_result.scalar_one_or_none()
        if event:
            stage_entry_times[app.id] = event.occurred_at
        else:
            # Use created_at or updated_at as fallback
            stage_entry_times[app.id] = app.updated_at or app.created_at

    # Analyze each stage
    bottlenecks = []
    total_at_risk = 0
    now = datetime.now(timezone.utc)

    for stage_name in WorkflowStage.active_stages():
        stage_enum = ApplicationStage(stage_name)
        stage_apps = [app for app in applications if app.stage == stage_enum]

        if not stage_apps:
            continue

        threshold_hours = STAGE_TIME_THRESHOLDS.get(stage_name, 168)

        # Calculate time in stage for each application
        times_in_stage = []
        stuck_count = 0

        for app in stage_apps:
            entry_time = stage_entry_times.get(app.id, app.created_at)
            if entry_time.tzinfo is None:
                entry_time = entry_time.replace(tzinfo=timezone.utc)
            hours_in_stage = (now - entry_time).total_seconds() / 3600
            times_in_stage.append(hours_in_stage)

            if hours_in_stage > threshold_hours:
                stuck_count += 1

        if not times_in_stage:
            continue

        avg_wait = mean(times_in_stage)
        pct_above = (stuck_count / len(times_in_stage)) * 100

        # Determine severity
        if pct_above >= 50:
            severity = "critical"
            total_at_risk += stuck_count
        elif pct_above >= 25:
            severity = "high"
            total_at_risk += stuck_count
        elif pct_above >= 10:
            severity = "medium"
        else:
            severity = "low"

        # Generate recommendation
        recommendations = {
            WorkflowStage.RESEARCHING: "Consider setting deadlines for initial research. Break down research into smaller tasks.",
            WorkflowStage.WRITING: "Review writing process. Consider using templates or AI assistance. Set intermediate milestones.",
            WorkflowStage.SUBMITTED: "Follow up on application status. Check submission portal for updates.",
        }

        if pct_above > 0 or severity in ["medium", "high", "critical"]:
            bottlenecks.append(
                BottleneckInfo(
                    stage=stage_name,
                    severity=severity,
                    avg_wait_hours=round(avg_wait, 2),
                    applications_stuck=stuck_count,
                    pct_above_threshold=round(pct_above, 1),
                    recommendation=recommendations.get(stage_name, "Review workflow for this stage."),
                )
            )

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    bottlenecks.sort(key=lambda b: severity_order.get(b.severity, 4))

    # Determine overall health
    if any(b.severity == "critical" for b in bottlenecks):
        overall_health = "critical"
    elif any(b.severity == "high" for b in bottlenecks):
        overall_health = "warning"
    else:
        overall_health = "healthy"

    return BottlenecksResponse(
        bottlenecks=bottlenecks,
        total_at_risk=total_at_risk,
        overall_health=overall_health,
    )


async def identify_bottlenecks_cached(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> BottlenecksResponse:
    """
    Identify workflow bottlenecks with caching.

    Cached version of identify_bottlenecks with 15-minute TTL.

    Args:
        db: Database session
        user_id: User ID to analyze

    Returns:
        Bottleneck analysis with recommendations (from cache if available)
    """
    # Build cache key
    cache_key_str = make_user_cache_key(str(user_id), "bottlenecks")

    # Check cache
    cached_result = get_cached(cache_key_str, CACHE_TTL_BOTTLENECKS)
    if cached_result is not None:
        logger.debug(f"Cache hit for bottlenecks for user {user_id}")
        return cached_result

    # Calculate and cache
    result = await identify_bottlenecks(db, user_id)
    set_cached(cache_key_str, result)
    logger.debug(f"Cached bottlenecks for user {user_id}")
    return result


# =============================================================================
# Completion Rate Tracking
# =============================================================================


async def calculate_completion_rates(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_type: str = "monthly",
    periods: int = 6,
) -> CompletionRatesResponse:
    """
    Calculate completion rates over time.

    Args:
        db: Database session
        user_id: User ID to analyze
        period_type: 'monthly' or 'quarterly'
        periods: Number of periods to analyze

    Returns:
        Completion rate metrics by period
    """
    # Get all applications with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == user_id)
        .order_by(GrantApplication.created_at)
    )
    applications = result.unique().scalars().all()

    if not applications:
        return CompletionRatesResponse(
            periods=[],
            overall_submission_rate=0,
            overall_success_rate=0,
            trend="stable",
        )

    # Group by period
    def get_period_key(dt: datetime) -> str:
        if period_type == "quarterly":
            quarter = (dt.month - 1) // 3 + 1
            return f"{dt.year}-Q{quarter}"
        else:  # monthly
            return dt.strftime("%Y-%m")

    period_data: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total_started": 0,
            "submitted": 0,
            "awarded": 0,
            "rejected": 0,
            "in_progress": 0,
        }
    )

    for app in applications:
        period = get_period_key(app.created_at)
        period_data[period]["total_started"] += 1

        if app.stage == ApplicationStage.SUBMITTED:
            period_data[period]["submitted"] += 1
            period_data[period]["in_progress"] += 1  # Still waiting
        elif app.stage == ApplicationStage.AWARDED:
            period_data[period]["submitted"] += 1
            period_data[period]["awarded"] += 1
        elif app.stage == ApplicationStage.REJECTED:
            period_data[period]["submitted"] += 1
            period_data[period]["rejected"] += 1
        else:
            period_data[period]["in_progress"] += 1

    # Build period metrics
    sorted_periods = sorted(period_data.keys())[-periods:]
    period_metrics = []

    for p in sorted_periods:
        data = period_data[p]
        total = data["total_started"]
        submitted = data["submitted"]
        awarded = data["awarded"]

        submission_rate = (submitted / total * 100) if total > 0 else 0
        success_rate = (awarded / submitted * 100) if submitted > 0 else 0

        period_metrics.append(
            CompletionRateMetrics(
                period=p,
                total_started=total,
                submitted=submitted,
                awarded=awarded,
                rejected=data["rejected"],
                in_progress=data["in_progress"],
                submission_rate=round(submission_rate, 1),
                success_rate=round(success_rate, 1),
            )
        )

    # Calculate overall rates
    total_all = sum(data["total_started"] for data in period_data.values())
    submitted_all = sum(data["submitted"] for data in period_data.values())
    awarded_all = sum(data["awarded"] for data in period_data.values())

    overall_submission = (submitted_all / total_all * 100) if total_all > 0 else 0
    overall_success = (awarded_all / submitted_all * 100) if submitted_all > 0 else 0

    # Determine trend
    if len(period_metrics) >= 2:
        recent_rate = period_metrics[-1].success_rate
        older_rate = period_metrics[-2].success_rate
        if recent_rate > older_rate + 5:
            trend = "improving"
        elif recent_rate < older_rate - 5:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    return CompletionRatesResponse(
        periods=period_metrics,
        overall_submission_rate=round(overall_submission, 1),
        overall_success_rate=round(overall_success, 1),
        trend=trend,
    )


async def calculate_completion_rates_cached(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_type: str = "monthly",
    periods: int = 6,
) -> CompletionRatesResponse:
    """
    Calculate completion rates over time with caching.

    Cached version of calculate_completion_rates with 30-minute TTL.

    Args:
        db: Database session
        user_id: User ID to analyze
        period_type: 'monthly' or 'quarterly'
        periods: Number of periods to analyze

    Returns:
        Completion rate metrics by period (from cache if available)
    """
    # Build cache key
    cache_key_str = make_user_cache_key(
        str(user_id),
        f"completion_rates:{period_type}:{periods}"
    )

    # Check cache
    cached_result = get_cached(cache_key_str, CACHE_TTL_COMPLETION_RATES)
    if cached_result is not None:
        logger.debug(f"Cache hit for completion_rates for user {user_id}")
        return cached_result

    # Calculate and cache
    result = await calculate_completion_rates(db, user_id, period_type, periods)
    set_cached(cache_key_str, result)
    logger.debug(f"Cached completion_rates for user {user_id}")
    return result


# =============================================================================
# Deadline Risk Forecasting
# =============================================================================


async def forecast_deadline_risks(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> DeadlineRiskForecastResponse:
    """
    Forecast deadline risks based on historical performance.

    Args:
        db: Database session
        user_id: User ID to analyze

    Returns:
        Deadline risk assessment for active applications
    """
    # Get time per stage for estimation
    time_per_stage = await calculate_time_per_stage(db, user_id)
    stage_avg_hours = {s.stage: s.avg_hours for s in time_per_stage.stages}

    # Get active applications with deadlines
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.user_id == user_id,
                GrantApplication.stage.in_([
                    ApplicationStage.RESEARCHING,
                    ApplicationStage.WRITING,
                    ApplicationStage.SUBMITTED,
                ]),
            )
        )
    )
    applications = result.unique().scalars().all()

    at_risk_applications = []
    risk_counts = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    now = datetime.now(timezone.utc)

    for app in applications:
        deadline = app.grant.deadline if app.grant else None
        if deadline and deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        # Calculate estimated days to complete
        current_stage = app.stage.value
        remaining_stages = []

        if current_stage == WorkflowStage.RESEARCHING:
            remaining_stages = [WorkflowStage.RESEARCHING, WorkflowStage.WRITING]
        elif current_stage == WorkflowStage.WRITING:
            remaining_stages = [WorkflowStage.WRITING]
        # Submitted stage has no remaining work

        estimated_hours = sum(stage_avg_hours.get(s, 48) for s in remaining_stages)
        estimated_days = estimated_hours / 24

        # Calculate risk
        days_until_deadline = None
        risk_level = "low"
        risk_score = 0

        if deadline:
            time_diff = deadline - now
            days_until_deadline = time_diff.days

            if days_until_deadline < 0:
                risk_level = "critical"
                risk_score = 100
            elif days_until_deadline < estimated_days:
                risk_level = "critical"
                risk_score = 95
            elif days_until_deadline < estimated_days * 1.5:
                risk_level = "high"
                risk_score = 75
            elif days_until_deadline < estimated_days * 2:
                risk_level = "medium"
                risk_score = 50
            else:
                risk_level = "low"
                risk_score = max(0, 25 - (days_until_deadline - estimated_days * 2))

        risk_counts[risk_level] += 1

        # Generate recommendations
        recommendations = []
        if risk_level == "critical":
            recommendations.append("Immediate action required to meet deadline")
            if current_stage == WorkflowStage.RESEARCHING:
                recommendations.append("Consider fast-tracking to writing stage")
        elif risk_level == "high":
            recommendations.append("Prioritize this application")
            recommendations.append("Review timeline and adjust if needed")
        elif risk_level == "medium":
            recommendations.append("Monitor progress closely")

        # Only include at-risk applications (medium or higher)
        if risk_level in ["medium", "high", "critical"]:
            at_risk_applications.append(
                DeadlineRiskApplication(
                    application_id=app.id,
                    grant_title=app.grant.title if app.grant else "Unknown Grant",
                    current_stage=current_stage,
                    deadline=deadline,
                    days_until_deadline=days_until_deadline,
                    estimated_days_to_complete=round(estimated_days, 1),
                    risk_level=risk_level,
                    risk_score=round(risk_score, 1),
                    recommended_actions=recommendations,
                )
            )

    # Sort by risk score descending
    at_risk_applications.sort(key=lambda a: -a.risk_score)

    return DeadlineRiskForecastResponse(
        at_risk_applications=at_risk_applications,
        total_applications=len(applications),
        low_risk_count=risk_counts["low"],
        medium_risk_count=risk_counts["medium"],
        high_risk_count=risk_counts["high"],
        critical_risk_count=risk_counts["critical"],
    )


# =============================================================================
# Complete Analytics Summary
# =============================================================================


async def get_workflow_analytics_summary(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> WorkflowAnalyticsResponse:
    """
    Get complete workflow analytics summary.

    Args:
        db: Database session
        user_id: User ID to analyze
        start_date: Start of analysis period
        end_date: End of analysis period

    Returns:
        Complete workflow analytics response
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=90)

    # Get all components
    time_per_stage = await calculate_time_per_stage(db, user_id, start_date, end_date)
    bottlenecks = await identify_bottlenecks(db, user_id)
    deadline_risks = await forecast_deadline_risks(db, user_id)
    completion_rates = await calculate_completion_rates(db, user_id)

    # Get application counts
    result = await db.execute(
        select(GrantApplication.stage, func.count(GrantApplication.id))
        .where(GrantApplication.user_id == user_id)
        .group_by(GrantApplication.stage)
    )
    stage_counts = dict(result.all())

    total_applications = sum(stage_counts.values())
    active_applications = sum(
        count for stage, count in stage_counts.items()
        if stage in [ApplicationStage.RESEARCHING, ApplicationStage.WRITING, ApplicationStage.SUBMITTED]
    )
    completed_applications = sum(
        count for stage, count in stage_counts.items()
        if stage in [ApplicationStage.AWARDED, ApplicationStage.REJECTED]
    )

    # Build summary
    summary = WorkflowAnalyticsSummary(
        total_applications=total_applications,
        active_applications=active_applications,
        completed_applications=completed_applications,
        avg_completion_time_days=time_per_stage.total_avg_time_hours / 24 if time_per_stage.total_avg_time_hours else None,
        submission_rate=completion_rates.overall_submission_rate,
        success_rate=completion_rates.overall_success_rate,
        current_bottleneck=bottlenecks.bottlenecks[0].stage if bottlenecks.bottlenecks else None,
        at_risk_count=deadline_risks.high_risk_count + deadline_risks.critical_risk_count,
        workflow_health=bottlenecks.overall_health,
    )

    return WorkflowAnalyticsResponse(
        summary=summary,
        time_per_stage=time_per_stage,
        bottlenecks=bottlenecks,
        deadline_risks=deadline_risks,
        period_start=start_date,
        period_end=end_date,
        generated_at=datetime.now(timezone.utc),
    )


# =============================================================================
# Store Analytics
# =============================================================================


async def store_workflow_analytics(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
    period_type: str,
    metrics: dict[str, Any],
) -> WorkflowAnalytics:
    """
    Store computed workflow analytics.

    Args:
        db: Database session
        user_id: User ID
        period_start: Start of period
        period_end: End of period
        period_type: Type of period (daily, weekly, monthly)
        metrics: Computed metrics as dict

    Returns:
        The created or updated WorkflowAnalytics record
    """
    # Check for existing record
    result = await db.execute(
        select(WorkflowAnalytics).where(
            and_(
                WorkflowAnalytics.user_id == user_id,
                WorkflowAnalytics.period_start == period_start,
                WorkflowAnalytics.period_end == period_end,
                WorkflowAnalytics.period_type == period_type,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.metrics = metrics
        existing.generated_at = datetime.now(timezone.utc)
        await db.flush()
        return existing

    analytics = WorkflowAnalytics(
        id=uuid.uuid4(),
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        period_type=period_type,
        metrics=metrics,
        generated_at=datetime.now(timezone.utc),
    )
    db.add(analytics)
    await db.flush()
    return analytics


# =============================================================================
# Cache Invalidation
# =============================================================================


def invalidate_user_analytics_cache(user_id: str) -> int:
    """
    Invalidate all analytics cache entries for a specific user.

    Should be called when:
    - A new workflow event is recorded
    - Application status changes
    - User data is updated that affects analytics

    Args:
        user_id: UUID of the user (as string)

    Returns:
        Number of cache entries invalidated
    """
    count = invalidate_user_cache(user_id)
    if count > 0:
        logger.info(f"Invalidated {count} analytics cache entries for user {user_id}")
    return count


async def invalidate_and_refresh_cache(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """
    Invalidate cache and pre-warm with fresh data.

    Useful after significant events to ensure fresh data is immediately available.

    Args:
        db: Database session
        user_id: User ID
    """
    # Invalidate existing cache
    invalidate_user_analytics_cache(str(user_id))

    # Pre-warm cache with fresh calculations
    try:
        await calculate_time_per_stage_cached(db, user_id)
        await identify_bottlenecks_cached(db, user_id)
        await calculate_completion_rates_cached(db, user_id)
        logger.info(f"Pre-warmed analytics cache for user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to pre-warm cache for user {user_id}: {e}")


__all__ = [
    # Event tracking
    "track_workflow_event",
    "track_stage_transition",
    "get_application_events",
    # Analytics calculations (uncached)
    "calculate_time_per_stage",
    "identify_bottlenecks",
    "calculate_completion_rates",
    "forecast_deadline_risks",
    "get_workflow_analytics_summary",
    # Analytics calculations (cached)
    "calculate_time_per_stage_cached",
    "identify_bottlenecks_cached",
    "calculate_completion_rates_cached",
    # Storage
    "store_workflow_analytics",
    # Cache management
    "invalidate_user_analytics_cache",
    "invalidate_and_refresh_cache",
    # Cache TTL constants
    "CACHE_TTL_TIME_PER_STAGE",
    "CACHE_TTL_BOTTLENECKS",
    "CACHE_TTL_COMPLETION_RATES",
    "CACHE_TTL_SUMMARY",
]
