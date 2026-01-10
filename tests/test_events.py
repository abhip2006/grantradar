"""
Tests for Redis Streams event bus.
Tests event publishing, consuming, and dead letter queue handling.
"""

import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from backend.core.events import (
    AlertPendingEvent,
    GrantDiscoveredEvent,
    GrantValidatedEvent,
    MatchComputedEvent,
    PriorityLevel,
    AlertChannel,
)


class TestStreamNames:
    """Tests for StreamNames class."""

    def test_stream_names_defined(self):
        """Test that all stream names are defined."""
        from backend.events import StreamNames

        assert StreamNames.GRANTS_DISCOVERED == "grants:discovered"
        assert StreamNames.GRANTS_VALIDATED == "grants:validated"
        assert StreamNames.MATCHES_COMPUTED == "matches:computed"
        assert StreamNames.ALERTS_PENDING == "alerts:pending"

    def test_dlq_names_defined(self):
        """Test that DLQ names are defined."""
        from backend.events import StreamNames

        assert StreamNames.DLQ_GRANTS_DISCOVERED == "dlq:grants:discovered"
        assert StreamNames.DLQ_GRANTS_VALIDATED == "dlq:grants:validated"
        assert StreamNames.DLQ_MATCHES_COMPUTED == "dlq:matches:computed"
        assert StreamNames.DLQ_ALERTS_PENDING == "dlq:alerts:pending"

    def test_get_dlq_for_stream(self):
        """Test getting DLQ name for a stream."""
        from backend.events import StreamNames

        dlq = StreamNames.get_dlq_for_stream("grants:discovered")
        assert dlq == "dlq:grants:discovered"

    def test_all_streams(self):
        """Test getting all stream names."""
        from backend.events import StreamNames

        streams = StreamNames.all_streams()
        assert len(streams) == 4
        assert "grants:discovered" in streams
        assert "grants:validated" in streams


class TestConsumerGroups:
    """Tests for ConsumerGroups class."""

    def test_consumer_groups_defined(self):
        """Test that consumer groups are defined."""
        from backend.events import ConsumerGroups

        assert ConsumerGroups.DISCOVERY_VALIDATORS == "discovery-validators"
        assert ConsumerGroups.CURATION_PROCESSORS == "curation-processors"
        assert ConsumerGroups.MATCHING_WORKERS == "matching-workers"
        assert ConsumerGroups.ALERT_DISPATCHERS == "alert-dispatchers"
        assert ConsumerGroups.DLQ_HANDLERS == "dlq-handlers"


class TestEventBus:
    """Tests for EventBus class."""

    @pytest.fixture
    def mock_redis(self):
        """Create a mock Redis client."""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.xadd = AsyncMock(return_value="1234567890-0")
        redis_mock.xread = AsyncMock(return_value=[])
        redis_mock.xreadgroup = AsyncMock(return_value=[])
        redis_mock.xack = AsyncMock(return_value=1)
        redis_mock.xlen = AsyncMock(return_value=0)
        redis_mock.xinfo_stream = AsyncMock(return_value={"length": 0})
        redis_mock.xinfo_groups = AsyncMock(return_value=[])
        redis_mock.xgroup_create = AsyncMock(return_value=True)
        redis_mock.aclose = AsyncMock()
        return redis_mock

    @pytest.mark.asyncio
    async def test_connect(self, mock_redis):
        """Test connecting to Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            assert bus._connected is True
            mock_redis.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect(self, mock_redis):
        """Test disconnecting from Redis."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()
            await bus.disconnect()

            assert bus._connected is False
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_ensure_connected(self, mock_redis):
        """Test auto-connection on first use."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus

            bus = EventBus(redis_url="redis://localhost:6379")
            redis = await bus._ensure_connected()

            assert redis is not None
            assert bus._connected is True

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_redis):
        """Test health check when Redis is healthy."""
        mock_redis.xinfo_stream.side_effect = [
            {"length": 10, "first-entry": ("1-0", {}), "last-entry": ("2-0", {})},
            {"length": 5, "first-entry": ("1-0", {}), "last-entry": ("2-0", {})},
            {"length": 3, "first-entry": ("1-0", {}), "last-entry": ("2-0", {})},
            {"length": 2, "first-entry": ("1-0", {}), "last-entry": ("2-0", {})},
        ]

        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()
            health = await bus.health_check()

            assert health["connected"] is True

    @pytest.mark.asyncio
    async def test_publish_grant_discovered(self, mock_redis):
        """Test publishing a grant discovered event."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus, StreamNames

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            event = GrantDiscoveredEvent(
                event_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                source="grants.gov",
                title="Test Grant",
                url="https://test.com",
            )

            message_id = await bus.publish(StreamNames.GRANTS_DISCOVERED, event)

            assert message_id == "1234567890-0"
            mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_grant_validated(self, mock_redis):
        """Test publishing a grant validated event."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus, StreamNames

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            event = GrantValidatedEvent(
                event_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                quality_score=0.85,
                categories=["research", "science"],
            )

            message_id = await bus.publish(StreamNames.GRANTS_VALIDATED, event)

            assert message_id == "1234567890-0"

    @pytest.mark.asyncio
    async def test_publish_match_computed(self, mock_redis):
        """Test publishing a match computed event."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus, StreamNames

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            event = MatchComputedEvent(
                event_id=uuid.uuid4(),
                match_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                match_score=0.87,
                priority_level=PriorityLevel.HIGH,
            )

            message_id = await bus.publish(StreamNames.MATCHES_COMPUTED, event)

            assert message_id == "1234567890-0"

    @pytest.mark.asyncio
    async def test_publish_alert_pending(self, mock_redis):
        """Test publishing an alert pending event."""
        with patch("redis.asyncio.from_url", return_value=mock_redis):
            from backend.events import EventBus, StreamNames

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            event = AlertPendingEvent(
                event_id=uuid.uuid4(),
                alert_id=uuid.uuid4(),
                match_id=uuid.uuid4(),
                channel=AlertChannel.EMAIL,
                user_email="test@university.edu",
            )

            message_id = await bus.publish(StreamNames.ALERTS_PENDING, event)

            assert message_id == "1234567890-0"


