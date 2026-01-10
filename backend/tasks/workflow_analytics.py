"""
Workflow Analytics Celery Tasks

Celery tasks for periodic workflow analytics aggregation and event processing.

Tasks:
    - aggregate_workflow_analytics: Compute and store analytics for all users (daily)
    - compute_user_workflow_analytics: Compute analytics for a specific user
    - cleanup_old_workflow_events: Archive or delete old events
"""

import json
import logging
from datetime import date, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.celery_app import celery_app, normal_task
from backend.core.config import settings
from backend.database import get_sync_db
from backend.models import GrantApplication, User
from backend.models.workflow_analytics import WorkflowAnalytics, WorkflowEvent, WorkflowStage

logger = logging.getLogger(__name__)

# Redis client for caching
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

# Cache TTL
CACHE_TTL_WORKFLOW_ANALYTICS = 6 * 60 * 60  # 6 hours


# =============================================================================
# Helper Functions
# =============================================================================


def _cache_key(prefix: str, identifier: str = "") -> str:
    """Generate a consistent cache key for workflow analytics data."""
    if identifier:
        return f"workflow_analytics:{prefix}:{identifier}"
    return f"workflow_analytics:{prefix}"


def _store_in_cache(key: str, data: dict[str, Any], ttl: int) -> None:
    """Store analytics data in Redis cache with TTL."""
    try:
        redis_client.setex(key, ttl, json.dumps(data, default=str))
        logger.debug(f"Cached workflow analytics data: {key} (TTL: {ttl}s)")
    except Exception as e:
        logger.warning(f"Failed to cache workflow analytics data: {e}")


def _get_from_cache(key: str) -> Optional[dict[str, Any]]:
    """Retrieve analytics data from Redis cache."""
    try:
        cached = redis_client.get(key)
        if cached:
            return json.loads(cached)
    except Exception as e:
        logger.warning(f"Failed to retrieve cached workflow analytics: {e}")
    return None


def _calculate_percentage(numerator: int, denominator: int) -> float:
    """Safely calculate percentage, handling division by zero."""
    if denominator == 0:
        return 0.0
    return round((numerator / denominator) * 100, 2)


# =============================================================================
# Main Aggregation Task
# =============================================================================


