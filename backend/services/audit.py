"""
Global Audit Logging Service
Comprehensive service for logging and querying audit events.
"""
import csv
import io
import json
import logging
import time
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from sqlalchemy import and_, desc, distinct, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.audit import AuditLog
from backend.models import User
from backend.schemas.audit import (
    AuditExportFormat,
    AuditLogCreate,
    AuditLogFilters,
    AuditLogResponse,
    AuditStats,
    ResourceHistory,
    UserActivitySummary,
)

logger = logging.getLogger(__name__)

# Type variable for decorated functions
F = TypeVar("F", bound=Callable[..., Any])


class AuditService:
    """
    Service for comprehensive audit logging across the application.

    Provides methods for:
    - Logging actions with full context
    - Querying logs with various filters
    - User activity analysis
    - Resource change history
    - Exporting logs for compliance
    """

    def __init__(self, db: AsyncSession):
        """Initialize audit service with database session."""
        self.db = db

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        old_values: Optional[dict] = None,
        new_values: Optional[dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        extra_data: Optional[dict] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
    ) -> AuditLog:
        """
        Log an action to the audit log.

        Args:
            action: Type of action (CREATE, READ, UPDATE, DELETE, LOGIN, etc.)
            resource_type: Type of resource affected (grant, user, team, etc.)
            resource_id: ID of the affected resource
            user_id: ID of the user performing the action
            old_values: Previous values (for UPDATE actions)
            new_values: New values (for CREATE/UPDATE actions)
            ip_address: Client IP address
            user_agent: Client user agent string
            extra_data: Additional context
            success: Whether the action succeeded
            error_message: Error message if failed
            request_id: Request correlation ID
            duration_ms: Action duration in milliseconds

        Returns:
            Created AuditLog entry
        """
        audit_log = AuditLog(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            extra_data=extra_data,
            success=success,
            error_message=error_message,
            request_id=request_id,
            duration_ms=duration_ms,
            timestamp=datetime.now(timezone.utc),
        )

        self.db.add(audit_log)
        await self.db.flush()
        await self.db.refresh(audit_log)

        logger.debug(
            f"Audit log created: {action} on {resource_type} "
            f"(id={resource_id}, user={user_id}, success={success})"
        )

        return audit_log

    async def get_audit_logs(
        self,
        filters: Optional[AuditLogFilters] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[AuditLogResponse], int]:
        """
        Query audit logs with filters and pagination.

        Args:
            filters: Query filters
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of audit log responses, total count)
        """
        # Build base query
        query = select(AuditLog).order_by(desc(AuditLog.timestamp))

        # Apply filters
        if filters:
            conditions = []

            if filters.user_id:
                conditions.append(AuditLog.user_id == filters.user_id)

            if filters.action:
                conditions.append(AuditLog.action == filters.action)

            if filters.actions:
                conditions.append(AuditLog.action.in_(filters.actions))

            if filters.resource_type:
                conditions.append(AuditLog.resource_type == filters.resource_type)

            if filters.resource_types:
                conditions.append(AuditLog.resource_type.in_(filters.resource_types))

            if filters.resource_id:
                conditions.append(AuditLog.resource_id == filters.resource_id)

            if filters.success is not None:
                conditions.append(AuditLog.success == filters.success)

            if filters.start_date:
                conditions.append(AuditLog.timestamp >= filters.start_date)

            if filters.end_date:
                conditions.append(AuditLog.timestamp <= filters.end_date)

            if filters.ip_address:
                conditions.append(AuditLog.ip_address == filters.ip_address)

            if filters.request_id:
                conditions.append(AuditLog.request_id == filters.request_id)

            if filters.search_query:
                search_term = f"%{filters.search_query}%"
                conditions.append(
                    or_(
                        AuditLog.error_message.ilike(search_term),
                        func.cast(AuditLog.extra_data, String).ilike(search_term),
                    )
                )

            if conditions:
                query = query.where(and_(*conditions))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply pagination
        offset = (page - 1) * page_size
        query = query.offset(offset).limit(page_size)

        # Execute query
        result = await self.db.execute(query)
        logs = result.scalars().all()

        # Convert to response models
        responses = []
        for log in logs:
            response = AuditLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                user_name=log.user.name if log.user else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                old_values=log.old_values,
                new_values=log.new_values,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                extra_data=log.extra_data,
                success=log.success,
                error_message=log.error_message,
                request_id=log.request_id,
                duration_ms=log.duration_ms,
            )
            responses.append(response)

        return responses, total

    async def get_user_activity(
        self,
        user_id: uuid.UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UserActivitySummary:
        """
        Get activity summary for a specific user.

        Args:
            user_id: User ID to get activity for
            start_date: Start of time range
            end_date: End of time range

        Returns:
            UserActivitySummary with aggregated activity data
        """
        # Build base conditions
        conditions = [AuditLog.user_id == user_id]

        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)

        # Get user info
        user_result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()

        # Get total and success/failure counts
        stats_query = select(
            func.count(AuditLog.id).label("total"),
            func.sum(func.cast(AuditLog.success, Integer)).label("successful"),
            func.min(AuditLog.timestamp).label("first"),
            func.max(AuditLog.timestamp).label("last"),
        ).where(and_(*conditions))

        stats_result = await self.db.execute(stats_query)
        stats = stats_result.first()

        # Get actions by type
        actions_query = (
            select(AuditLog.action, func.count(AuditLog.id).label("count"))
            .where(and_(*conditions))
            .group_by(AuditLog.action)
        )
        actions_result = await self.db.execute(actions_query)
        actions_by_type = {row.action: row.count for row in actions_result}

        # Get resources by type
        resources_query = (
            select(AuditLog.resource_type, func.count(AuditLog.id).label("count"))
            .where(and_(*conditions))
            .group_by(AuditLog.resource_type)
        )
        resources_result = await self.db.execute(resources_query)
        resources_by_type = {row.resource_type: row.count for row in resources_result}

        # Get unique IP addresses
        ips_query = (
            select(distinct(AuditLog.ip_address))
            .where(and_(*conditions, AuditLog.ip_address.isnot(None)))
        )
        ips_result = await self.db.execute(ips_query)
        ip_addresses = [row[0] for row in ips_result if row[0]]

        return UserActivitySummary(
            user_id=user_id,
            user_email=user.email if user else None,
            user_name=user.name if user else None,
            total_actions=stats.total or 0,
            successful_actions=stats.successful or 0,
            failed_actions=(stats.total or 0) - (stats.successful or 0),
            actions_by_type=actions_by_type,
            resources_by_type=resources_by_type,
            first_activity=stats.first or datetime.now(timezone.utc),
            last_activity=stats.last or datetime.now(timezone.utc),
            ip_addresses=ip_addresses,
        )

    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> ResourceHistory:
        """
        Get change history for a specific resource.

        Args:
            resource_type: Type of resource
            resource_id: Resource ID
            page: Page number
            page_size: Items per page

        Returns:
            ResourceHistory with change history
        """
        # Build query for this resource
        conditions = [
            AuditLog.resource_type == resource_type,
            AuditLog.resource_id == resource_id,
        ]

        # Get total changes
        count_query = select(func.count(AuditLog.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total_changes = count_result.scalar() or 0

        # Get history entries
        history_query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(desc(AuditLog.timestamp))
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        history_result = await self.db.execute(history_query)
        logs = history_result.scalars().all()

        # Convert to responses
        history = []
        for log in logs:
            response = AuditLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                user_id=log.user_id,
                user_email=log.user.email if log.user else None,
                user_name=log.user.name if log.user else None,
                action=log.action,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                old_values=log.old_values,
                new_values=log.new_values,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                extra_data=log.extra_data,
                success=log.success,
                error_message=log.error_message,
                request_id=log.request_id,
                duration_ms=log.duration_ms,
            )
            history.append(response)

        # Find creation entry
        created_query = (
            select(AuditLog)
            .where(
                and_(
                    *conditions,
                    AuditLog.action == "CREATE",
                )
            )
            .order_by(AuditLog.timestamp)
            .limit(1)
        )
        created_result = await self.db.execute(created_query)
        created_log = created_result.scalar_one_or_none()

        # Find last modification
        modified_query = (
            select(AuditLog)
            .where(and_(*conditions))
            .order_by(desc(AuditLog.timestamp))
            .limit(1)
        )
        modified_result = await self.db.execute(modified_query)
        modified_log = modified_result.scalar_one_or_none()

        return ResourceHistory(
            resource_type=resource_type,
            resource_id=resource_id,
            history=history,
            total_changes=total_changes,
            created_at=created_log.timestamp if created_log else None,
            created_by=created_log.user_id if created_log else None,
            last_modified_at=modified_log.timestamp if modified_log else None,
            last_modified_by=modified_log.user_id if modified_log else None,
        )

    async def export_audit_logs(
        self,
        format: AuditExportFormat,
        filters: Optional[AuditLogFilters] = None,
        include_details: bool = True,
        max_records: int = 10000,
    ) -> tuple[str, str]:
        """
        Export audit logs for compliance or analysis.

        Args:
            format: Export format (CSV or JSON)
            filters: Filters to apply
            include_details: Include old/new values and extra_data
            max_records: Maximum records to export

        Returns:
            Tuple of (export content, filename)
        """
        # Get logs with filters
        logs, total = await self.get_audit_logs(
            filters=filters,
            page=1,
            page_size=max_records,
        )

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

        if format == AuditExportFormat.JSON:
            # Export as JSON
            export_data = {
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "total_records": len(logs),
                "filters_applied": filters.model_dump() if filters else None,
                "logs": [log.model_dump(mode="json") for log in logs],
            }
            content = json.dumps(export_data, indent=2, default=str)
            filename = f"audit_logs_{timestamp}.json"

        else:
            # Export as CSV
            output = io.StringIO()
            writer = csv.writer(output)

            # Write headers
            headers = [
                "id",
                "timestamp",
                "user_id",
                "user_email",
                "action",
                "resource_type",
                "resource_id",
                "success",
                "error_message",
                "ip_address",
                "request_id",
                "duration_ms",
            ]
            if include_details:
                headers.extend(["old_values", "new_values", "extra_data"])

            writer.writerow(headers)

            # Write data rows
            for log in logs:
                row = [
                    str(log.id),
                    log.timestamp.isoformat() if log.timestamp else "",
                    str(log.user_id) if log.user_id else "",
                    log.user_email or "",
                    log.action,
                    log.resource_type,
                    str(log.resource_id) if log.resource_id else "",
                    str(log.success),
                    log.error_message or "",
                    log.ip_address or "",
                    log.request_id or "",
                    str(log.duration_ms) if log.duration_ms else "",
                ]
                if include_details:
                    row.extend([
                        json.dumps(log.old_values) if log.old_values else "",
                        json.dumps(log.new_values) if log.new_values else "",
                        json.dumps(log.extra_data) if log.extra_data else "",
                    ])
                writer.writerow(row)

            content = output.getvalue()
            filename = f"audit_logs_{timestamp}.csv"

        return content, filename

    async def get_audit_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> AuditStats:
        """
        Get aggregated audit statistics.

        Args:
            start_date: Start of time range
            end_date: End of time range

        Returns:
            AuditStats with aggregated metrics
        """
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        # Build base conditions
        conditions = []
        if start_date:
            conditions.append(AuditLog.timestamp >= start_date)
        if end_date:
            conditions.append(AuditLog.timestamp <= end_date)

        # Total logs
        total_query = select(func.count(AuditLog.id))
        if conditions:
            total_query = total_query.where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_logs = total_result.scalar() or 0

        # Logs today
        today_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.timestamp >= today_start)
        )
        logs_today = today_result.scalar() or 0

        # Logs this week
        week_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.timestamp >= week_start)
        )
        logs_this_week = week_result.scalar() or 0

        # Logs this month
        month_result = await self.db.execute(
            select(func.count(AuditLog.id)).where(AuditLog.timestamp >= month_start)
        )
        logs_this_month = month_result.scalar() or 0

        # Actions by type
        actions_query = (
            select(AuditLog.action, func.count(AuditLog.id).label("count"))
            .group_by(AuditLog.action)
        )
        if conditions:
            actions_query = actions_query.where(and_(*conditions))
        actions_result = await self.db.execute(actions_query)
        actions_by_type = {row.action: row.count for row in actions_result}

        # Resources by type
        resources_query = (
            select(AuditLog.resource_type, func.count(AuditLog.id).label("count"))
            .group_by(AuditLog.resource_type)
        )
        if conditions:
            resources_query = resources_query.where(and_(*conditions))
        resources_result = await self.db.execute(resources_query)
        resources_by_type = {row.resource_type: row.count for row in resources_result}

        # Success rate
        success_query = select(func.count(AuditLog.id)).where(AuditLog.success == True)
        if conditions:
            success_query = success_query.where(and_(*conditions))
        success_result = await self.db.execute(success_query)
        successful = success_result.scalar() or 0
        success_rate = (successful / total_logs * 100) if total_logs > 0 else 100.0

        # Unique users
        users_query = select(func.count(distinct(AuditLog.user_id)))
        if conditions:
            users_query = users_query.where(and_(*conditions))
        users_result = await self.db.execute(users_query)
        unique_users = users_result.scalar() or 0

        # Unique IPs
        ips_query = select(func.count(distinct(AuditLog.ip_address)))
        if conditions:
            ips_query = ips_query.where(and_(*conditions))
        ips_result = await self.db.execute(ips_query)
        unique_ips = ips_result.scalar() or 0

        # Average duration
        duration_query = select(func.avg(AuditLog.duration_ms)).where(
            AuditLog.duration_ms.isnot(None)
        )
        if conditions:
            duration_query = duration_query.where(and_(*conditions))
        duration_result = await self.db.execute(duration_query)
        avg_duration = duration_result.scalar()

        return AuditStats(
            total_logs=total_logs,
            logs_today=logs_today,
            logs_this_week=logs_this_week,
            logs_this_month=logs_this_month,
            actions_by_type=actions_by_type,
            resources_by_type=resources_by_type,
            success_rate=round(success_rate, 2),
            unique_users=unique_users,
            unique_ips=unique_ips,
            average_duration_ms=round(avg_duration, 2) if avg_duration else None,
        )

    async def cleanup_old_logs(
        self,
        days_to_keep: int = 365,
    ) -> int:
        """
        Remove audit logs older than specified days.

        Args:
            days_to_keep: Number of days of logs to retain

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)

        # Count records to delete
        count_query = select(func.count(AuditLog.id)).where(
            AuditLog.timestamp < cutoff_date
        )
        count_result = await self.db.execute(count_query)
        count = count_result.scalar() or 0

        if count > 0:
            # Delete old records
            from sqlalchemy import delete
            delete_query = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
            await self.db.execute(delete_query)
            await self.db.flush()

            logger.info(f"Cleaned up {count} audit logs older than {days_to_keep} days")

        return count


# Import String and Integer for SQLAlchemy type casting
from sqlalchemy import Integer, String


def audit_action(
    action: str,
    resource_type: str,
    resource_id_param: Optional[str] = None,
    capture_old_values: bool = False,
    capture_new_values: bool = True,
):
    """
    Decorator for automatic audit logging of endpoint actions.

    Args:
        action: Action type (CREATE, UPDATE, DELETE, etc.)
        resource_type: Type of resource being acted upon
        resource_id_param: Name of the parameter containing resource ID
        capture_old_values: Whether to capture old values (for updates)
        capture_new_values: Whether to capture new values

    Usage:
        @audit_action(action="CREATE", resource_type="grant")
        async def create_grant(...):
            ...

        @audit_action(action="UPDATE", resource_type="grant", resource_id_param="grant_id", capture_old_values=True)
        async def update_grant(grant_id: UUID, ...):
            ...
    """

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            request = kwargs.get("request")
            db = kwargs.get("db")
            current_user = kwargs.get("current_user")

            # Extract resource ID from kwargs
            resource_id = None
            if resource_id_param and resource_id_param in kwargs:
                resource_id = kwargs[resource_id_param]
                if isinstance(resource_id, str):
                    try:
                        resource_id = uuid.UUID(resource_id)
                    except ValueError:
                        pass

            # Extract request metadata
            ip_address = None
            user_agent = None
            if request:
                ip_address = getattr(request.client, "host", None) if request.client else None
                user_agent = request.headers.get("user-agent", "")[:500]

            # Execute the actual function
            success = True
            error_message = None
            result = None
            new_values = None

            try:
                result = await func(*args, **kwargs)

                # Capture new values from result if needed
                if capture_new_values and result:
                    if hasattr(result, "model_dump"):
                        new_values = result.model_dump(mode="json")
                    elif hasattr(result, "to_dict"):
                        new_values = result.to_dict()
                    elif isinstance(result, dict):
                        new_values = result

                # Extract resource_id from result if not in params
                if not resource_id and result:
                    if hasattr(result, "id"):
                        resource_id = result.id
                    elif isinstance(result, dict) and "id" in result:
                        resource_id = result["id"]

            except Exception as e:
                success = False
                error_message = str(e)
                raise

            finally:
                # Calculate duration
                duration_ms = int((time.time() - start_time) * 1000)

                # Log the action if we have a database session
                if db:
                    try:
                        audit_service = AuditService(db)
                        await audit_service.log_action(
                            action=action,
                            resource_type=resource_type,
                            resource_id=resource_id if isinstance(resource_id, uuid.UUID) else None,
                            user_id=current_user.id if current_user else None,
                            new_values=new_values,
                            ip_address=ip_address,
                            user_agent=user_agent,
                            success=success,
                            error_message=error_message,
                            duration_ms=duration_ms,
                        )
                    except Exception as log_error:
                        logger.error(f"Failed to create audit log: {log_error}")

            return result

        return wrapper

    return decorator


async def log_audit_action(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: Optional[uuid.UUID] = None,
    user_id: Optional[uuid.UUID] = None,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    extra_data: Optional[dict] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    request_id: Optional[str] = None,
) -> AuditLog:
    """
    Convenience function for logging audit actions.

    This is a simpler interface for cases where the decorator isn't suitable.
    """
    service = AuditService(db)
    return await service.log_action(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        user_id=user_id,
        old_values=old_values,
        new_values=new_values,
        ip_address=ip_address,
        user_agent=user_agent,
        extra_data=extra_data,
        success=success,
        error_message=error_message,
        request_id=request_id,
    )