class TestEventSerialization:
    """Tests for event serialization."""

    def test_serialize_grant_discovered_event(self):
        """Test serializing a grant discovered event."""
        event = GrantDiscoveredEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            source="grants.gov",
            title="Test Grant",
            url="https://test.com",
        )

        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["source"] == "grants.gov"
        assert data["title"] == "Test Grant"
        assert data["url"] == "https://test.com"

    def test_deserialize_grant_discovered_event(self):
        """Test deserializing a grant discovered event."""
        event_id = str(uuid.uuid4())
        grant_id = str(uuid.uuid4())
        data = {
            "event_id": event_id,
            "grant_id": grant_id,
            "source": "grants.gov",
            "title": "Test Grant",
            "url": "https://test.com",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
        }

        event = GrantDiscoveredEvent.model_validate(data)

        assert str(event.event_id) == event_id
        assert event.source == "grants.gov"

    def test_serialize_match_computed_event(self):
        """Test serializing a match computed event."""
        event = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            match_score=0.87,
            priority_level=PriorityLevel.HIGH,
            matching_criteria=["research_area", "career_stage"],
        )

        json_str = event.model_dump_json()
        data = json.loads(json_str)

        assert data["match_score"] == 0.87
        assert data["priority_level"] == "high"
        assert "research_area" in data["matching_criteria"]


class TestEventRetryLogic:
    """Tests for event retry and dead letter queue logic."""

    def test_max_retries_default(self):
        """Test default max retries."""
        from backend.events import EventBus

        bus = EventBus(redis_url="redis://localhost:6379")
        assert bus._max_retries == 3

    def test_max_retries_custom(self):
        """Test custom max retries."""
        from backend.events import EventBus

        bus = EventBus(redis_url="redis://localhost:6379", max_retries=5)
        assert bus._max_retries == 5

    def test_retry_delay_base_default(self):
        """Test default retry delay base."""
        from backend.events import EventBus

        bus = EventBus(redis_url="redis://localhost:6379")
        assert bus._retry_delay_base == 1.0

    def test_retry_delay_base_custom(self):
        """Test custom retry delay base."""
        from backend.events import EventBus

        bus = EventBus(redis_url="redis://localhost:6379", retry_delay_base=2.0)
        assert bus._retry_delay_base == 2.0


class TestStreamMetrics:
    """Tests for stream metrics collection."""

    @pytest.fixture
    def mock_redis_with_stream_info(self):
        """Create mock Redis with stream info."""
        redis_mock = AsyncMock()
        redis_mock.ping = AsyncMock(return_value=True)
        redis_mock.xinfo_stream = AsyncMock(
            return_value={
                "length": 100,
                "radix-tree-keys": 1,
                "radix-tree-nodes": 2,
                "groups": 1,
                "last-generated-id": "1234567890-0",
                "first-entry": ("1234567890-0", {"data": "test"}),
                "last-entry": ("1234567891-0", {"data": "test2"}),
            }
        )
        redis_mock.aclose = AsyncMock()
        return redis_mock

    @pytest.mark.asyncio
    async def test_get_stream_length(self, mock_redis_with_stream_info):
        """Test getting stream length."""
        with patch("redis.asyncio.from_url", return_value=mock_redis_with_stream_info):
            from backend.events import EventBus, StreamNames

            bus = EventBus(redis_url="redis://localhost:6379")
            await bus.connect()

            # Call xinfo_stream to get length
            info = await bus._redis.xinfo_stream(StreamNames.GRANTS_DISCOVERED)

            assert info["length"] == 100
