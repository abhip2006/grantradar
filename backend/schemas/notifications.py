"""Notification schemas for API request/response validation."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class NotificationType(str, Enum):
    """Types of notifications."""

    TEAM_INVITE = "team_invite"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    ROLE_CHANGED = "role_changed"
    PERMISSIONS_UPDATED = "permissions_updated"
    DEADLINE_REMINDER = "deadline_reminder"
    APPLICATION_UPDATE = "application_update"
    SYSTEM = "system"


# ============================================================================
# Response Schemas
# ============================================================================


class NotificationResponse(BaseModel):
    """Response schema for a notification."""

    id: UUID = Field(..., description="Unique identifier for the notification")
    user_id: UUID = Field(..., description="User who receives this notification")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message content")
    metadata: Optional[dict[str, Any]] = Field(
        None, description="Additional context data"
    )
    read: bool = Field(..., description="Whether the notification has been read")
    read_at: Optional[datetime] = Field(
        None, description="When the notification was marked as read"
    )
    action_url: Optional[str] = Field(
        None, description="URL to navigate to when notification is clicked"
    )
    created_at: datetime = Field(..., description="When the notification was created")

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response schema for listing notifications."""

    notifications: List[NotificationResponse] = Field(
        ..., description="List of notifications"
    )
    total: int = Field(..., description="Total number of notifications")
    unread_count: int = Field(..., description="Number of unread notifications")
    has_more: bool = Field(..., description="Whether more notifications exist")


class UnreadCountResponse(BaseModel):
    """Response schema for unread notification count."""

    count: int = Field(..., description="Number of unread notifications")


class MarkReadResponse(BaseModel):
    """Response schema for marking notifications as read."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Status message")
    notification: Optional[NotificationResponse] = Field(
        None, description="Updated notification (for single mark read)"
    )
    updated_count: Optional[int] = Field(
        None, description="Number of notifications updated (for mark all read)"
    )


class DeleteNotificationResponse(BaseModel):
    """Response schema for deleting a notification."""

    success: bool = Field(..., description="Whether the deletion succeeded")
    message: str = Field(..., description="Status message")
