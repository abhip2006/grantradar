"""
Tests for notification service.
Tests the notification service for WebSocket events and Redis pub/sub.
"""

import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.events import (
    DeadlineReminderEvent,
    GrantUpdateEvent,
    NewMatchEvent,
    StatsUpdateEvent,
)


class TestNotificationService:
    """Tests for async NotificationService."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.publish = AsyncMock(return_value=1)
        redis_mock.aclose = AsyncMock()
        return redis_mock

    @pytest.mark.asyncio
    async def test_connect(self, mock_redis):
        """Test connecting to Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            assert service._redis is not None

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis):
        """Test disconnecting from Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()
            await service.disconnect()

            assert service._redis is None
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected(self, mock_redis):
        """Test auto-connection on first use."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            # Should auto-connect
            redis = await service._ensure_connected()

            assert redis is not None

    @pytest.mark.asyncio
    async def test_publish(self, mock_redis):
        """Test publishing a message."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            result = await service._publish(
                channel="test_channel",
                event_type="test_event",
                payload={"key": "value"},
                user_id=uuid.uuid4(),
            )

            assert result == 1
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_new_match(self, mock_redis):
        """Test sending a new match notification."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            result = await service.notify_new_match(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Test Grant",
                match_score=0.85,
                agency="NSF",
                amount_range="$100,000 - $500,000",
            )

            assert result == 1
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_deadline_reminder(self, mock_redis):
        """Test sending a deadline reminder notification."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            deadline = datetime.now(timezone.utc) + timedelta(days=3)
            result = await service.notify_deadline_reminder(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Upcoming Grant Deadline",
                days_remaining=3,
                deadline=deadline,
            )

            assert result == 1
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_grant_update(self, mock_redis):
        """Test sending a grant update notification."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            result = await service.notify_grant_update(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Updated Grant",
                update_type="deadline_changed",
                changes={"old": "2025-03-01", "new": "2025-04-01"},
            )

            assert result == 1
            mock_redis.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_stats_update(self, mock_redis):
        """Test sending a stats update notification."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.notifications import NotificationService

            service = NotificationService(redis_url="redis://localhost:6379")
            await service.connect()

            result = await service.notify_stats_update(
                user_id=uuid.uuid4(),
                new_grants_count=5,
                high_matches_count=3,
                pending_deadlines_count=2,
            )

            assert result == 1
            mock_redis.publish.assert_called_once()


class TestSyncNotificationService:
    """Tests for sync NotificationService."""

    @pytest.fixture
    def mock_sync_redis(self):
        """Create a mock sync Redis client."""
        redis_mock = MagicMock()
        redis_mock.publish = MagicMock(return_value=1)
        redis_mock.close = MagicMock()
        return redis_mock

    def test_connect_sync(self, mock_sync_redis):
        """Test connecting to Redis synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()

            assert service._redis is not None

    def test_disconnect_sync(self, mock_sync_redis):
        """Test disconnecting synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()
            service.disconnect()

            assert service._redis is None
            mock_sync_redis.close.assert_called_once()

    def test_notify_new_match_sync(self, mock_sync_redis):
        """Test sending a new match notification synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()

            result = service.notify_new_match(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Test Grant",
                match_score=0.85,
            )

            assert result == 1
            mock_sync_redis.publish.assert_called_once()

    def test_notify_deadline_reminder_sync(self, mock_sync_redis):
        """Test sending a deadline reminder synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()

            deadline = datetime.now(timezone.utc) + timedelta(days=3)
            result = service.notify_deadline_reminder(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Test Grant",
                days_remaining=3,
                deadline=deadline,
            )

            assert result == 1
            mock_sync_redis.publish.assert_called_once()

    def test_notify_grant_update_sync(self, mock_sync_redis):
        """Test sending a grant update synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()

            result = service.notify_grant_update(
                user_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                title="Test Grant",
                update_type="amount_updated",
            )

            assert result == 1
            mock_sync_redis.publish.assert_called_once()

    def test_notify_stats_update_sync(self, mock_sync_redis):
        """Test sending a stats update synchronously."""
        with patch("redis.from_url", return_value=mock_sync_redis):
            from backend.notifications import SyncNotificationService

            service = SyncNotificationService(redis_url="redis://localhost:6379")
            service.connect()

            result = service.notify_stats_update(
                user_id=uuid.uuid4(),
                new_grants_count=10,
                high_matches_count=5,
                pending_deadlines_count=3,
            )

            assert result == 1
            mock_sync_redis.publish.assert_called_once()


class TestNotificationHelpers:
    """Tests for notification helper functions."""

    def test_create_match_notification_payload(self):
        """Test creating a match notification payload."""

        grant_id = uuid.uuid4()
        event = NewMatchEvent(
            grant_id=grant_id,
            title="AI Research Grant",
            match_score=0.89,
            agency="NSF",
            amount_range="$100,000 - $500,000",
        )

        payload = event.model_dump()

        assert str(grant_id) == str(payload["grant_id"])
        assert payload["title"] == "AI Research Grant"
        assert payload["match_score"] == 0.89
        assert payload["agency"] == "NSF"

    def test_create_deadline_reminder_payload(self):
        """Test creating a deadline reminder payload."""

        grant_id = uuid.uuid4()
        deadline = datetime.now(timezone.utc) + timedelta(days=3)
        event = DeadlineReminderEvent(
            grant_id=grant_id,
            title="Upcoming Deadline",
            days_remaining=3,
            deadline=deadline,
        )

        payload = event.model_dump()

        assert str(grant_id) == str(payload["grant_id"])
        assert payload["days_remaining"] == 3

    def test_create_grant_update_payload(self):
        """Test creating a grant update payload."""

        grant_id = uuid.uuid4()
        event = GrantUpdateEvent(
            grant_id=grant_id,
            title="Updated Grant",
            update_type="deadline_changed",
            changes={"old_deadline": "2025-03-01", "new_deadline": "2025-04-01"},
            message="Deadline extended by one month",
        )

        payload = event.model_dump()

        assert payload["update_type"] == "deadline_changed"
        assert payload["message"] == "Deadline extended by one month"

    def test_create_stats_update_payload(self):
        """Test creating a stats update payload."""

        event = StatsUpdateEvent(
            new_grants_count=10,
            high_matches_count=5,
            pending_deadlines_count=3,
            total_saved_count=50,
        )

        payload = event.model_dump()

        assert payload["new_grants_count"] == 10
        assert payload["high_matches_count"] == 5
        assert payload["pending_deadlines_count"] == 3
        assert payload["total_saved_count"] == 50
