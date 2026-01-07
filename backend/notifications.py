"""
GrantRadar Notification Service
Service for triggering WebSocket events from Celery workers and other processes.

Provides cross-process communication through Redis pub/sub, enabling:
- Celery workers to send real-time notifications
- Multiple WebSocket server instances to stay synchronized
- Decoupled notification logic from event sources
"""
import json
import logging
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

import redis.asyncio as aioredis
import redis as sync_redis
from pydantic import BaseModel

from backend.core.config import settings
from backend.core.events import (
    DeadlineReminderEvent,
    GrantUpdateEvent,
    NewMatchEvent,
    StatsUpdateEvent,
)
from backend.websocket import PubSubChannels

logger = logging.getLogger(__name__)


# =============================================================================
# Notification Service (Async)
# =============================================================================

class NotificationService:
    """
    Async notification service for triggering WebSocket events.

    Use this in FastAPI routes and async contexts.
    Uses Redis pub/sub to communicate with WebSocket servers.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the notification service.

        Args:
            redis_url: Redis connection URL. Defaults to settings.redis_url.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[aioredis.Redis] = None

    async def connect(self) -> None:
        """Establish connection to Redis."""
        if self._redis is not None:
            return

        self._redis = aioredis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("NotificationService connected to Redis")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            logger.info("NotificationService disconnected from Redis")

    async def _ensure_connected(self) -> aioredis.Redis:
        """Ensure Redis connection is established."""
        if self._redis is None:
            await self.connect()
        return self._redis  # type: ignore

    async def _publish(
        self,
        channel: str,
        event_type: str,
        payload: dict[str, Any],
        user_id: Optional[str | UUID] = None,
    ) -> int:
        """
        Publish a message to a Redis pub/sub channel.

        Args:
            channel: Target Redis channel.
            event_type: Type of event (e.g., 'new_match').
            payload: Event payload data.
            user_id: Optional user ID for targeting.

        Returns:
            Number of subscribers that received the message.
        """
        redis_client = await self._ensure_connected()

        message = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            message["user_id"] = str(user_id)

        message_str = json.dumps(message, default=str)
        subscribers = await redis_client.publish(channel, message_str)

        logger.debug(
            f"Published {event_type} to {channel}: "
            f"subscribers={subscribers}, user_id={user_id}"
        )

        return subscribers

    async def notify_new_match(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        match_score: float,
        deadline: Optional[datetime] = None,
        agency: Optional[str] = None,
        amount_range: Optional[str] = None,
    ) -> int:
        """
        Send a new match notification to a user.

        Args:
            user_id: Target user ID.
            grant_id: ID of the matched grant.
            title: Grant title.
            match_score: Match score (0.0 to 1.0).
            deadline: Grant deadline.
            agency: Funding agency name.
            amount_range: Funding amount range (e.g., "$50,000 - $100,000").

        Returns:
            Number of subscribers notified.
        """
        event = NewMatchEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            match_score=match_score,
            deadline=deadline,
            agency=agency,
            amount_range=amount_range,
        )

        channel = PubSubChannels.user_channel(user_id)
        return await self._publish(
            channel=channel,
            event_type="new_match",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    async def notify_deadline_reminder(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        days_remaining: int,
        deadline: datetime,
        url: Optional[str] = None,
    ) -> int:
        """
        Send a deadline reminder notification.

        Args:
            user_id: Target user ID.
            grant_id: ID of the grant.
            title: Grant title.
            days_remaining: Days until deadline.
            deadline: Actual deadline datetime.
            url: URL to the grant.

        Returns:
            Number of subscribers notified.
        """
        event = DeadlineReminderEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            days_remaining=days_remaining,
            deadline=deadline,
            url=url,
        )

        channel = PubSubChannels.user_channel(user_id)
        return await self._publish(
            channel=channel,
            event_type="deadline_soon",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    async def notify_grant_update(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        update_type: str,
        changes: Optional[dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> int:
        """
        Send a grant update notification.

        Args:
            user_id: Target user ID.
            grant_id: ID of the updated grant.
            title: Grant title.
            update_type: Type of update (e.g., 'deadline_changed', 'amount_updated').
            changes: Dictionary of changed fields.
            message: Human-readable update message.

        Returns:
            Number of subscribers notified.
        """
        event = GrantUpdateEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            update_type=update_type,
            changes=changes,
            message=message,
        )

        channel = PubSubChannels.user_channel(user_id)
        return await self._publish(
            channel=channel,
            event_type="grant_update",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    async def notify_stats_update(
        self,
        user_id: str | UUID,
        new_grants_count: int = 0,
        high_matches_count: int = 0,
        pending_deadlines_count: int = 0,
        total_saved_count: Optional[int] = None,
    ) -> int:
        """
        Send dashboard stats update to a user.

        Args:
            user_id: Target user ID.
            new_grants_count: Number of new grants since last check.
            high_matches_count: Number of high-scoring matches.
            pending_deadlines_count: Number of upcoming deadlines.
            total_saved_count: Total saved grants count.

        Returns:
            Number of subscribers notified.
        """
        event = StatsUpdateEvent(
            new_grants_count=new_grants_count,
            high_matches_count=high_matches_count,
            pending_deadlines_count=pending_deadlines_count,
            total_saved_count=total_saved_count,
        )

        channel = PubSubChannels.user_channel(user_id)
        return await self._publish(
            channel=channel,
            event_type="stats_update",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    async def broadcast(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast an event to all connected clients.

        Args:
            event_type: Name of the event.
            data: Event payload.

        Returns:
            Number of subscribers notified.
        """
        return await self._publish(
            channel=PubSubChannels.BROADCAST,
            event_type=event_type,
            payload=data,
        )

    async def notify_user(
        self,
        user_id: str | UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Send a custom event to a specific user.

        Args:
            user_id: Target user ID.
            event_type: Name of the event.
            data: Event payload.

        Returns:
            Number of subscribers notified.
        """
        channel = PubSubChannels.user_channel(user_id)
        return await self._publish(
            channel=channel,
            event_type=event_type,
            payload=data,
            user_id=user_id,
        )


# =============================================================================
# Notification Service (Sync) - For Celery Workers
# =============================================================================

class SyncNotificationService:
    """
    Synchronous notification service for Celery workers.

    Use this in Celery tasks and other synchronous contexts.
    """

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize the sync notification service.

        Args:
            redis_url: Redis connection URL. Defaults to settings.redis_url.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[sync_redis.Redis] = None

    def connect(self) -> None:
        """Establish connection to Redis."""
        if self._redis is not None:
            return

        self._redis = sync_redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        logger.info("SyncNotificationService connected to Redis")

    def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            self._redis.close()
            self._redis = None
            logger.info("SyncNotificationService disconnected from Redis")

    def _ensure_connected(self) -> sync_redis.Redis:
        """Ensure Redis connection is established."""
        if self._redis is None:
            self.connect()
        return self._redis  # type: ignore

    def _publish(
        self,
        channel: str,
        event_type: str,
        payload: dict[str, Any],
        user_id: Optional[str | UUID] = None,
    ) -> int:
        """
        Publish a message to a Redis pub/sub channel.

        Args:
            channel: Target Redis channel.
            event_type: Type of event.
            payload: Event payload data.
            user_id: Optional user ID for targeting.

        Returns:
            Number of subscribers that received the message.
        """
        redis_client = self._ensure_connected()

        message = {
            "event_type": event_type,
            "payload": payload,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if user_id:
            message["user_id"] = str(user_id)

        message_str = json.dumps(message, default=str)
        subscribers = redis_client.publish(channel, message_str)

        logger.debug(
            f"Published {event_type} to {channel}: "
            f"subscribers={subscribers}, user_id={user_id}"
        )

        return subscribers

    def notify_new_match(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        match_score: float,
        deadline: Optional[datetime] = None,
        agency: Optional[str] = None,
        amount_range: Optional[str] = None,
    ) -> int:
        """
        Send a new match notification to a user (sync version).

        Args:
            user_id: Target user ID.
            grant_id: ID of the matched grant.
            title: Grant title.
            match_score: Match score (0.0 to 1.0).
            deadline: Grant deadline.
            agency: Funding agency name.
            amount_range: Funding amount range.

        Returns:
            Number of subscribers notified.
        """
        event = NewMatchEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            match_score=match_score,
            deadline=deadline,
            agency=agency,
            amount_range=amount_range,
        )

        channel = PubSubChannels.user_channel(user_id)
        return self._publish(
            channel=channel,
            event_type="new_match",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    def notify_deadline_reminder(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        days_remaining: int,
        deadline: datetime,
        url: Optional[str] = None,
    ) -> int:
        """
        Send a deadline reminder notification (sync version).

        Args:
            user_id: Target user ID.
            grant_id: ID of the grant.
            title: Grant title.
            days_remaining: Days until deadline.
            deadline: Actual deadline datetime.
            url: URL to the grant.

        Returns:
            Number of subscribers notified.
        """
        event = DeadlineReminderEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            days_remaining=days_remaining,
            deadline=deadline,
            url=url,
        )

        channel = PubSubChannels.user_channel(user_id)
        return self._publish(
            channel=channel,
            event_type="deadline_soon",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    def notify_grant_update(
        self,
        user_id: str | UUID,
        grant_id: str | UUID,
        title: str,
        update_type: str,
        changes: Optional[dict[str, Any]] = None,
        message: Optional[str] = None,
    ) -> int:
        """
        Send a grant update notification (sync version).

        Args:
            user_id: Target user ID.
            grant_id: ID of the updated grant.
            title: Grant title.
            update_type: Type of update.
            changes: Dictionary of changed fields.
            message: Human-readable update message.

        Returns:
            Number of subscribers notified.
        """
        event = GrantUpdateEvent(
            grant_id=UUID(str(grant_id)) if isinstance(grant_id, str) else grant_id,
            title=title,
            update_type=update_type,
            changes=changes,
            message=message,
        )

        channel = PubSubChannels.user_channel(user_id)
        return self._publish(
            channel=channel,
            event_type="grant_update",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    def notify_stats_update(
        self,
        user_id: str | UUID,
        new_grants_count: int = 0,
        high_matches_count: int = 0,
        pending_deadlines_count: int = 0,
        total_saved_count: Optional[int] = None,
    ) -> int:
        """
        Send dashboard stats update (sync version).

        Args:
            user_id: Target user ID.
            new_grants_count: Number of new grants.
            high_matches_count: Number of high-scoring matches.
            pending_deadlines_count: Number of upcoming deadlines.
            total_saved_count: Total saved grants count.

        Returns:
            Number of subscribers notified.
        """
        event = StatsUpdateEvent(
            new_grants_count=new_grants_count,
            high_matches_count=high_matches_count,
            pending_deadlines_count=pending_deadlines_count,
            total_saved_count=total_saved_count,
        )

        channel = PubSubChannels.user_channel(user_id)
        return self._publish(
            channel=channel,
            event_type="stats_update",
            payload=event.model_dump(mode="json"),
            user_id=user_id,
        )

    def broadcast(
        self,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Broadcast an event to all connected clients (sync version).

        Args:
            event_type: Name of the event.
            data: Event payload.

        Returns:
            Number of subscribers notified.
        """
        return self._publish(
            channel=PubSubChannels.BROADCAST,
            event_type=event_type,
            payload=data,
        )

    def notify_user(
        self,
        user_id: str | UUID,
        event_type: str,
        data: dict[str, Any],
    ) -> int:
        """
        Send a custom event to a specific user (sync version).

        Args:
            user_id: Target user ID.
            event_type: Name of the event.
            data: Event payload.

        Returns:
            Number of subscribers notified.
        """
        channel = PubSubChannels.user_channel(user_id)
        return self._publish(
            channel=channel,
            event_type=event_type,
            payload=data,
            user_id=user_id,
        )


# =============================================================================
# Global Instances
# =============================================================================

_notification_service: Optional[NotificationService] = None
_sync_notification_service: Optional[SyncNotificationService] = None


async def get_notification_service() -> NotificationService:
    """
    Get or create the global async notification service.

    Returns:
        NotificationService instance.
    """
    global _notification_service

    if _notification_service is None:
        _notification_service = NotificationService()
        await _notification_service.connect()

    return _notification_service


def get_sync_notification_service() -> SyncNotificationService:
    """
    Get or create the global sync notification service.

    Use this in Celery tasks.

    Returns:
        SyncNotificationService instance.
    """
    global _sync_notification_service

    if _sync_notification_service is None:
        _sync_notification_service = SyncNotificationService()
        _sync_notification_service.connect()

    return _sync_notification_service


async def close_notification_service() -> None:
    """Close the async notification service."""
    global _notification_service

    if _notification_service is not None:
        await _notification_service.disconnect()
        _notification_service = None


def close_sync_notification_service() -> None:
    """Close the sync notification service."""
    global _sync_notification_service

    if _sync_notification_service is not None:
        _sync_notification_service.disconnect()
        _sync_notification_service = None


__all__ = [
    "NotificationService",
    "SyncNotificationService",
    "get_notification_service",
    "get_sync_notification_service",
    "close_notification_service",
    "close_sync_notification_service",
]
