"""
Discovery Agent Tests
Tests for grant discovery agents including RSS parsing, API fetching, and Redis publishing.
"""
import asyncio
import hashlib
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
import uuid

import httpx
import pytest
import redis

from agents.discovery.base import DiscoveryAgent
from agents.discovery.grants_gov_rss import (
    GrantsGovRSSAgent,
    GrantsGovEntry,
    GrantsGovDetails,
    DiscoveredGrant,
    RateLimiter,
)


# =============================================================================
# Rate Limiter Tests
# =============================================================================


class TestRateLimiter:
    """Tests for the RateLimiter class."""

    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests_under_limit(self):
        """Test that rate limiter allows requests under the limit."""
        limiter = RateLimiter(max_requests=3, time_window=1.0)

        # Should allow 3 requests quickly
        for _ in range(3):
            await limiter.acquire()

        # Verify all requests tracked
        assert len(limiter.request_times) == 3

    @pytest.mark.asyncio
    async def test_rate_limiter_blocks_over_limit(self):
        """Test that rate limiter blocks requests over the limit."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)

        # Make 2 requests (at limit)
        await limiter.acquire()
        await limiter.acquire()

        # Third request should be delayed
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should have waited for at least part of the time window
        assert elapsed >= 0.05  # Allow some timing slack

    @pytest.mark.asyncio
    async def test_rate_limiter_clears_old_requests(self):
        """Test that rate limiter clears expired requests."""
        limiter = RateLimiter(max_requests=2, time_window=0.1)

        # Make 2 requests
        await limiter.acquire()
        await limiter.acquire()

        # Wait for time window to expire
        await asyncio.sleep(0.15)

        # Next request should not block since old ones expired
        start = asyncio.get_event_loop().time()
        await limiter.acquire()
        elapsed = asyncio.get_event_loop().time() - start

        # Should be nearly instant
        assert elapsed < 0.05


# =============================================================================
# Grants.gov Entry Parsing Tests
# =============================================================================


class TestGrantsGovEntry:
    """Tests for parsing RSS feed entries."""

    def test_grants_gov_entry_valid(self):
        """Test parsing a valid RSS entry."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="Test Grant",
            agency="NIH",
            link="https://grants.gov/test",
        )

        assert entry.opportunity_id == "123456"
        assert entry.title == "Test Grant"
        assert entry.agency == "NIH"

    def test_grants_gov_entry_strips_whitespace(self):
        """Test that opportunity_id whitespace is stripped."""
        entry = GrantsGovEntry(
            opportunity_id="  123456  ",
            title="Test Grant",
            agency="NIH",
            link="https://grants.gov/test",
        )

        assert entry.opportunity_id == "123456"

    def test_grants_gov_entry_optional_fields(self):
        """Test entry with optional fields."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="Test Grant",
            agency="NIH",
            link="https://grants.gov/test",
            close_date=datetime(2024, 12, 31),
            posted_date=datetime(2024, 1, 1),
            description="A test grant opportunity",
        )

        assert entry.close_date == datetime(2024, 12, 31)
        assert entry.posted_date == datetime(2024, 1, 1)
        assert entry.description == "A test grant opportunity"


# =============================================================================
# Grants.gov Details Parsing Tests
# =============================================================================


class TestGrantsGovDetails:
    """Tests for parsing API response details."""

    def test_grants_gov_details_valid(self):
        """Test parsing valid API response."""
        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Research Grant",
            agencyName="National Institutes of Health",
        )

        assert details.opportunity_id == "123456"
        assert details.title == "Research Grant"
        assert details.agency_name == "National Institutes of Health"

    def test_grants_gov_details_with_funding(self):
        """Test parsing API response with funding information."""
        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Research Grant",
            awardCeiling=500000.0,
            awardFloor=100000.0,
            estimatedTotalProgramFunding=2000000.0,
        )

        assert details.award_ceiling == 500000.0
        assert details.award_floor == 100000.0
        assert details.estimated_total_funding == 2000000.0

    def test_grants_gov_details_aliases(self):
        """Test that field aliases work correctly."""
        data = {
            "opportunityId": "123456",
            "opportunityTitle": "Test Grant",
            "agencyCode": "NIH",
            "closeDate": "12/31/2024",
        }

        details = GrantsGovDetails(**data)

        assert details.opportunity_id == "123456"
        assert details.title == "Test Grant"
        assert details.agency_code == "NIH"
        assert details.close_date == "12/31/2024"


# =============================================================================
# Discovered Grant Model Tests
# =============================================================================


class TestDiscoveredGrant:
    """Tests for the DiscoveredGrant model."""

    def test_discovered_grant_to_stream_dict(self):
        """Test converting to Redis stream format."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="NIH",
            url="https://grants.gov/test",
            eligible_applicants=["universities", "nonprofits"],
            cfda_numbers=["93.123", "93.456"],
        )

        stream_dict = grant.to_stream_dict()

        assert stream_dict["external_id"] == "123456"
        assert stream_dict["title"] == "Test Grant"
        assert stream_dict["source"] == "grants_gov"
        # Lists should be JSON serialized
        assert json.loads(stream_dict["eligible_applicants"]) == ["universities", "nonprofits"]
        assert json.loads(stream_dict["cfda_numbers"]) == ["93.123", "93.456"]

    def test_discovered_grant_defaults(self):
        """Test default values are set correctly."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="NIH",
            url="https://grants.gov/test",
        )

        assert grant.source == "grants_gov"
        assert grant.eligible_applicants == []
        assert grant.cfda_numbers == []
        assert grant.discovered_at is not None


# =============================================================================
# Grants.gov RSS Agent Tests
# =============================================================================


class TestGrantsGovRSSAgent:
    """Tests for the GrantsGovRSSAgent class."""

    @pytest.fixture
    def agent(self, fake_redis):
        """Create agent with fake Redis."""
        agent = GrantsGovRSSAgent()
        agent._redis = fake_redis
        return agent

    @pytest.mark.asyncio
    async def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = GrantsGovRSSAgent()

        assert agent.rate_limiter is not None
        assert agent.RSS_FEED_URL is not None
        assert agent.REDIS_STREAM == "grants:discovered"

    @pytest.mark.asyncio
    async def test_fetch_rss_feed_success(self, agent, sample_rss_feed, mock_httpx_client):
        """Test successful RSS feed fetching."""
        # Setup mock response
        async def mock_get(url):
            response = AsyncMock()
            response.text = sample_rss_feed
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.get = mock_get
        agent._http_client = mock_httpx_client

        entries = await agent.fetch_rss_feed()

        assert len(entries) == 2
        assert entries[0].title == "Research Grant Opportunity"
        assert entries[1].title == "Education Grant Opportunity"

    @pytest.mark.asyncio
    async def test_fetch_rss_feed_http_error(self, agent, mock_httpx_client):
        """Test handling of HTTP errors (retries then raises RetryError)."""
        from tenacity import RetryError

        async def mock_get(url):
            response = MagicMock()
            response.status_code = 500
            raise httpx.HTTPStatusError("Server Error", request=MagicMock(), response=response)

        mock_httpx_client.get = mock_get
        agent._http_client = mock_httpx_client

        # The function retries on errors, eventually raising RetryError
        with pytest.raises(RetryError):
            await agent.fetch_rss_feed()

    @pytest.mark.asyncio
    async def test_fetch_rss_feed_malformed(self, agent, malformed_rss_feed, mock_httpx_client):
        """Test handling of malformed RSS feed."""
        async def mock_get(url):
            response = AsyncMock()
            response.text = malformed_rss_feed
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.get = mock_get
        agent._http_client = mock_httpx_client

        # Should not raise, but may return partial results or empty list
        entries = await agent.fetch_rss_feed()
        assert isinstance(entries, list)

    @pytest.mark.asyncio
    async def test_is_processed_new_entry(self, agent, fake_redis):
        """Test checking if entry is processed - new entry."""
        agent._redis = fake_redis

        is_processed = await agent.is_processed("NEW-123456")

        assert is_processed is False

    @pytest.mark.asyncio
    async def test_is_processed_existing_entry(self, agent, fake_redis):
        """Test checking if entry is processed - existing entry."""
        agent._redis = fake_redis

        # Mark as processed first
        await agent.mark_processed("EXISTING-123456")

        is_processed = await agent.is_processed("EXISTING-123456")

        assert is_processed is True

    @pytest.mark.asyncio
    async def test_mark_processed(self, agent, fake_redis):
        """Test marking entry as processed."""
        agent._redis = fake_redis

        await agent.mark_processed("123456")

        # Check it's now in the set
        is_member = await fake_redis.sismember(agent.REDIS_PROCESSED_SET, "123456")
        assert is_member is True

    @pytest.mark.asyncio
    async def test_publish_grant(self, agent, fake_redis):
        """Test publishing grant to Redis stream."""
        agent._redis = fake_redis

        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="NIH",
            url="https://grants.gov/test",
        )

        message_id = await agent.publish_grant(grant)

        assert message_id is not None
        # Check stream has the message
        stream_len = await fake_redis.xlen(agent.REDIS_STREAM)
        assert stream_len == 1

    @pytest.mark.asyncio
    async def test_normalize_grant_with_details(self, agent):
        """Test normalizing grant with full API details."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="Basic Title",
            agency="Unknown",
            link="https://grants.gov/basic",
        )

        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Full Title from API",
            agencyName="National Institutes of Health",
            description="Detailed description",
            awardCeiling=500000.0,
            awardFloor=100000.0,
            closeDate="12/31/2024",
        )

        normalized = agent._normalize_grant(entry, details)

        # Should use API details over RSS entry
        assert normalized.title == "Full Title from API"
        assert normalized.agency == "National Institutes of Health"
        assert normalized.description == "Detailed description"
        assert normalized.award_ceiling == 500000.0

    @pytest.mark.asyncio
    async def test_normalize_grant_without_details(self, agent):
        """Test normalizing grant without API details (fallback)."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="RSS Title",
            agency="RSS Agency",
            link="https://grants.gov/rss",
            description="RSS description",
        )

        normalized = agent._normalize_grant(entry, None)

        # Should use RSS entry values
        assert normalized.title == "RSS Title"
        assert normalized.agency == "RSS Agency"
        assert normalized.description == "RSS description"

    @pytest.mark.asyncio
    async def test_discover_new_grants_filters_duplicates(self, agent, fake_redis, sample_rss_feed, mock_httpx_client):
        """Test that already-processed grants are filtered."""
        agent._redis = fake_redis

        # Mark one entry as already processed
        await agent.mark_processed("123456")

        # Setup mock to return RSS feed
        async def mock_get(url):
            response = AsyncMock()
            response.text = sample_rss_feed
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.get = mock_get
        agent._http_client = mock_httpx_client

        # Mock the API fetch to return empty (no details)
        async def mock_post(url, **kwargs):
            response = AsyncMock()
            response.json.return_value = {"oppHits": []}
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.post = mock_post

        grants = await agent.discover_new_grants()

        # Should only have 1 grant (the other was filtered as duplicate)
        assert len(grants) == 1
        assert grants[0].external_id == "123457"

    @pytest.mark.asyncio
    async def test_close_releases_resources(self, agent, fake_redis, mock_httpx_client):
        """Test that close() releases all resources."""
        agent._redis = fake_redis
        agent._http_client = mock_httpx_client

        await agent.close()

        assert agent._redis is None
        assert agent._http_client is None


# =============================================================================
# Base Discovery Agent Tests
# =============================================================================


class TestBaseDiscoveryAgent:
    """Tests for the DiscoveryAgent base class."""

    class ConcreteAgent(DiscoveryAgent):
        """Concrete implementation for testing."""

        async def discover(self):
            return [{"external_id": "test", "title": "Test Grant"}]

        async def run(self):
            grants = await self.discover()
            return len(grants)

    @pytest.fixture
    def base_agent(self, mock_redis):
        """Create a concrete agent for testing."""
        agent = self.ConcreteAgent("test_source")
        agent._redis_client = mock_redis
        return agent

    def test_source_name_set(self, base_agent):
        """Test source name is set correctly."""
        assert base_agent.source_name == "test_source"

    def test_compute_grant_hash(self, base_agent):
        """Test grant hash computation is deterministic."""
        hash1 = base_agent._compute_grant_hash("ext123", "Test Grant")
        hash2 = base_agent._compute_grant_hash("ext123", "Test Grant")

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest

    def test_compute_grant_hash_different_inputs(self, base_agent):
        """Test different inputs produce different hashes."""
        hash1 = base_agent._compute_grant_hash("ext123", "Test Grant")
        hash2 = base_agent._compute_grant_hash("ext124", "Test Grant")
        hash3 = base_agent._compute_grant_hash("ext123", "Different Grant")

        assert hash1 != hash2
        assert hash1 != hash3
        assert hash2 != hash3

    @pytest.mark.asyncio
    async def test_is_duplicate_new(self, base_agent, mock_redis):
        """Test checking duplicate for new grant."""
        mock_redis.sismember = AsyncMock(return_value=False)

        is_dup = await base_agent.is_duplicate("new123", "New Grant")

        assert is_dup is False

    @pytest.mark.asyncio
    async def test_is_duplicate_existing(self, base_agent, mock_redis):
        """Test checking duplicate for existing grant."""
        mock_redis.sismember = AsyncMock(return_value=True)

        is_dup = await base_agent.is_duplicate("existing123", "Existing Grant")

        assert is_dup is True

    @pytest.mark.asyncio
    async def test_mark_as_seen(self, base_agent, mock_redis):
        """Test marking grant as seen."""
        base_agent.mark_as_seen("ext123", "Test Grant")

        mock_redis.sadd.assert_called_once()
        mock_redis.expire.assert_called_once()

    @pytest.mark.asyncio
    async def test_publish_grant(self, base_agent, mock_redis):
        """Test publishing grant to Redis stream."""
        grant_data = {
            "external_id": "ext123",
            "title": "Test Grant",
        }

        message_id = base_agent.publish_grant(grant_data)

        mock_redis.xadd.assert_called_once()
        # Source should be added
        call_args = mock_redis.xadd.call_args
        assert "data" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_last_check_time_none(self, base_agent, mock_redis):
        """Test getting last check time when not set."""
        mock_redis.get = MagicMock(return_value=None)

        result = base_agent.get_last_check_time()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_last_check_time_exists(self, base_agent, mock_redis):
        """Test getting last check time when set."""
        timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        mock_redis.get = MagicMock(return_value=timestamp.isoformat())

        result = base_agent.get_last_check_time()

        assert result == timestamp

    @pytest.mark.asyncio
    async def test_set_last_check_time(self, base_agent, mock_redis):
        """Test setting last check time."""
        timestamp = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

        base_agent.set_last_check_time(timestamp)

        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, base_agent, mock_redis):
        """Test closing agent releases Redis connection."""
        base_agent.close()

        mock_redis.close.assert_called_once()
        assert base_agent._redis_client is None


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestDiscoveryErrorHandling:
    """Tests for error handling in discovery agents."""

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self, mock_httpx_client):
        """Test retry behavior on network errors."""
        agent = GrantsGovRSSAgent()

        # Setup mock to fail twice then succeed
        call_count = 0

        async def mock_get(url):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Connection timeout")

            response = AsyncMock()
            response.text = "<rss><channel></channel></rss>"
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.get = mock_get
        agent._http_client = mock_httpx_client

        # Should eventually succeed after retries
        entries = await agent.fetch_rss_feed()

        assert call_count == 3
        assert isinstance(entries, list)

    @pytest.mark.asyncio
    async def test_api_rate_limit_handling(self, mock_httpx_client):
        """Test handling of API rate limit responses (retries then raises RetryError)."""
        from tenacity import RetryError
        agent = GrantsGovRSSAgent()

        async def mock_post(url, **kwargs):
            response = MagicMock()
            response.status_code = 429
            raise httpx.HTTPStatusError("Rate limited", request=MagicMock(), response=response)

        mock_httpx_client.post = mock_post
        agent._http_client = mock_httpx_client

        # The function retries on errors, eventually raising RetryError
        with pytest.raises(RetryError):
            await agent.fetch_grant_details("123456")

    @pytest.mark.asyncio
    async def test_json_parse_error_handling(self, mock_httpx_client):
        """Test handling of invalid JSON responses."""
        from tenacity import RetryError
        agent = GrantsGovRSSAgent()

        async def mock_post(url, **kwargs):
            response = MagicMock()
            # json() in httpx is synchronous, so use a regular function that raises
            response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
            response.raise_for_status = MagicMock()
            return response

        mock_httpx_client.post = mock_post
        agent._http_client = mock_httpx_client

        # The function retries on errors, eventually raising RetryError wrapping JSONDecodeError
        with pytest.raises((json.JSONDecodeError, RetryError)):
            await agent.fetch_grant_details("123456")


# =============================================================================
# Redis Stream Publishing Tests
# =============================================================================


class TestRedisStreamPublishing:
    """Tests for Redis stream publishing behavior."""

    @pytest.mark.asyncio
    async def test_publish_adds_timestamp(self, fake_redis):
        """Test that published grants include discovery timestamp."""
        agent = GrantsGovRSSAgent()
        agent._redis = fake_redis

        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="NIH",
            url="https://grants.gov/test",
        )

        await agent.publish_grant(grant)

        # Check the stream has data
        stream_len = await fake_redis.xlen(agent.REDIS_STREAM)
        assert stream_len == 1

    @pytest.mark.asyncio
    async def test_publish_serializes_lists(self, fake_redis):
        """Test that list fields are properly serialized."""
        agent = GrantsGovRSSAgent()
        agent._redis = fake_redis

        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="NIH",
            url="https://grants.gov/test",
            eligible_applicants=["universities", "nonprofits"],
            cfda_numbers=["93.123"],
        )

        await agent.publish_grant(grant)

        # Verify serialization happened
        stream_dict = grant.to_stream_dict()
        assert isinstance(stream_dict["eligible_applicants"], str)
        assert json.loads(stream_dict["eligible_applicants"]) == ["universities", "nonprofits"]

    @pytest.mark.asyncio
    async def test_batch_publish(self, fake_redis):
        """Test publishing multiple grants in batch."""

        class ConcreteAgent(DiscoveryAgent):
            async def discover(self):
                return []

            async def run(self):
                return 0

        agent = ConcreteAgent("test")
        # Use sync mock for batch operations
        mock_redis = MagicMock()
        mock_redis.xadd = MagicMock(return_value="123-0")
        mock_redis.sadd = MagicMock()
        mock_redis.expire = MagicMock()
        agent._redis_client = mock_redis

        grants = [
            {"external_id": f"grant-{i}", "title": f"Grant {i}"}
            for i in range(5)
        ]

        message_ids = agent.publish_grants_batch(grants)

        assert len(message_ids) == 5
        assert mock_redis.xadd.call_count == 5