@normal_task
@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.aggregate_workflow_analytics")
def aggregate_workflow_analytics(self) -> dict[str, Any]:
    """
    Aggregate workflow analytics for all users.

    Scheduled to run daily via Celery Beat. Computes:
    - Time per stage metrics
    - Bottleneck identification
    - Completion rates
    - Success patterns

    Results are stored in workflow_analytics table and cached in Redis.

    Returns:
        dict: Summary of aggregation results
    """
    logger.info("Starting workflow analytics aggregation for all users")
    db: Session = get_sync_db()

    try:
        # Get all users with applications
        users_result = db.execute(
            select(User.id).distinct().join(GrantApplication, User.id == GrantApplication.user_id)
        )
        user_ids = [row[0] for row in users_result.all()]

        logger.info(f"Found {len(user_ids)} users with applications")

        # Define analysis period
        end_date = date.today()
        start_date = end_date - timedelta(days=30)  # Last 30 days

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "period": f"{start_date} to {end_date}",
            "users_processed": 0,
            "users_succeeded": 0,
            "users_failed": 0,
            "errors": [],
        }

        for user_id in user_ids:
            try:
                # Compute analytics for this user (sync version)
                metrics = _compute_user_metrics_sync(db, user_id, start_date, end_date)

                # Store in database
                _store_analytics_sync(
                    db=db,
                    user_id=user_id,
                    period_start=start_date,
                    period_end=end_date,
                    period_type="weekly",
                    metrics=metrics,
                )

                # Cache the results
                cache_key = _cache_key("user", str(user_id))
                _store_in_cache(cache_key, metrics, CACHE_TTL_WORKFLOW_ANALYTICS)

                results["users_succeeded"] += 1

            except Exception as e:
                logger.error(f"Failed to compute analytics for user {user_id}: {e}")
                results["users_failed"] += 1
                results["errors"].append(
                    {
                        "user_id": str(user_id),
                        "error": str(e),
                    }
                )

            results["users_processed"] += 1

        db.commit()

        logger.info(
            f"Workflow analytics aggregation completed. "
            f"Processed: {results['users_processed']}, "
            f"Succeeded: {results['users_succeeded']}, "
            f"Failed: {results['users_failed']}"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to aggregate workflow analytics: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Per-User Analytics Task
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.compute_user_workflow_analytics")
def compute_user_workflow_analytics(
    self,
    user_id: str,
    period_days: int = 30,
) -> dict[str, Any]:
    """
    Compute workflow analytics for a specific user.

    Can be triggered on-demand when user requests analytics.

    Args:
        user_id: UUID of the user
        period_days: Number of days to analyze

    Returns:
        dict: Computed workflow analytics
    """
    logger.info(f"Computing workflow analytics for user {user_id}")
    db: Session = get_sync_db()

    try:
        # Check cache first
        cache_key = _cache_key("user", user_id)
        cached_data = _get_from_cache(cache_key)
        if cached_data:
            logger.debug(f"Returning cached workflow analytics for user {user_id}")
            return cached_data

        # Define period
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        # Compute metrics
        user_uuid = UUID(user_id)
        metrics = _compute_user_metrics_sync(db, user_uuid, start_date, end_date)

        # Store in database
        _store_analytics_sync(
            db=db,
            user_id=user_uuid,
            period_start=start_date,
            period_end=end_date,
            period_type="weekly",
            metrics=metrics,
        )

        db.commit()

        # Cache the results
        _store_in_cache(cache_key, metrics, CACHE_TTL_WORKFLOW_ANALYTICS)

        logger.info(f"Workflow analytics computed for user {user_id}")
        return metrics

    except Exception as e:
        logger.error(f"Failed to compute workflow analytics for user {user_id}: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Cleanup Task
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.cleanup_old_workflow_events")
def cleanup_old_workflow_events(
    self,
    retention_days: int = 365,
) -> dict[str, Any]:
    """
    Clean up old workflow events beyond retention period.

    Args:
        retention_days: Number of days to retain events (default: 365)

    Returns:
        dict: Cleanup results
    """
    logger.info(f"Starting cleanup of workflow events older than {retention_days} days")
    db: Session = get_sync_db()

    try:
        cutoff_date = datetime.utcnow() - timedelta(days=retention_days)

        # Count events to delete
        count_result = db.execute(select(func.count(WorkflowEvent.id)).where(WorkflowEvent.occurred_at < cutoff_date))
        events_to_delete = count_result.scalar() or 0

        if events_to_delete > 0:
            # Delete in batches to avoid long-running transactions
            batch_size = 1000
            deleted_total = 0

            while deleted_total < events_to_delete:
                # Get batch of IDs to delete
                ids_result = db.execute(
                    select(WorkflowEvent.id).where(WorkflowEvent.occurred_at < cutoff_date).limit(batch_size)
                )
                ids_to_delete = [row[0] for row in ids_result.all()]

                if not ids_to_delete:
                    break

                # Delete batch
                db.execute(WorkflowEvent.__table__.delete().where(WorkflowEvent.id.in_(ids_to_delete)))
                db.commit()

                deleted_total += len(ids_to_delete)
                logger.debug(f"Deleted {deleted_total}/{events_to_delete} workflow events")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "retention_days": retention_days,
            "cutoff_date": cutoff_date.isoformat(),
            "events_deleted": events_to_delete,
        }

        logger.info(f"Workflow event cleanup completed. Deleted {events_to_delete} events.")
        return results

    except Exception as e:
        logger.error(f"Failed to cleanup workflow events: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


# =============================================================================
# Pre-calculation Tasks
# =============================================================================


@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.precalculate_analytics")
def precalculate_analytics(self) -> dict[str, Any]:
    """
    Pre-calculate common analytics queries for all active users.

    Run hourly to ensure analytics cache is warm for users who frequently
    access the dashboard. This reduces latency when users request analytics.

    Pre-calculates and caches:
    - Time per stage for all active users
    - Bottleneck analysis
    - Completion rates

    Returns:
        dict: Summary of pre-calculation results
    """
    logger.info("Starting analytics pre-calculation for active users")
    db: Session = get_sync_db()

    try:
        # Get users who have been active recently (have applications modified in last 7 days)
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        users_result = db.execute(
            select(User.id)
            .distinct()
            .join(GrantApplication, User.id == GrantApplication.user_id)
            .where(GrantApplication.updated_at >= cutoff_date)
        )
        active_user_ids = [row[0] for row in users_result.all()]

        logger.info(f"Found {len(active_user_ids)} active users for pre-calculation")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "active_users": len(active_user_ids),
            "users_succeeded": 0,
            "users_failed": 0,
            "cache_entries_created": 0,
            "errors": [],
        }

        # Define analysis period
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        for user_id in active_user_ids:
            try:
                # Compute and cache metrics
                metrics = _compute_user_metrics_sync(db, user_id, start_date, end_date)

                # Store in Redis cache with appropriate TTLs
                # Time per stage (5 minutes TTL in in-memory, 1 hour in Redis)
                time_per_stage_key = _cache_key("time_per_stage", str(user_id))
                _store_in_cache(time_per_stage_key, metrics.get("time_per_stage", {}), 60 * 60)

                # Bottlenecks (15 minutes TTL in in-memory, 2 hours in Redis)
                bottlenecks_key = _cache_key("bottlenecks", str(user_id))
                _store_in_cache(bottlenecks_key, metrics.get("bottlenecks", []), 2 * 60 * 60)

                # Completion rates (30 minutes TTL in in-memory, 4 hours in Redis)
                completion_rates_key = _cache_key("completion_rates", str(user_id))
                _store_in_cache(
                    completion_rates_key,
                    {
                        "submission_rate": metrics.get("summary", {}).get("submission_rate", 0),
                        "success_rate": metrics.get("summary", {}).get("success_rate", 0),
                    },
                    4 * 60 * 60,
                )

                # Full summary
                summary_key = _cache_key("user", str(user_id))
                _store_in_cache(summary_key, metrics, CACHE_TTL_WORKFLOW_ANALYTICS)

                results["users_succeeded"] += 1
                results["cache_entries_created"] += 4  # 4 entries per user

            except Exception as e:
                logger.error(f"Failed to pre-calculate analytics for user {user_id}: {e}")
                results["users_failed"] += 1
                results["errors"].append(
                    {
                        "user_id": str(user_id),
                        "error": str(e),
                    }
                )

        logger.info(
            f"Analytics pre-calculation completed. "
            f"Succeeded: {results['users_succeeded']}, "
            f"Failed: {results['users_failed']}, "
            f"Cache entries: {results['cache_entries_created']}"
        )

        return results

    except Exception as e:
        logger.error(f"Failed to pre-calculate analytics: {e}", exc_info=True)
        raise
    finally:
        db.close()


@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.warm_analytics_cache")
def warm_analytics_cache(
    self,
    user_id: str,
) -> dict[str, Any]:
    """
    Warm the analytics cache for a specific user.

    Call this after significant events like:
    - New workflow event recorded
    - Application status change
    - User completes onboarding

    Args:
        user_id: UUID of the user (as string)

    Returns:
        dict: Cache warming results
    """
    logger.info(f"Warming analytics cache for user {user_id}")
    db: Session = get_sync_db()

    try:
        # Define analysis period
        end_date = date.today()
        start_date = end_date - timedelta(days=90)

        # Compute metrics
        user_uuid = UUID(user_id)
        metrics = _compute_user_metrics_sync(db, user_uuid, start_date, end_date)

        # Store in cache with various TTLs
        time_per_stage_key = _cache_key("time_per_stage", user_id)
        _store_in_cache(time_per_stage_key, metrics.get("time_per_stage", {}), 60 * 60)

        bottlenecks_key = _cache_key("bottlenecks", user_id)
        _store_in_cache(bottlenecks_key, metrics.get("bottlenecks", []), 2 * 60 * 60)

        completion_rates_key = _cache_key("completion_rates", user_id)
        _store_in_cache(
            completion_rates_key,
            {
                "submission_rate": metrics.get("summary", {}).get("submission_rate", 0),
                "success_rate": metrics.get("summary", {}).get("success_rate", 0),
            },
            4 * 60 * 60,
        )

        summary_key = _cache_key("user", user_id)
        _store_in_cache(summary_key, metrics, CACHE_TTL_WORKFLOW_ANALYTICS)

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "cache_entries_created": 4,
            "status": "success",
        }

        logger.info(f"Analytics cache warmed for user {user_id}")
        return results

    except Exception as e:
        logger.error(f"Failed to warm analytics cache for user {user_id}: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
        }
    finally:
        db.close()


