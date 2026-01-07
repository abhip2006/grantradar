"""
GrantRadar Redis Streams Event Bus
Wrapper for Redis Streams with consumer groups, retries, and dead letter queues
"""
import json
import time
from datetime import datetime
from typing import Any, Callable, Optional, TypeVar
from uuid import UUID, uuid4

import redis.asyncio as redis
import structlog
from pydantic import BaseModel
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.core.config import settings
from backend.core.events import (
    AlertPendingEvent,
    BaseEvent,
    DeadLetterEvent,
    GrantDiscoveredEvent,
    GrantValidatedEvent,
    MatchComputedEvent,
)

logger = structlog.get_logger(__name__)

T = TypeVar("T", bound=BaseEvent)


class StreamNames:
    """Redis Stream names for the GrantRadar event bus."""

    GRANTS_DISCOVERED = "grants:discovered"
    GRANTS_VALIDATED = "grants:validated"
    MATCHES_COMPUTED = "matches:computed"
    ALERTS_PENDING = "alerts:pending"

    # Dead letter queues
    DLQ_GRANTS_DISCOVERED = "dlq:grants:discovered"
    DLQ_GRANTS_VALIDATED = "dlq:grants:validated"
    DLQ_MATCHES_COMPUTED = "dlq:matches:computed"
    DLQ_ALERTS_PENDING = "dlq:alerts:pending"

    @classmethod
    def get_dlq_for_stream(cls, stream: str) -> str:
        """Get the dead letter queue name for a given stream."""
        return f"dlq:{stream}"

    @classmethod
    def all_streams(cls) -> list[str]:
        """Get all main stream names."""
        return [
            cls.GRANTS_DISCOVERED,
            cls.GRANTS_VALIDATED,
            cls.MATCHES_COMPUTED,
            cls.ALERTS_PENDING,
        ]


class ConsumerGroups:
    """Consumer group names for parallel processing."""

    DISCOVERY_VALIDATORS = "discovery-validators"
    CURATION_PROCESSORS = "curation-processors"
    MATCHING_WORKERS = "matching-workers"
    ALERT_DISPATCHERS = "alert-dispatchers"
    DLQ_HANDLERS = "dlq-handlers"


