"""
Audit Logging API Endpoints
Admin endpoints for viewing and exporting audit logs.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, Response, status

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import User
from backend.schemas.audit import (
    AuditExportFormat,
    AuditLogFilters,
    AuditLogListResponse,
    AuditLogResponse,
    AuditStats,
    ResourceHistory,
    UserActivitySummary,
)
from backend.services.audit import AuditService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/audit", tags=["Audit Logs"])


def require_admin(current_user: User) -> User:
    """
    Verify user has admin privileges.

    For now, all authenticated users can access audit logs.
    In production, you'd check for an is_admin flag or role.
    """
    # TODO: Add proper admin check when admin role is implemented
    # if not current_user.is_admin:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="Admin privileges required"
    #     )
    return current_user


@router.get(
    "",
    response_model=AuditLogListResponse,
    summary="List audit logs",
    description="List audit logs with optional filters. Admin only.",
)
async def list_audit_logs(
    request: Request,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    actions: Optional[str] = Query(None, description="Comma-separated list of actions"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_types: Optional[str] = Query(None, description="Comma-separated resource types"),
    resource_id: Optional[UUID] = Query(None, description="Filter by resource ID"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter until this date"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    search: Optional[str] = Query(None, description="Search in extra_data and errors"),
    request_id: Optional[str] = Query(None, description="Filter by request ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> AuditLogListResponse:
    """
    List audit logs with filtering and pagination.

    Available filters:
    - user_id: Filter by specific user
    - action: Filter by action type (CREATE, UPDATE, DELETE, LOGIN, etc.)
    - resource_type: Filter by resource type (grant, user, team, etc.)
    - success: Filter by success/failure
    - start_date/end_date: Date range filter
    - search: Search in extra_data and error messages
    """
    require_admin(current_user)

    # Build filters
    filters = AuditLogFilters(
        user_id=user_id,
        action=action,
        actions=actions.split(",") if actions else None,
        resource_type=resource_type,
        resource_types=resource_types.split(",") if resource_types else None,
        resource_id=resource_id,
        success=success,
        start_date=start_date,
        end_date=end_date,
        ip_address=ip_address,
        search_query=search,
        request_id=request_id,
    )

    audit_service = AuditService(db)
    logs, total = await audit_service.get_audit_logs(
        filters=filters,
        page=page,
        page_size=page_size,
    )

    total_pages = (total + page_size - 1) // page_size

    return AuditLogListResponse(
        items=logs,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get(
    "/stats",
    response_model=AuditStats,
    summary="Get audit statistics",
    description="Get aggregated audit statistics. Admin only.",
)
async def get_audit_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
) -> AuditStats:
    """
    Get aggregated audit statistics.

    Returns metrics including:
    - Total log count
    - Logs by time period (today, week, month)
    - Actions by type breakdown
    - Resources by type breakdown
    - Success rate
    - Unique users and IPs
    - Average action duration
    """
    require_admin(current_user)

    audit_service = AuditService(db)
    return await audit_service.get_audit_stats(
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/user/{user_id}",
    response_model=UserActivitySummary,
    summary="Get user activity",
    description="Get activity summary for a specific user. Admin only.",
)
async def get_user_activity(
    user_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    start_date: Optional[datetime] = Query(None, description="Start of time range"),
    end_date: Optional[datetime] = Query(None, description="End of time range"),
) -> UserActivitySummary:
    """
    Get activity summary for a specific user.

    Returns:
    - Total actions performed
    - Success/failure counts
    - Actions breakdown by type
    - Resources breakdown by type
    - First and last activity timestamps
    - Unique IP addresses used
    """
    require_admin(current_user)

    audit_service = AuditService(db)
    return await audit_service.get_user_activity(
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=ResourceHistory,
    summary="Get resource history",
    description="Get change history for a specific resource. Admin only.",
)
async def get_resource_history(
    resource_type: str,
    resource_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
) -> ResourceHistory:
    """
    Get change history for a specific resource.

    Returns:
    - Full change history with old/new values
    - Creation information (when, by whom)
    - Last modification information
    - Total number of changes
    """
    require_admin(current_user)

    audit_service = AuditService(db)
    return await audit_service.get_resource_history(
        resource_type=resource_type,
        resource_id=resource_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/export",
    summary="Export audit logs",
    description="Export audit logs as CSV or JSON. Admin only.",
)
async def export_audit_logs(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    format: AuditExportFormat = Query(AuditExportFormat.CSV, description="Export format"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    start_date: Optional[datetime] = Query(None, description="Filter from this date"),
    end_date: Optional[datetime] = Query(None, description="Filter until this date"),
    include_details: bool = Query(True, description="Include old/new values and extra_data"),
    max_records: int = Query(10000, le=100000, description="Maximum records to export"),
) -> Response:
    """
    Export audit logs for compliance or analysis.

    Supports CSV and JSON formats. Large exports may take time.
    Maximum 100,000 records per export.
    """
    require_admin(current_user)

    # Build filters
    filters = AuditLogFilters(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        success=success,
        start_date=start_date,
        end_date=end_date,
    )

    audit_service = AuditService(db)
    content, filename = await audit_service.export_audit_logs(
        format=format,
        filters=filters,
        include_details=include_details,
        max_records=max_records,
    )

    # Set appropriate content type
    if format == AuditExportFormat.JSON:
        content_type = "application/json"
    else:
        content_type = "text/csv"

    return Response(
        content=content,
        media_type=content_type,
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )


@router.get(
    "/{log_id}",
    response_model=AuditLogResponse,
    summary="Get audit log entry",
    description="Get a specific audit log entry by ID. Admin only.",
)
async def get_audit_log(
    log_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> AuditLogResponse:
    """
    Get a specific audit log entry by ID.
    """
    require_admin(current_user)

    audit_service = AuditService(db)

    # Get single log entry
    filters = AuditLogFilters()
    logs, _ = await audit_service.get_audit_logs(
        filters=filters,
        page=1,
        page_size=1,
    )

    # Filter by ID (since we don't have direct ID filter in base query)
    from sqlalchemy import select
    from backend.models.audit import AuditLog

    result = await db.execute(select(AuditLog).where(AuditLog.id == log_id))
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log entry {log_id} not found",
        )

    return AuditLogResponse(
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


@router.delete(
    "/cleanup",
    summary="Cleanup old audit logs",
    description="Remove audit logs older than specified days. Admin only.",
)
async def cleanup_audit_logs(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    days_to_keep: int = Query(365, ge=30, le=3650, description="Days of logs to retain"),
) -> dict:
    """
    Remove old audit logs for storage management.

    Minimum retention is 30 days, maximum is 10 years.
    This operation is irreversible.
    """
    require_admin(current_user)

    audit_service = AuditService(db)
    deleted_count = await audit_service.cleanup_old_logs(days_to_keep=days_to_keep)

    return {
        "message": f"Cleaned up {deleted_count} audit logs older than {days_to_keep} days",
        "deleted_count": deleted_count,
    }
