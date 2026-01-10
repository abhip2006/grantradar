"""
Base Discovery Agent
Abstract base class for all grant discovery agents with common functionality.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional
import hashlib
import json

import redis
import structlog

from backend.core.config import settings


class DiscoveryAgent(ABC):
    """
    Base class for grant discovery agents.

    Provides common functionality for:
    - Redis stream publishing
    - Duplicate detection via seen hashes
    - Error handling patterns
    - Structured logging setup
    - Last check time tracking
    """

    # Redis stream for discovered grants
    GRANTS_STREAM = "grants:discovered"
    # Redis key prefix for tracking seen grants
    SEEN_GRANTS_PREFIX = "grants:seen:"
    # Redis key prefix for last check time
    LAST_CHECK_PREFIX = "discovery:last_check:"
    # Default TTL for seen grant hashes (30 days)
    SEEN_GRANT_TTL_SECONDS = 60 * 60 * 24 * 30

    def __init__(self, source_name: str):
        """
        Initialize discovery agent.

        Args:
            source_name: Unique identifier for this data source (e.g., 'nsf', 'nih', 'grants_gov')
        """
        self.source_name = source_name
        self.logger = structlog.get_logger().bind(agent="discovery", source=source_name)
        self._redis_client: Optional[redis.Redis] = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy-loaded Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis_client

    def _get_seen_key(self) -> str:
        """Get Redis key for tracking seen grants for this source."""
        return f"{self.SEEN_GRANTS_PREFIX}{self.source_name}"

    def _get_last_check_key(self) -> str:
        """Get Redis key for last check timestamp."""
        return f"{self.LAST_CHECK_PREFIX}{self.source_name}"

    def _compute_grant_hash(self, external_id: str, title: str) -> str:
        """
        Compute a unique hash for a grant to detect duplicates.

        Args:
            external_id: External identifier from the source
            title: Grant title

        Returns:
            SHA-256 hash string
        """
        content = f"{self.source_name}:{external_id}:{title}"
        return hashlib.sha256(content.encode()).hexdigest()

    def is_duplicate(self, external_id: str, title: str) -> bool:
        """
        Check if a grant has already been processed.

        Args:
            external_id: External identifier from the source
            title: Grant title

        Returns:
            True if grant has been seen before
        """
        grant_hash = self._compute_grant_hash(external_id, title)
        seen_key = self._get_seen_key()

        return self.redis_client.sismember(seen_key, grant_hash)

    def mark_as_seen(self, external_id: str, title: str) -> None:
        """
        Mark a grant as processed to prevent reprocessing.

        Args:
            external_id: External identifier from the source
            title: Grant title
        """
        grant_hash = self._compute_grant_hash(external_id, title)
        seen_key = self._get_seen_key()

        # Add to set and set TTL on the key
        self.redis_client.sadd(seen_key, grant_hash)
        # Refresh TTL each time we add
        self.redis_client.expire(seen_key, self.SEEN_GRANT_TTL_SECONDS)

    def get_last_check_time(self) -> Optional[datetime]:
        """
        Get the last time this source was checked.

        Returns:
            Datetime of last check, or None if never checked
        """
        last_check_key = self._get_last_check_key()
        timestamp_str = self.redis_client.get(last_check_key)

        if timestamp_str:
            return datetime.fromisoformat(timestamp_str)
        return None

    def set_last_check_time(self, check_time: Optional[datetime] = None) -> None:
        """
        Update the last check time for this source.

        Args:
            check_time: Time to set, defaults to current UTC time
        """
        if check_time is None:
            check_time = datetime.now(timezone.utc)

        last_check_key = self._get_last_check_key()
        self.redis_client.set(last_check_key, check_time.isoformat())

    def publish_grant(self, grant_data: dict[str, Any]) -> str:
        """
        Publish a discovered grant to the Redis stream.

        Args:
            grant_data: Normalized grant data dictionary

        Returns:
            Redis stream message ID
        """
        # Ensure source is set
        grant_data["source"] = self.source_name
        grant_data["discovered_at"] = datetime.now(timezone.utc).isoformat()

        # Serialize the grant data
        message = {"data": json.dumps(grant_data)}

        # Publish to stream
        message_id = self.redis_client.xadd(self.GRANTS_STREAM, message)

        self.logger.info(
            "grant_published",
            external_id=grant_data.get("external_id"),
            title=grant_data.get("title", "")[:100],
            message_id=message_id,
        )

        return message_id

    def publish_grants_batch(self, grants: list[dict[str, Any]]) -> list[str]:
        """
        Publish multiple grants to the Redis stream.

        Args:
            grants: List of normalized grant data dictionaries

        Returns:
            List of Redis stream message IDs
        """
        message_ids = []
        for grant in grants:
            try:
                msg_id = self.publish_grant(grant)
                message_ids.append(msg_id)
            except Exception as e:
                self.logger.error("grant_publish_failed", external_id=grant.get("external_id"), error=str(e))
        return message_ids

    @abstractmethod
    async def discover(self) -> list[dict[str, Any]]:
        """
        Discover new grants from the source.

        Implementations should:
        1. Fetch data from the source API
        2. Filter out duplicates using is_duplicate()
        3. Mark new grants as seen using mark_as_seen()
        4. Return normalized grant data

        Returns:
            List of discovered grant data dictionaries
        """
        pass

    @abstractmethod
    async def run(self) -> int:
        """
        Execute the discovery process.

        This is the main entry point called by Celery tasks.
        Should call discover() and publish results.

        Returns:
            Number of new grants discovered
        """
        pass

    def close(self) -> None:
        """Clean up resources."""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None
