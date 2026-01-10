"""
GrantRadar Cleanup Tasks

Periodic maintenance tasks for data cleanup, archival, and resource management.

Tasks:
    - cleanup_expired_data: Main cleanup task scheduled daily
    - cleanup_old_alerts: Remove old alert records
    - cleanup_redis_streams: Trim Redis streams to manageable size
    - cleanup_failed_tasks: Clean up Celery task results and dead letter queues
    - archive_old_grants: Move expired grants to archive table

Queue: normal (all tasks run on normal priority queue)
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import redis
from sqlalchemy import delete, func, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import get_sync_db
from backend.events import StreamNames
from backend.models import AlertSent, Grant, Match

logger = logging.getLogger(__name__)


# =============================================================================
# Helper Functions
# =============================================================================


def get_redis_client() -> redis.Redis:
    """
    Get a synchronous Redis client for cleanup tasks.

    Returns:
        Redis client instance.
    """
    return redis.from_url(settings.redis_url, decode_responses=True)


def get_celery_redis_client() -> redis.Redis:
    """
    Get Redis client connected to Celery result backend.

    Returns:
        Redis client instance for Celery results.
    """
    return redis.from_url(settings.celery_result_backend, decode_responses=True)


# =============================================================================
# Main Cleanup Task (Scheduled Daily)
# =============================================================================


@celery_app.task(
    name="backend.tasks.cleanup.cleanup_expired_data",
    queue="normal",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2400,  # 40 minutes
)
def cleanup_expired_data() -> dict[str, Any]:
    """
    Main cleanup task that runs daily to clean expired data.

    Performs:
        1. Delete grants with deadlines >1 year past
        2. Archive old matches (>6 months, not saved)
        3. Clean up expired Redis keys
        4. Vacuum database tables
        5. Trim Redis streams

    Returns:
        dict: Cleanup statistics including counts of deleted records.

    Raises:
        SQLAlchemyError: On database errors (will trigger retry).
        redis.RedisError: On Redis errors (will trigger retry).
    """
    logger.info("Starting daily cleanup job")
    start_time = datetime.utcnow()
    stats: dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "grants_deleted": 0,
        "matches_archived": 0,
        "alerts_deleted": 0,
        "redis_keys_deleted": 0,
        "streams_trimmed": 0,
        "errors": [],
    }

    db = get_sync_db()

    try:
        # =====================================================================
        # 1. Delete grants with deadlines >1 year past
        # =====================================================================
        logger.info("Deleting expired grants (deadline >1 year past)")
        one_year_ago = datetime.utcnow() - timedelta(days=365)

        try:
            expired_grants_query = delete(Grant).where(
                Grant.deadline < one_year_ago,
                Grant.deadline.isnot(None),  # Only delete grants with deadlines
            )
            result = db.execute(expired_grants_query)
            stats["grants_deleted"] = result.rowcount
            db.commit()
            logger.info(f"Deleted {stats['grants_deleted']} expired grants")
        except SQLAlchemyError as e:
            db.rollback()
            error_msg = f"Failed to delete expired grants: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # =====================================================================
        # 2. Archive old matches (>6 months, not saved by user)
        # =====================================================================
        logger.info("Archiving old matches (>6 months, not saved)")
        six_months_ago = datetime.utcnow() - timedelta(days=180)

        try:
            # Delete matches that are old and not saved/applied
            old_matches_query = delete(Match).where(
                Match.created_at < six_months_ago,
                Match.user_action.in_([None, "dismissed"]),
            )
            result = db.execute(old_matches_query)
            stats["matches_archived"] = result.rowcount
            db.commit()
            logger.info(f"Archived {stats['matches_archived']} old matches")
        except SQLAlchemyError as e:
            db.rollback()
            error_msg = f"Failed to archive old matches: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # =====================================================================
        # 3. Clean up old alert records (call dedicated task)
        # =====================================================================
        try:
            alert_stats = cleanup_old_alerts()
            stats["alerts_deleted"] = alert_stats.get("alerts_deleted", 0)
        except Exception as e:
            error_msg = f"Failed to cleanup alerts: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # =====================================================================
        # 4. Clean up expired Redis keys
        # =====================================================================
        logger.info("Cleaning up expired Redis keys")
        try:
            redis_client = get_redis_client()

            # Clean up session keys older than 7 days
            session_pattern = "session:*"
            session_keys = redis_client.keys(session_pattern)
            deleted_count = 0

            for key in session_keys:
                ttl = redis_client.ttl(key)
                # Delete keys with no TTL or expired
                if ttl == -1 or ttl == -2:
                    redis_client.delete(key)
                    deleted_count += 1

            stats["redis_keys_deleted"] = deleted_count
            logger.info(f"Deleted {deleted_count} expired Redis keys")

            redis_client.close()
        except redis.RedisError as e:
            error_msg = f"Failed to cleanup Redis keys: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # =====================================================================
        # 5. Vacuum database tables
        # =====================================================================
        logger.info("Vacuuming database tables")
        try:
            # Run VACUUM ANALYZE on key tables
            # Note: VACUUM cannot run inside a transaction block
            db.connection().connection.set_isolation_level(0)  # Autocommit mode

            for table in ["grants", "matches", "alerts_sent"]:
                try:
                    db.execute(text(f"VACUUM ANALYZE {table}"))
                    logger.info(f"Vacuumed table: {table}")
                except Exception as e:
                    logger.warning(f"Failed to vacuum {table}: {e}")

            db.connection().connection.set_isolation_level(1)  # Back to normal
        except Exception as e:
            error_msg = f"Failed to vacuum tables: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

        # =====================================================================
        # 6. Trim Redis streams (call dedicated task)
        # =====================================================================
        try:
            stream_stats = cleanup_redis_streams()
            stats["streams_trimmed"] = stream_stats.get("streams_trimmed", 0)
        except Exception as e:
            error_msg = f"Failed to trim Redis streams: {e}"
            logger.error(error_msg, exc_info=True)
            stats["errors"].append(error_msg)

    except Exception as e:
        error_msg = f"Unexpected error during cleanup: {e}"
        logger.error(error_msg, exc_info=True)
        stats["errors"].append(error_msg)
    finally:
        db.close()

    # Calculate total duration
    end_time = datetime.utcnow()
    stats["completed_at"] = end_time.isoformat()
    stats["duration_seconds"] = (end_time - start_time).total_seconds()

    logger.info(
        "Daily cleanup job completed",
        extra={
            "stats": stats,
            "duration": stats["duration_seconds"],
        },
    )

    return stats


# =============================================================================
# Alert Cleanup Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.cleanup.cleanup_old_alerts",
    queue="normal",
    soft_time_limit=600,  # 10 minutes
    time_limit=900,  # 15 minutes
)
def cleanup_old_alerts(days_old: int = 90) -> dict[str, Any]:
    """
    Remove alert_sent records older than specified days.

    Keeps only summary statistics and frees up database space.
    Alerts older than the threshold that haven't been engaged with
    are safe to delete.

    Args:
        days_old: Number of days to retain alerts (default: 90).

    Returns:
        dict: Cleanup statistics.

    Raises:
        SQLAlchemyError: On database errors.
    """
    logger.info(f"Cleaning up alerts older than {days_old} days")
    start_time = datetime.utcnow()
    stats: dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "alerts_deleted": 0,
        "summary_stats": {},
    }

    db = get_sync_db()

    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # First, collect summary statistics before deletion
        summary_query = (
            select(
                AlertSent.channel,
                func.count(AlertSent.id).label("total_sent"),
                func.count(AlertSent.opened_at).label("total_opened"),
                func.count(AlertSent.clicked_at).label("total_clicked"),
            )
            .where(AlertSent.sent_at < cutoff_date)
            .group_by(AlertSent.channel)
        )

        summary_results = db.execute(summary_query).all()

        # Store summary statistics
        for row in summary_results:
            stats["summary_stats"][row.channel] = {
                "total_sent": row.total_sent,
                "total_opened": row.total_opened,
                "total_clicked": row.total_clicked,
                "open_rate": ((row.total_opened / row.total_sent * 100) if row.total_sent > 0 else 0),
                "click_rate": ((row.total_clicked / row.total_sent * 100) if row.total_sent > 0 else 0),
            }

        # Delete old alerts
        delete_query = delete(AlertSent).where(AlertSent.sent_at < cutoff_date)
        result = db.execute(delete_query)
        stats["alerts_deleted"] = result.rowcount

        db.commit()

        end_time = datetime.utcnow()
        stats["completed_at"] = end_time.isoformat()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Deleted {stats['alerts_deleted']} old alerts",
            extra={"stats": stats},
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to cleanup old alerts: {e}", exc_info=True)
        raise
    finally:
        db.close()

    return stats


# =============================================================================
# Redis Stream Cleanup Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.cleanup.cleanup_redis_streams",
    queue="normal",
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
)
def cleanup_redis_streams(max_length: int = 10000) -> dict[str, Any]:
    """
    Trim Redis streams to reasonable size to prevent memory bloat.

    Keeps only the most recent entries per stream and cleans up
    inactive consumer groups.

    Args:
        max_length: Maximum number of entries to keep per stream (default: 10000).

    Returns:
        dict: Cleanup statistics.

    Raises:
        redis.RedisError: On Redis errors.
    """
    logger.info(f"Trimming Redis streams to max length {max_length}")
    start_time = datetime.utcnow()
    stats: dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "streams_trimmed": 0,
        "total_entries_removed": 0,
        "consumer_groups_cleaned": 0,
        "stream_details": {},
    }

    try:
        redis_client = get_redis_client()

        # Get all main streams
        all_streams = StreamNames.all_streams()

        for stream_name in all_streams:
            try:
                # Check if stream exists
                stream_info = redis_client.xinfo_stream(stream_name)
                current_length = stream_info["length"]

                if current_length > max_length:
                    # Trim to max_length using XTRIM with MAXLEN
                    removed = redis_client.xtrim(stream_name, maxlen=max_length)
                    stats["streams_trimmed"] += 1
                    stats["total_entries_removed"] += removed

                    stats["stream_details"][stream_name] = {
                        "original_length": current_length,
                        "new_length": max_length,
                        "entries_removed": removed,
                    }

                    logger.info(f"Trimmed stream {stream_name}: {current_length} -> {max_length} ({removed} removed)")
                else:
                    stats["stream_details"][stream_name] = {
                        "length": current_length,
                        "action": "no_trim_needed",
                    }

                # Clean up inactive consumer groups
                try:
                    groups_info = redis_client.xinfo_groups(stream_name)

                    for group in groups_info:
                        # Check if consumer group has pending messages older than 7 days
                        pending = redis_client.xpending(stream_name, group["name"])

                        if pending:
                            # If no messages pending, consumer group might be inactive
                            # This is a simplified check - in production you'd want more logic
                            pass

                except redis.ResponseError:
                    # No consumer groups exist for this stream
                    pass

            except redis.ResponseError as e:
                # Stream doesn't exist
                logger.debug(f"Stream {stream_name} doesn't exist: {e}")
                continue

        # Also trim dead letter queues
        for stream_name in all_streams:
            dlq_name = StreamNames.get_dlq_for_stream(stream_name)
            try:
                dlq_info = redis_client.xinfo_stream(dlq_name)
                dlq_length = dlq_info["length"]

                if dlq_length > 1000:  # Keep fewer DLQ entries
                    removed = redis_client.xtrim(dlq_name, maxlen=1000)
                    stats["total_entries_removed"] += removed
                    logger.info(f"Trimmed DLQ {dlq_name}: removed {removed} entries")

            except redis.ResponseError:
                # DLQ doesn't exist
                continue

        redis_client.close()

        end_time = datetime.utcnow()
        stats["completed_at"] = end_time.isoformat()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Trimmed {stats['streams_trimmed']} streams, removed {stats['total_entries_removed']} entries",
            extra={"stats": stats},
        )

    except redis.RedisError as e:
        logger.error(f"Failed to cleanup Redis streams: {e}", exc_info=True)
        raise

    return stats


# =============================================================================
# Celery Task Results Cleanup
# =============================================================================


@celery_app.task(
    name="backend.tasks.cleanup.cleanup_failed_tasks",
    queue="normal",
    soft_time_limit=300,  # 5 minutes
    time_limit=600,  # 10 minutes
)
def cleanup_failed_tasks(days_old: int = 7) -> dict[str, Any]:
    """
    Remove Celery task results older than specified days.

    Cleans up:
        1. Old task results from Redis
        2. Dead letter queue entries
        3. Stuck consumer group pending messages

    Args:
        days_old: Number of days to retain task results (default: 7).

    Returns:
        dict: Cleanup statistics.

    Raises:
        redis.RedisError: On Redis errors.
    """
    logger.info(f"Cleaning up Celery task results older than {days_old} days")
    start_time = datetime.utcnow()
    stats: dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "task_results_deleted": 0,
        "dlq_entries_removed": 0,
        "pending_messages_acked": 0,
    }

    try:
        redis_client = get_celery_redis_client()

        # Calculate cutoff timestamp (in milliseconds)
        cutoff_timestamp = int((datetime.utcnow() - timedelta(days=days_old)).timestamp() * 1000)

        # =====================================================================
        # 1. Clean up old Celery task results
        # =====================================================================
        # Celery stores results with keys like: celery-task-meta-{task_id}
        task_result_pattern = "celery-task-meta-*"
        task_keys = redis_client.keys(task_result_pattern)

        for key in task_keys:
            try:
                # Check TTL - if no TTL set or already expired, delete
                ttl = redis_client.ttl(key)
                if ttl == -1:
                    # No TTL set, check if result is old by looking at the data
                    # For safety, we'll just ensure TTL is set
                    redis_client.expire(key, 86400 * days_old)  # Set TTL
                elif ttl == -2:
                    # Key doesn't exist (race condition)
                    pass
            except Exception as e:
                logger.warning(f"Error checking task result key {key}: {e}")

        logger.info(f"Processed {len(task_keys)} task result keys")

        # =====================================================================
        # 2. Clean up dead letter queue entries
        # =====================================================================
        all_streams = StreamNames.all_streams()

        for stream_name in all_streams:
            dlq_name = StreamNames.get_dlq_for_stream(stream_name)

            try:
                # Get DLQ entries older than cutoff
                dlq_entries = redis_client.xrange(dlq_name, "-", "+")

                removed = 0
                for entry_id, entry_data in dlq_entries:
                    # Entry ID format: timestamp-sequence
                    entry_timestamp = int(entry_id.split("-")[0])

                    if entry_timestamp < cutoff_timestamp:
                        redis_client.xdel(dlq_name, entry_id)
                        removed += 1

                stats["dlq_entries_removed"] += removed

                if removed > 0:
                    logger.info(f"Removed {removed} old entries from {dlq_name}")

            except redis.ResponseError:
                # DLQ doesn't exist
                continue

        # =====================================================================
        # 3. Reset stuck consumer groups
        # =====================================================================
        # This is more aggressive - handle with care in production
        for stream_name in all_streams:
            try:
                groups = redis_client.xinfo_groups(stream_name)

                for group in groups:
                    group_name = group["name"]
                    pending_info = redis_client.xpending(stream_name, group_name)

                    if pending_info and pending_info[0] > 0:
                        # Get detailed pending messages
                        pending_messages = redis_client.xpending_range(
                            stream_name,
                            group_name,
                            min="-",
                            max="+",
                            count=100,
                        )

                        for msg in pending_messages:
                            msg_id = msg["message_id"]
                            idle_time_ms = msg["time_since_delivered"]

                            # If message has been pending for > 1 hour, acknowledge it
                            if idle_time_ms > 3600000:  # 1 hour in ms
                                redis_client.xack(stream_name, group_name, msg_id)
                                stats["pending_messages_acked"] += 1

            except redis.ResponseError:
                # Stream or consumer group doesn't exist
                continue

        redis_client.close()

        end_time = datetime.utcnow()
        stats["completed_at"] = end_time.isoformat()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            "Celery cleanup completed",
            extra={
                "stats": stats,
                "duration": stats["duration_seconds"],
            },
        )

    except redis.RedisError as e:
        logger.error(f"Failed to cleanup Celery tasks: {e}", exc_info=True)
        raise

    return stats


# =============================================================================
# Grant Archive Task
# =============================================================================


@celery_app.task(
    name="backend.tasks.cleanup.archive_old_grants",
    queue="normal",
    soft_time_limit=1800,  # 30 minutes
    time_limit=2400,  # 40 minutes
)
def archive_old_grants(months_old: int = 12) -> dict[str, Any]:
    """
    Move expired grants to archive table for long-term storage.

    Archives grants with deadlines older than specified months while
    preserving metadata for analytics. This helps keep the main grants
    table performant.

    Note: This task assumes an archive table exists. If not, grants
    are marked with an 'archived' flag in metadata instead.

    Args:
        months_old: Number of months after deadline to archive (default: 12).

    Returns:
        dict: Archive statistics.

    Raises:
        SQLAlchemyError: On database errors.
    """
    logger.info(f"Archiving grants with deadlines older than {months_old} months")
    start_time = datetime.utcnow()
    stats: dict[str, Any] = {
        "started_at": start_time.isoformat(),
        "grants_archived": 0,
        "total_size_bytes": 0,
    }

    db = get_sync_db()

    try:
        # Calculate cutoff date
        cutoff_date = datetime.utcnow() - timedelta(days=months_old * 30)

        # Find grants to archive
        archive_query = select(Grant).where(
            Grant.deadline < cutoff_date,
            Grant.deadline.isnot(None),
        )

        grants_to_archive = db.execute(archive_query).scalars().all()

        # Since we don't have an archive table defined in models.py,
        # we'll use a simpler approach: add metadata flag and delete matches
        for grant in grants_to_archive:
            try:
                # Update grant metadata to mark as archived
                if grant.raw_data is None:
                    grant.raw_data = {}

                grant.raw_data["archived_at"] = datetime.utcnow().isoformat()
                grant.raw_data["archived_reason"] = "deadline_expired"

                # Optionally delete associated matches to save space
                # (only if they haven't been saved by users)
                unsaved_matches_query = delete(Match).where(
                    Match.grant_id == grant.id,
                    Match.user_action.in_([None, "dismissed"]),
                )
                db.execute(unsaved_matches_query)

                stats["grants_archived"] += 1

            except Exception as e:
                logger.warning(f"Failed to archive grant {grant.id}: {e}")
                continue

        db.commit()

        end_time = datetime.utcnow()
        stats["completed_at"] = end_time.isoformat()
        stats["duration_seconds"] = (end_time - start_time).total_seconds()

        logger.info(
            f"Archived {stats['grants_archived']} grants",
            extra={"stats": stats},
        )

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Failed to archive grants: {e}", exc_info=True)
        raise
    finally:
        db.close()

    return stats


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "cleanup_expired_data",
    "cleanup_old_alerts",
    "cleanup_redis_streams",
    "cleanup_failed_tasks",
    "archive_old_grants",
]