@celery_app.task(bind=True, name="backend.tasks.workflow_analytics.invalidate_user_cache")
def invalidate_user_cache_task(
    self,
    user_id: str,
) -> dict[str, Any]:
    """
    Invalidate all cached analytics data for a specific user.

    Call this when user data changes significantly to ensure
    fresh calculations on next request.

    Args:
        user_id: UUID of the user (as string)

    Returns:
        dict: Invalidation results
    """
    logger.info(f"Invalidating analytics cache for user {user_id}")

    try:
        # Delete all cache keys for this user
        keys_to_delete = [
            _cache_key("user", user_id),
            _cache_key("time_per_stage", user_id),
            _cache_key("bottlenecks", user_id),
            _cache_key("completion_rates", user_id),
        ]

        deleted_count = 0
        for key in keys_to_delete:
            try:
                result = redis_client.delete(key)
                if result:
                    deleted_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete cache key {key}: {e}")

        results = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "keys_deleted": deleted_count,
            "status": "success",
        }

        logger.info(f"Cache invalidated for user {user_id}: {deleted_count} keys deleted")
        return results

    except Exception as e:
        logger.error(f"Failed to invalidate cache for user {user_id}: {e}", exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "status": "failed",
            "error": str(e),
        }


# =============================================================================
# Sync Helper Functions
# =============================================================================


