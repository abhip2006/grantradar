"""Notifications API endpoints for managing user notifications."""
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError
from backend.models import Notification
from backend.schemas.notifications import (
    NotificationResponse,
    NotificationListResponse,
    UnreadCountResponse,
    MarkReadResponse,
    DeleteNotificationResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


# =============================================================================
# Helper Functions
# =============================================================================


def _build_notification_response(notification: Notification) -> NotificationResponse:
    """Build a NotificationResponse from a Notification model."""
    return NotificationResponse(
        id=notification.id,
        user_id=notification.user_id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        metadata=notification.metadata_,
        read=notification.read,
        read_at=notification.read_at,
        action_url=notification.action_url,
        created_at=notification.created_at,
    )


async def _get_notification_by_id(
    db: AsyncSession,
    user_id: UUID,
    notification_id: UUID,
) -> Notification:
    """
    Get a notification by ID with ownership check.

    Args:
        db: Database session.
        user_id: ID of the user who owns the notification.
        notification_id: ID of the notification.

    Returns:
        Notification record.

    Raises:
        NotFoundError: If notification not found or ownership mismatch.
    """
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == user_id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise NotFoundError("Notification", str(notification_id))

    return notification


# =============================================================================
# Notification Endpoints
# =============================================================================


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications",
    description="Get all notifications for the current user with optional filtering.",
)
async def list_notifications(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    unread_only: bool = Query(
        False, description="Filter to show only unread notifications"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
) -> NotificationListResponse:
    """
    List all notifications for the current user.

    Returns notifications sorted by most recent first, with optional
    filtering for unread notifications only.
    """
    # Build base query
    query = select(Notification).where(Notification.user_id == current_user.id)

    # Apply unread filter if requested
    if unread_only:
        query = query.where(Notification.read == False)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get unread count (always needed for response)
    unread_query = select(func.count()).where(
        and_(
            Notification.user_id == current_user.id,
            Notification.read == False,
        )
    )
    unread_result = await db.execute(unread_query)
    unread_count = unread_result.scalar() or 0

    # Apply pagination and ordering
    query = (
        query.order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(query)
    notifications = list(result.scalars().all())

    notification_responses = [_build_notification_response(n) for n in notifications]

    return NotificationListResponse(
        notifications=notification_responses,
        total=total,
        unread_count=unread_count,
        has_more=(offset + len(notifications)) < total,
    )


@router.get(
    "/unread-count",
    response_model=UnreadCountResponse,
    summary="Get unread notification count",
    description="Get the count of unread notifications for the current user.",
)
async def get_unread_count(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> UnreadCountResponse:
    """
    Get the count of unread notifications.

    This is a lightweight endpoint for displaying notification badges.
    """
    result = await db.execute(
        select(func.count()).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read == False,
            )
        )
    )
    count = result.scalar() or 0

    return UnreadCountResponse(count=count)


@router.patch(
    "/{notification_id}/read",
    response_model=MarkReadResponse,
    summary="Mark notification as read",
    description="Mark a single notification as read.",
)
async def mark_notification_read(
    notification_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MarkReadResponse:
    """
    Mark a single notification as read.

    Updates the read status and records the timestamp.
    """
    notification = await _get_notification_by_id(db, current_user.id, notification_id)

    if not notification.read:
        notification.read = True
        notification.read_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(notification)

        logger.info(f"Notification marked as read: {notification_id}")

    return MarkReadResponse(
        success=True,
        message="Notification marked as read",
        notification=_build_notification_response(notification),
    )


@router.post(
    "/mark-all-read",
    response_model=MarkReadResponse,
    summary="Mark all notifications as read",
    description="Mark all unread notifications for the current user as read.",
)
async def mark_all_notifications_read(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MarkReadResponse:
    """
    Mark all unread notifications as read.

    Bulk updates all unread notifications for the current user.
    """
    # Get all unread notifications for this user
    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.user_id == current_user.id,
                Notification.read == False,
            )
        )
    )
    notifications = list(result.scalars().all())

    updated_count = 0
    now = datetime.now(timezone.utc)

    for notification in notifications:
        notification.read = True
        notification.read_at = now
        updated_count += 1

    if updated_count > 0:
        await db.commit()
        logger.info(
            f"Marked {updated_count} notifications as read for user {current_user.id}"
        )

    return MarkReadResponse(
        success=True,
        message=f"Marked {updated_count} notifications as read",
        updated_count=updated_count,
    )


@router.delete(
    "/{notification_id}",
    response_model=DeleteNotificationResponse,
    summary="Delete notification",
    description="Delete a notification.",
)
async def delete_notification(
    notification_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> DeleteNotificationResponse:
    """
    Delete a notification.

    Permanently removes the notification from the database.
    """
    notification = await _get_notification_by_id(db, current_user.id, notification_id)

    await db.delete(notification)
    await db.commit()

    logger.info(f"Notification deleted: {notification_id}")

    return DeleteNotificationResponse(
        success=True,
        message="Notification deleted successfully",
    )