class EventBus:
    """
    Redis Streams event bus for GrantRadar.

    Provides:
    - Event publishing with JSON serialization
    - Consumer groups for parallel processing
    - Automatic retry logic
    - Dead letter queue handling
    - Latency tracking
    - Health monitoring
    """

    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay_base: float = 1.0,
    ):
        """
        Initialize the event bus.

        Args:
            redis_url: Redis connection URL. Defaults to settings.redis_url.
            max_retries: Maximum retry attempts before moving to DLQ.
            retry_delay_base: Base delay in seconds for exponential backoff.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None
        self._max_retries = max_retries
        self._retry_delay_base = retry_delay_base
        self._connected = False

    async def connect(self) -> None:
        """
        Establish connection to Redis.

        Raises:
            redis.ConnectionError: If unable to connect to Redis.
        """
        if self._redis is not None:
            return

        logger.info("connecting_to_redis", redis_url=self._redis_url.split("@")[-1])

        self._redis = redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )

        # Verify connection
        await self._redis.ping()
        self._connected = True
        logger.info("redis_connected")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
            self._connected = False
            logger.info("redis_disconnected")

    async def _ensure_connected(self) -> redis.Redis:
        """Ensure Redis connection is established."""
        if self._redis is None:
            await self.connect()
        return self._redis  # type: ignore

    async def health_check(self) -> dict[str, Any]:
        """
        Check Redis connection health.

        Returns:
            Dictionary with health status and latency.
        """
        try:
            r = await self._ensure_connected()
            start = time.perf_counter()
            await r.ping()
            latency_ms = (time.perf_counter() - start) * 1000

            # Get stream info
            stream_lengths = {}
            for stream in StreamNames.all_streams():
                try:
                    length = await r.xlen(stream)
                    stream_lengths[stream] = length
                except redis.ResponseError:
                    stream_lengths[stream] = 0

            return {
                "status": "healthy",
                "connected": True,
                "latency_ms": round(latency_ms, 2),
                "stream_lengths": stream_lengths,
                "timestamp": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            logger.error("health_check_failed", error=str(e))
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def create_consumer_group(
        self,
        stream: str,
        group: str,
        start_id: str = "0",
    ) -> bool:
        """
        Create a consumer group for a stream.

        Args:
            stream: Stream name.
            group: Consumer group name.
            start_id: Starting message ID ("0" for all, "$" for new only).

        Returns:
            True if created, False if already exists.
        """
        r = await self._ensure_connected()

        try:
            # Create stream if it doesn't exist
            await r.xgroup_create(
                stream,
                group,
                id=start_id,
                mkstream=True,
            )
            logger.info(
                "consumer_group_created",
                stream=stream,
                group=group,
                start_id=start_id,
            )
            return True
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                # Group already exists
                logger.debug("consumer_group_exists", stream=stream, group=group)
                return False
            raise

    async def setup_consumer_groups(self) -> None:
        """Set up all consumer groups for the event bus."""
        stream_group_mapping = [
            (StreamNames.GRANTS_DISCOVERED, ConsumerGroups.DISCOVERY_VALIDATORS),
            (StreamNames.GRANTS_VALIDATED, ConsumerGroups.CURATION_PROCESSORS),
            (StreamNames.MATCHES_COMPUTED, ConsumerGroups.MATCHING_WORKERS),
            (StreamNames.ALERTS_PENDING, ConsumerGroups.ALERT_DISPATCHERS),
            (StreamNames.DLQ_GRANTS_DISCOVERED, ConsumerGroups.DLQ_HANDLERS),
            (StreamNames.DLQ_GRANTS_VALIDATED, ConsumerGroups.DLQ_HANDLERS),
            (StreamNames.DLQ_MATCHES_COMPUTED, ConsumerGroups.DLQ_HANDLERS),
            (StreamNames.DLQ_ALERTS_PENDING, ConsumerGroups.DLQ_HANDLERS),
        ]

        for stream, group in stream_group_mapping:
            await self.create_consumer_group(stream, group)

    def _serialize_event(self, event: BaseEvent) -> dict[str, str]:
        """
        Serialize an event to Redis-compatible format.

        Args:
            event: Pydantic event model.

        Returns:
            Dictionary with string keys and values.
        """
        # Use Pydantic's JSON serialization
        json_str = event.model_dump_json()
        return {
            "payload": json_str,
            "event_type": event.__class__.__name__,
            "published_at": datetime.utcnow().isoformat(),
        }

    def _deserialize_event(
        self,
        data: dict[str, str],
        event_class: type[T],
    ) -> T:
        """
        Deserialize Redis data to an event model.

        Args:
            data: Dictionary from Redis.
            event_class: Target Pydantic model class.

        Returns:
            Deserialized event instance.
        """
        payload = data.get("payload", "{}")
        return event_class.model_validate_json(payload)

    @retry(
        retry=retry_if_exception_type(redis.ConnectionError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def publish(
        self,
        stream: str,
        event: BaseEvent,
        maxlen: Optional[int] = 10000,
    ) -> str:
        """
        Publish an event to a stream.

        Args:
            stream: Target stream name.
            event: Event to publish.
            maxlen: Maximum stream length (approximate, for memory management).

        Returns:
            Message ID assigned by Redis.

        Raises:
            redis.ConnectionError: If unable to connect to Redis.
        """
        r = await self._ensure_connected()

        data = self._serialize_event(event)
        start = time.perf_counter()

        message_id = await r.xadd(
            stream,
            data,
            maxlen=maxlen,
            approximate=True,
        )

        latency_ms = (time.perf_counter() - start) * 1000

        logger.info(
            "event_published",
            stream=stream,
            message_id=message_id,
            event_type=data["event_type"],
            event_id=str(event.event_id),
            latency_ms=round(latency_ms, 2),
        )

        return message_id

    async def publish_grant_discovered(self, event: GrantDiscoveredEvent) -> str:
        """Publish a grant discovered event."""
        return await self.publish(StreamNames.GRANTS_DISCOVERED, event)

    async def publish_grant_validated(self, event: GrantValidatedEvent) -> str:
        """Publish a grant validated event."""
        return await self.publish(StreamNames.GRANTS_VALIDATED, event)

    async def publish_match_computed(self, event: MatchComputedEvent) -> str:
        """Publish a match computed event."""
        return await self.publish(StreamNames.MATCHES_COMPUTED, event)

    async def publish_alert_pending(self, event: AlertPendingEvent) -> str:
        """Publish an alert pending event."""
        return await self.publish(StreamNames.ALERTS_PENDING, event)

    async def consume(
        self,
        stream: str,
        group: str,
        consumer: str,
        count: int = 10,
        block_ms: int = 5000,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        Consume messages from a stream using consumer groups.

        Args:
            stream: Stream name.
            group: Consumer group name.
            consumer: Consumer identifier.
            count: Maximum messages to read.
            block_ms: Block timeout in milliseconds.

        Returns:
            List of (message_id, data) tuples.
        """
        r = await self._ensure_connected()
        start = time.perf_counter()

        try:
            # Read new messages for this consumer
            response = await r.xreadgroup(
                groupname=group,
                consumername=consumer,
                streams={stream: ">"},
                count=count,
                block=block_ms,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            if not response:
                return []

            # Extract messages from response
            # Response format: [[stream_name, [(msg_id, data), ...]]]
            messages = []
            for stream_data in response:
                stream_name, stream_messages = stream_data
                for msg_id, data in stream_messages:
                    messages.append((msg_id, data))

            if messages:
                logger.debug(
                    "messages_consumed",
                    stream=stream,
                    group=group,
                    consumer=consumer,
                    count=len(messages),
                    latency_ms=round(latency_ms, 2),
                )

            return messages

        except redis.ResponseError as e:
            if "NOGROUP" in str(e):
                logger.warning(
                    "consumer_group_not_found",
                    stream=stream,
                    group=group,
                )
                await self.create_consumer_group(stream, group)
                return []
            raise

    async def consume_pending(
        self,
        stream: str,
        group: str,
        consumer: str,
        min_idle_time_ms: int = 60000,
        count: int = 10,
    ) -> list[tuple[str, dict[str, str]]]:
        """
        Claim and consume pending (unacknowledged) messages.

        This is useful for recovering messages from failed consumers.

        Args:
            stream: Stream name.
            group: Consumer group name.
            consumer: Consumer identifier to claim messages for.
            min_idle_time_ms: Minimum idle time before claiming.
            count: Maximum messages to claim.

        Returns:
            List of (message_id, data) tuples.
        """
        r = await self._ensure_connected()

        try:
            # Get pending message IDs
            pending = await r.xpending_range(
                stream,
                group,
                min="-",
                max="+",
                count=count,
            )

            if not pending:
                return []

            # Filter by idle time and claim messages
            message_ids = [
                msg["message_id"]
                for msg in pending
                if msg["time_since_delivered"] >= min_idle_time_ms
            ]

            if not message_ids:
                return []

            # Claim the messages
            claimed = await r.xclaim(
                stream,
                group,
                consumer,
                min_idle_time=min_idle_time_ms,
                message_ids=message_ids,
            )

            logger.info(
                "pending_messages_claimed",
                stream=stream,
                group=group,
                consumer=consumer,
                claimed_count=len(claimed),
            )

            return [(msg_id, data) for msg_id, data in claimed if data]

        except redis.ResponseError as e:
            logger.error("claim_pending_failed", error=str(e))
            return []

    async def acknowledge(
        self,
        stream: str,
        group: str,
        message_id: str,
    ) -> bool:
        """
        Acknowledge successful message processing.

        Args:
            stream: Stream name.
            group: Consumer group name.
            message_id: Message ID to acknowledge.

        Returns:
            True if acknowledged successfully.
        """
        r = await self._ensure_connected()

        ack_count = await r.xack(stream, group, message_id)

        if ack_count > 0:
            logger.debug(
                "message_acknowledged",
                stream=stream,
                group=group,
                message_id=message_id,
            )
            return True

        return False

    async def move_to_dlq(
        self,
        stream: str,
        group: str,
        message_id: str,
        original_data: dict[str, str],
        error: Exception,
        failure_count: int,
    ) -> str:
        """
        Move a failed message to the dead letter queue.

        Args:
            stream: Original stream name.
            group: Consumer group name.
            message_id: Original message ID.
            original_data: Original message data.
            error: Exception that caused the failure.
            failure_count: Number of processing attempts.

        Returns:
            Message ID in the DLQ.
        """
        r = await self._ensure_connected()

        # Create DLQ event
        dlq_event = DeadLetterEvent(
            event_id=uuid4(),
            original_stream=stream,
            original_message_id=message_id,
            original_payload=json.loads(original_data.get("payload", "{}")),
            error_message=str(error),
            error_type=error.__class__.__name__,
            failure_count=failure_count,
            first_failure_at=datetime.utcnow(),
            last_failure_at=datetime.utcnow(),
        )

        dlq_stream = StreamNames.get_dlq_for_stream(stream)
        dlq_message_id = await self.publish(dlq_stream, dlq_event)

        # Acknowledge the original message to remove it from pending
        await self.acknowledge(stream, group, message_id)

        logger.warning(
            "message_moved_to_dlq",
            original_stream=stream,
            original_message_id=message_id,
            dlq_stream=dlq_stream,
            dlq_message_id=dlq_message_id,
            error_type=error.__class__.__name__,
            failure_count=failure_count,
        )

        return dlq_message_id

    async def process_with_retry(
        self,
        stream: str,
        group: str,
        message_id: str,
        data: dict[str, str],
        processor: Callable[[dict[str, str]], Any],
    ) -> bool:
        """
        Process a message with automatic retry and DLQ handling.

        Args:
            stream: Stream name.
            group: Consumer group name.
            message_id: Message ID.
            data: Message data.
            processor: Async function to process the message.

        Returns:
            True if processed successfully, False if moved to DLQ.
        """
        # Track retry count in message metadata
        retry_count = int(data.get("_retry_count", "0"))

        try:
            await processor(data)
            await self.acknowledge(stream, group, message_id)
            return True

        except Exception as e:
            retry_count += 1
            logger.error(
                "message_processing_failed",
                stream=stream,
                message_id=message_id,
                error=str(e),
                retry_count=retry_count,
                max_retries=self._max_retries,
            )

            if retry_count >= self._max_retries:
                await self.move_to_dlq(
                    stream,
                    group,
                    message_id,
                    data,
                    e,
                    retry_count,
                )
                return False

            # For retry, we acknowledge the current message and republish
            # with incremented retry count
            r = await self._ensure_connected()
            data["_retry_count"] = str(retry_count)
            data["_last_error"] = str(e)
            data["_last_retry_at"] = datetime.utcnow().isoformat()

            await r.xadd(stream, data)
            await self.acknowledge(stream, group, message_id)

            logger.info(
                "message_requeued_for_retry",
                stream=stream,
                message_id=message_id,
                retry_count=retry_count,
            )

            return False

    async def get_stream_info(self, stream: str) -> dict[str, Any]:
        """
        Get detailed information about a stream.

        Args:
            stream: Stream name.

        Returns:
            Dictionary with stream information.
        """
        r = await self._ensure_connected()

        try:
            info = await r.xinfo_stream(stream)
            groups = await r.xinfo_groups(stream)

            return {
                "stream": stream,
                "length": info.get("length", 0),
                "first_entry": info.get("first-entry"),
                "last_entry": info.get("last-entry"),
                "groups": [
                    {
                        "name": g.get("name"),
                        "consumers": g.get("consumers"),
                        "pending": g.get("pending"),
                        "last_delivered_id": g.get("last-delivered-id"),
                    }
                    for g in groups
                ],
            }
        except redis.ResponseError as e:
            if "no such key" in str(e).lower():
                return {"stream": stream, "length": 0, "groups": []}
            raise

    async def get_pending_count(
        self,
        stream: str,
        group: str,
    ) -> int:
        """
        Get count of pending (unacknowledged) messages.

        Args:
            stream: Stream name.
            group: Consumer group name.

        Returns:
            Number of pending messages.
        """
        r = await self._ensure_connected()

        try:
            pending = await r.xpending(stream, group)
            return pending.get("pending", 0) if pending else 0
        except redis.ResponseError:
            return 0

    async def trim_stream(
        self,
        stream: str,
        maxlen: int,
        approximate: bool = True,
    ) -> int:
        """
        Trim a stream to a maximum length.

        Args:
            stream: Stream name.
            maxlen: Maximum length to keep.
            approximate: Use approximate trimming for performance.

        Returns:
            Number of messages removed.
        """
        r = await self._ensure_connected()

        before_len = await r.xlen(stream)
        await r.xtrim(stream, maxlen=maxlen, approximate=approximate)
        after_len = await r.xlen(stream)

        removed = before_len - after_len
        if removed > 0:
            logger.info(
                "stream_trimmed",
                stream=stream,
                removed=removed,
                new_length=after_len,
            )

        return removed


# Global event bus instance
_event_bus: Optional[EventBus] = None


async def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.

    Returns:
        EventBus instance.
    """
    global _event_bus

    if _event_bus is None:
        _event_bus = EventBus()
        await _event_bus.connect()
        await _event_bus.setup_consumer_groups()

    return _event_bus


async def close_event_bus() -> None:
    """Close the global event bus connection."""
    global _event_bus

    if _event_bus is not None:
        await _event_bus.disconnect()
        _event_bus = None