def _compute_user_metrics_sync(
    db: Session,
    user_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, Any]:
    """
    Compute workflow metrics for a user (synchronous version).

    Args:
        db: Database session
        user_id: User UUID
        start_date: Analysis period start
        end_date: Analysis period end

    Returns:
        dict: Computed metrics
    """
    from collections import defaultdict
    from statistics import mean, median

    # Get applications for this user
    apps_result = db.execute(select(GrantApplication).where(GrantApplication.user_id == user_id))
    applications = apps_result.scalars().all()

    if not applications:
        return {
            "total_applications": 0,
            "message": "No applications found",
        }

    # Count by stage
    stage_counts = defaultdict(int)
    for app in applications:
        stage_counts[app.stage.value] += 1

    # Get workflow events
    events_result = db.execute(
        select(WorkflowEvent)
        .join(GrantApplication, WorkflowEvent.kanban_card_id == GrantApplication.id)
        .where(
            GrantApplication.user_id == user_id,
            WorkflowEvent.occurred_at >= datetime.combine(start_date, datetime.min.time()),
            WorkflowEvent.occurred_at <= datetime.combine(end_date, datetime.max.time()),
        )
        .order_by(WorkflowEvent.kanban_card_id, WorkflowEvent.occurred_at)
    )
    events = events_result.scalars().all()

    # Calculate time in each stage
    app_events: dict[UUID, list] = defaultdict(list)
    for event in events:
        app_events[event.kanban_card_id].append(event)

    stage_times: dict[str, list[float]] = defaultdict(list)

    for app_id, app_event_list in app_events.items():
        stage_enter_times: dict[str, datetime] = {}

        for event in sorted(app_event_list, key=lambda e: e.occurred_at):
            if event.event_type == "stage_enter" and event.stage:
                stage_enter_times[event.stage] = event.occurred_at
            elif event.event_type == "stage_exit" and event.stage:
                if event.stage in stage_enter_times:
                    duration = event.occurred_at - stage_enter_times[event.stage]
                    hours = duration.total_seconds() / 3600
                    stage_times[event.stage].append(hours)
                    del stage_enter_times[event.stage]

    # Build stage metrics
    time_per_stage = {}
    for stage in WorkflowStage.all_stages():
        times = stage_times.get(stage, [])
        if times:
            time_per_stage[stage] = {
                "avg_hours": round(mean(times), 2),
                "median_hours": round(median(times), 2),
                "min_hours": round(min(times), 2),
                "max_hours": round(max(times), 2),
                "count": len(times),
            }
        else:
            time_per_stage[stage] = {
                "avg_hours": 0,
                "median_hours": 0,
                "min_hours": 0,
                "max_hours": 0,
                "count": 0,
            }

    # Calculate completion rates
    total = len(applications)
    submitted = sum(1 for app in applications if app.stage.value in ["submitted", "awarded", "rejected"])
    awarded = stage_counts.get("awarded", 0)
    rejected = stage_counts.get("rejected", 0)

    submission_rate = _calculate_percentage(submitted, total)
    success_rate = _calculate_percentage(awarded, submitted)

    # Identify bottlenecks
    bottlenecks = []
    thresholds = {
        "researching": 72,  # 3 days
        "writing": 168,  # 7 days
        "submitted": 720,  # 30 days
    }

    now = datetime.utcnow()
    for stage in ["researching", "writing", "submitted"]:
        stage_apps = [app for app in applications if app.stage.value == stage]
        if not stage_apps:
            continue

        stuck_count = 0
        for app in stage_apps:
            # Use updated_at as proxy for stage entry time
            entry_time = app.updated_at or app.created_at
            hours_in_stage = (now - entry_time).total_seconds() / 3600
            if hours_in_stage > thresholds.get(stage, 168):
                stuck_count += 1

        if stuck_count > 0:
            bottlenecks.append(
                {
                    "stage": stage,
                    "stuck_count": stuck_count,
                    "total_in_stage": len(stage_apps),
                    "pct_stuck": round(stuck_count / len(stage_apps) * 100, 1),
                }
            )

    # Compile metrics
    metrics = {
        "computed_at": datetime.utcnow().isoformat(),
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
        "summary": {
            "total_applications": total,
            "active_applications": stage_counts.get("researching", 0)
            + stage_counts.get("writing", 0)
            + stage_counts.get("submitted", 0),
            "completed_applications": awarded + rejected,
            "submission_rate": submission_rate,
            "success_rate": success_rate,
        },
        "stage_counts": dict(stage_counts),
        "time_per_stage": time_per_stage,
        "bottlenecks": bottlenecks,
        "events_analyzed": len(events),
    }

    return metrics


