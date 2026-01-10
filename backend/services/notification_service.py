"""In-app notification service for managing user notifications."""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from uuid import UUID

import structlog
from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Notification, User
from backend.core.exceptions import NotFoundError


logger = structlog.get_logger(__name__)


# Notification type constants
class NotificationType:
    """Constants for notification types."""

    TEAM_INVITE_RECEIVED = "team_invite_received"
    TEAM_INVITE_ACCEPTED = "team_invite_accepted"
    TEAM_INVITE_DECLINED = "team_invite_declined"
    TEAM_ROLE_CHANGED = "team_role_changed"
    TEAM_MEMBER_REMOVED = "team_member_removed"
    TEAM_MEMBER_JOINED = "team_member_joined"
    DEADLINE_REMINDER = "deadline_reminder"
    GRANT_MATCH = "grant_match"
    SYSTEM_ALERT = "system_alert"


class InAppNotificationService:
    """
    Service for managing in-app notifications.

    Provides methods to create, retrieve, mark as read, and delete
    notifications for users. Separate from WebSocket real-time notifications.
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize the notification service.

        Args:
            db: Async database session.
        """
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        metadata: Optional[dict] = None,
        action_url: Optional[str] = None,
    ) -> Notification:
        """
        Create a new notification for a user.

        Args:
            user_id: ID of the user to notify.
            type: Notification type (e.g., 'team_invite_received').
            title: Notification title.
            message: Notification message content.
            metadata: Optional additional data.
            action_url: Optional URL for click action.

        Returns:
            Created Notification record.
        """
        notification = Notification(
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            metadata_=metadata,
            action_url=action_url,
            read=False,
        )
        self.db.add(notification)
        await self.db.commit()
        await self.db.refresh(notification)

        logger.info(
            "notification_created",
            notification_id=str(notification.id),
            user_id=str(user_id),
            type=type,
        )

        return notification

    async def get_notifications(
        self,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Notification], int]:
        """
        Get notifications for a user with pagination.

        Args:
            user_id: ID of the user.
            unread_only: If True, only return unread notifications.
            limit: Maximum number of notifications to return.
            offset: Number of notifications to skip.

        Returns:
            Tuple of (notifications list, total count).
        """
        # Build base query
        query = select(Notification).where(Notification.user_id == user_id)

        if unread_only:
            query = query.where(not Notification.read)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Apply pagination and ordering
        query = query.order_by(Notification.created_at.desc()).offset(offset).limit(limit)

        result = await self.db.execute(query)
        notifications = list(result.scalars().all())

        return notifications, total

    async def get_unread_count(self, user_id: UUID) -> int:
        """
        Get the count of unread notifications for a user.

        Args:
            user_id: ID of the user.

        Returns:
            Count of unread notifications.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.user_id == user_id,
                    not Notification.read,
                )
            )
        )
        return result.scalar() or 0

    async def mark_as_read(
        self,
        user_id: UUID,
        notification_id: UUID,
    ) -> Notification:
        """
        Mark a specific notification as read.

        Args:
            user_id: ID of the user (for ownership verification).
            notification_id: ID of the notification to mark.

        Returns:
            Updated Notification record.

        Raises:
            NotFoundError: If notification not found or doesn't belong to user.
        """
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise NotFoundError("Notification", str(notification_id))

        if not notification.read:
            notification.read = True
            notification.read_at = datetime.now(timezone.utc)
            await self.db.commit()
            await self.db.refresh(notification)

        return notification

    async def mark_all_as_read(self, user_id: UUID) -> int:
        """
        Mark all notifications as read for a user.

        Args:
            user_id: ID of the user.

        Returns:
            Number of notifications marked as read.
        """
        # Get unread notifications
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.user_id == user_id,
                    not Notification.read,
                )
            )
        )
        notifications = result.scalars().all()

        now = datetime.now(timezone.utc)
        count = 0

        for notification in notifications:
            notification.read = True
            notification.read_at = now
            count += 1

        if count > 0:
            await self.db.commit()
            logger.info(
                "notifications_marked_read",
                user_id=str(user_id),
                count=count,
            )

        return count

    async def delete_notification(
        self,
        user_id: UUID,
        notification_id: UUID,
    ) -> None:
        """
        Delete a specific notification.

        Args:
            user_id: ID of the user (for ownership verification).
            notification_id: ID of the notification to delete.

        Raises:
            NotFoundError: If notification not found or doesn't belong to user.
        """
        result = await self.db.execute(
            select(Notification).where(
                and_(
                    Notification.id == notification_id,
                    Notification.user_id == user_id,
                )
            )
        )
        notification = result.scalar_one_or_none()

        if not notification:
            raise NotFoundError("Notification", str(notification_id))

        await self.db.delete(notification)
        await self.db.commit()

        logger.info(
            "notification_deleted",
            notification_id=str(notification_id),
            user_id=str(user_id),
        )

    async def delete_old_notifications(self, days: int = 30) -> int:
        """
        Delete old read notifications for cleanup.

        Args:
            days: Delete read notifications older than this many days.

        Returns:
            Number of notifications deleted.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get count first
        count_result = await self.db.execute(
            select(func.count())
            .select_from(Notification)
            .where(
                and_(
                    Notification.read,
                    Notification.created_at < cutoff,
                )
            )
        )
        count = count_result.scalar() or 0

        if count > 0:
            await self.db.execute(
                delete(Notification).where(
                    and_(
                        Notification.read,
                        Notification.created_at < cutoff,
                    )
                )
            )
            await self.db.commit()

            logger.info(
                "old_notifications_deleted",
                count=count,
                cutoff_days=days,
            )

        return count

    async def notify_team_event(
        self,
        event_type: str,
        actor: User,
        target_user_id: UUID,
        entity_name: str,
        metadata: Optional[dict] = None,
    ) -> Optional[Notification]:
        """
        Create a notification for a team event.

        Helper method to create notifications for common team events
        like invitations, role changes, and member actions.

        Args:
            event_type: Type of team event (use NotificationType constants).
            actor: User who triggered the event.
            target_user_id: User to notify.
            entity_name: Name of the related entity (e.g., team name, email).
            metadata: Additional event metadata.

        Returns:
            Created Notification or None if same user as target.
        """
        # Don't notify the actor about their own actions
        if actor.id == target_user_id:
            return None

        actor_name = actor.name or actor.email

        # Build notification content based on event type
        title, message, action_url = self._get_team_event_content(event_type, actor_name, entity_name, metadata)

        # Merge event-specific metadata
        full_metadata = {
            "actor_id": str(actor.id),
            "actor_name": actor_name,
            "actor_email": actor.email,
            **(metadata or {}),
        }

        return await self.create_notification(
            user_id=target_user_id,
            type=event_type,
            title=title,
            message=message,
            metadata=full_metadata,
            action_url=action_url,
        )

    def _get_team_event_content(
        self,
        event_type: str,
        actor_name: str,
        entity_name: str,
        metadata: Optional[dict] = None,
    ) -> tuple[str, str, Optional[str]]:
        """
        Get notification content for a team event type.

        Args:
            event_type: Type of team event.
            actor_name: Name of the user who triggered the event.
            entity_name: Related entity name.
            metadata: Additional metadata for context.

        Returns:
            Tuple of (title, message, action_url).
        """
        action_url = "/team"  # Default action URL

        if event_type == NotificationType.TEAM_INVITE_RECEIVED:
            title = "Team Invitation"
            message = f"{actor_name} has invited you to join their team."
            action_url = "/team/invitations"

        elif event_type == NotificationType.TEAM_INVITE_ACCEPTED:
            title = "Invitation Accepted"
            message = f"{entity_name} has accepted your team invitation."

        elif event_type == NotificationType.TEAM_INVITE_DECLINED:
            title = "Invitation Declined"
            message = f"{entity_name} has declined your team invitation."

        elif event_type == NotificationType.TEAM_ROLE_CHANGED:
            new_role = metadata.get("new_role", "member") if metadata else "member"
            title = "Role Updated"
            message = f"Your role has been changed to {new_role} by {actor_name}."

        elif event_type == NotificationType.TEAM_MEMBER_REMOVED:
            title = "Removed from Team"
            message = f"You have been removed from {actor_name}'s team."
            action_url = "/dashboard"

        elif event_type == NotificationType.TEAM_MEMBER_JOINED:
            title = "New Team Member"
            message = f"{entity_name} has joined your team."

        else:
            title = "Team Update"
            message = f"A team event occurred involving {entity_name}."

        return title, message, action_url