def _store_analytics_sync(
    db: Session,
    user_id: UUID,
    period_start: date,
    period_end: date,
    period_type: str,
    metrics: dict[str, Any],
) -> WorkflowAnalytics:
    """
    Store workflow analytics in database (synchronous version).

    Args:
        db: Database session
        user_id: User UUID
        period_start: Period start date
        period_end: Period end date
        period_type: Period type (daily, weekly, monthly)
        metrics: Computed metrics

    Returns:
        WorkflowAnalytics record
    """
    import uuid as uuid_module

    # Check for existing record
    result = db.execute(
        select(WorkflowAnalytics).where(
            WorkflowAnalytics.user_id == user_id,
            WorkflowAnalytics.period_start == period_start,
            WorkflowAnalytics.period_end == period_end,
            WorkflowAnalytics.period_type == period_type,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.metrics = metrics
        existing.generated_at = datetime.utcnow()
        return existing

    analytics = WorkflowAnalytics(
        id=uuid_module.uuid4(),
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
        period_type=period_type,
        metrics=metrics,
        generated_at=datetime.utcnow(),
    )
    db.add(analytics)
    return analytics


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    # Aggregation tasks
    "aggregate_workflow_analytics",
    "compute_user_workflow_analytics",
    # Cleanup tasks
    "cleanup_old_workflow_events",
    # Pre-calculation tasks
    "precalculate_analytics",
    "warm_analytics_cache",
    "invalidate_user_cache_task",
]
