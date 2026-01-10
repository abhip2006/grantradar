"""
Tests for Grants.gov RSS Discovery Agent
"""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.discovery.grants_gov_rss import (
    DiscoveredGrant,
    GrantsGovDetails,
    GrantsGovEntry,
    GrantsGovRSSAgent,
    RateLimiter,
)


# ============================================================================
# Pydantic Model Tests
# ============================================================================


class TestGrantsGovEntry:
    """Tests for GrantsGovEntry model."""

    def test_valid_entry(self):
        """Test creating a valid RSS entry."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="Test Grant Opportunity",
            agency="Department of Energy",
            close_date=datetime(2025, 12, 31),
            link="https://www.grants.gov/view-opportunity.html?oppId=123456",
        )
        assert entry.opportunity_id == "123456"
        assert entry.title == "Test Grant Opportunity"
        assert entry.agency == "Department of Energy"

    def test_opportunity_id_stripped(self):
        """Test that opportunity ID is stripped of whitespace."""
        entry = GrantsGovEntry(
            opportunity_id="  123456  ",
            title="Test",
            agency="Test Agency",
            link="https://example.com",
        )
        assert entry.opportunity_id == "123456"

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="Test",
            agency="Test",
            link="https://example.com",
        )
        assert entry.close_date is None
        assert entry.posted_date is None
        assert entry.description is None


class TestGrantsGovDetails:
    """Tests for GrantsGovDetails model."""

    def test_valid_details_with_aliases(self):
        """Test creating details using API field names."""
        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Test Grant",
            agencyCode="DOE",
            agencyName="Department of Energy",
        )
        assert details.opportunity_id == "123456"
        assert details.title == "Test Grant"
        assert details.agency_code == "DOE"
        assert details.agency_name == "Department of Energy"

    def test_optional_funding_fields(self):
        """Test optional funding-related fields."""
        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Test Grant",
            awardCeiling=500000.0,
            awardFloor=100000.0,
            estimatedTotalProgramFunding=2000000.0,
            expectedNumberOfAwards=5,
        )
        assert details.award_ceiling == 500000.0
        assert details.award_floor == 100000.0
        assert details.estimated_total_funding == 2000000.0
        assert details.expected_number_of_awards == 5

    def test_cfda_list_default(self):
        """Test that CFDA list defaults to empty list."""
        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="Test Grant",
        )
        assert details.cfda_numbers == []


class TestDiscoveredGrant:
    """Tests for DiscoveredGrant model."""

    def test_valid_discovered_grant(self):
        """Test creating a valid discovered grant."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="Department of Energy",
            deadline=datetime(2025, 12, 31),
            url="https://www.grants.gov/view-opportunity.html?oppId=123456",
        )
        assert grant.external_id == "123456"
        assert grant.source == "grants_gov"
        assert grant.title == "Test Grant"
        assert grant.discovered_at is not None

    def test_to_stream_dict(self):
        """Test conversion to Redis stream dictionary."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="DOE",
            url="https://example.com",
            eligible_applicants=["Nonprofits", "Universities"],
            cfda_numbers=["12.345", "12.346"],
        )
        stream_dict = grant.to_stream_dict()

        assert stream_dict["external_id"] == "123456"
        assert stream_dict["source"] == "grants_gov"
        # Lists should be JSON serialized
        assert json.loads(stream_dict["eligible_applicants"]) == [
            "Nonprofits",
            "Universities",
        ]
        assert json.loads(stream_dict["cfda_numbers"]) == ["12.345", "12.346"]

    def test_to_stream_dict_excludes_none(self):
        """Test that None values are excluded from stream dict."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="DOE",
            url="https://example.com",
        )
        stream_dict = grant.to_stream_dict()

        assert "deadline" not in stream_dict
        assert "description" not in stream_dict
        assert "award_ceiling" not in stream_dict


# ============================================================================
# Rate Limiter Tests
# ============================================================================


class TestRateLimiter:
    """Tests for RateLimiter class."""

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self):
        """Test that requests within limit are allowed immediately."""
        limiter = RateLimiter(max_requests=3, time_window=1.0)

        # First 3 requests should be immediate
        for _ in range(3):
            await limiter.acquire()

        assert len(limiter.request_times) == 3

    @pytest.mark.asyncio
    async def test_blocks_requests_over_limit(self):
        """Test that requests over limit are delayed."""
        import time

        limiter = RateLimiter(max_requests=2, time_window=0.5)

        start = time.monotonic()
        for _ in range(3):
            await limiter.acquire()
        elapsed = time.monotonic() - start

        # Should have waited approximately 0.5 seconds for the third request
        assert elapsed >= 0.4  # Allow some tolerance


# ============================================================================
# Agent Tests
# ============================================================================


class TestGrantsGovRSSAgent:
    """Tests for GrantsGovRSSAgent class."""

    @pytest.fixture
    def agent(self):
        """Create an agent instance for testing."""
        return GrantsGovRSSAgent()

    @pytest.fixture
    def sample_rss_response(self):
        """Sample RSS XML response."""
        return """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Grants.gov New Opportunities</title>
                <item>
                    <title>Research Grant for Clean Energy</title>
                    <link>https://www.grants.gov/view-opportunity.html?oppId=123456</link>
                    <description>Funding for clean energy research.</description>
                    <pubDate>Mon, 01 Jan 2025 00:00:00 GMT</pubDate>
                </item>
                <item>
                    <title>Education Innovation Grant</title>
                    <link>https://www.grants.gov/view-opportunity.html?oppId=789012</link>
                    <description>Support for education technology.</description>
                    <pubDate>Tue, 02 Jan 2025 00:00:00 GMT</pubDate>
                </item>
            </channel>
        </rss>"""

    @pytest.fixture
    def sample_api_response(self):
        """Sample Grants.gov API response."""
        return {
            "oppHits": [
                {
                    "id": 123456,
                    "number": "DE-FOA-0001234",
                    "title": "Research Grant for Clean Energy",
                    "agency": "DOE",
                    "agencyName": "Department of Energy",
                    "oppStatus": "posted",
                    "openDate": "01/01/2025",
                    "closeDate": "03/31/2025",
                    "synopsis": "Full description of the clean energy grant opportunity.",
                    "awardCeiling": 500000,
                    "awardFloor": 100000,
                    "estimatedFunding": 2000000,
                    "numberOfAwards": 5,
                    "cfdaList": ["81.049"],
                    "eligibleApplicants": [
                        "Nonprofits",
                        "Public and State controlled institutions of higher education",
                    ],
                }
            ]
        }

    def test_agent_initialization(self, agent):
        """Test agent initializes with correct defaults."""
        assert agent.RSS_FEED_URL == "https://www.grants.gov/rss/GG_NewOps.xml"
        assert agent.REDIS_STREAM == "grants:discovered"
        assert agent.rate_limiter is not None

    def test_parse_rss_entry(self, agent):
        """Test parsing a feedparser entry."""
        # Create a mock feedparser entry
        mock_entry = MagicMock()
        mock_entry.title = "Test Grant"
        mock_entry.link = "https://www.grants.gov/view-opportunity.html?opportunityId=123456"
        mock_entry.summary = "Test description"
        mock_entry.published_parsed = (2025, 1, 15, 0, 0, 0, 0, 0, 0)
        mock_entry.updated_parsed = (2025, 1, 10, 0, 0, 0, 0, 0, 0)

        result = agent._parse_rss_entry(mock_entry)

        assert result is not None
        assert result.opportunity_id == "123456"
        assert result.title == "Test Grant"

    def test_parse_rss_entry_without_id(self, agent):
        """Test parsing entry without opportunity ID generates hash."""
        mock_entry = MagicMock()
        mock_entry.title = "Test Grant Without ID"
        mock_entry.link = "https://www.grants.gov/some-other-format"
        mock_entry.id = "not-a-number"
        mock_entry.summary = "Test description"
        mock_entry.published_parsed = None
        mock_entry.updated_parsed = None

        result = agent._parse_rss_entry(mock_entry)

        assert result is not None
        assert len(result.opportunity_id) == 12  # MD5 hash truncated to 12 chars

    def test_normalize_grant_with_details(self, agent):
        """Test normalizing grant with full API details."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="RSS Title",
            agency="Unknown Agency",
            link="https://www.grants.gov/view-opportunity.html?oppId=123456",
        )

        details = GrantsGovDetails(
            opportunityId="123456",
            opportunityTitle="API Title",
            agencyCode="DOE",
            agencyName="Department of Energy",
            closeDate="03/31/2025",
            awardCeiling=500000.0,
            description="Full description from API",
        )

        result = agent._normalize_grant(entry, details)

        assert result.external_id == "123456"
        assert result.title == "API Title"  # Should use API title
        assert result.agency == "Department of Energy"
        assert result.award_ceiling == 500000.0
        assert result.description == "Full description from API"

    def test_normalize_grant_without_details(self, agent):
        """Test normalizing grant without API details."""
        entry = GrantsGovEntry(
            opportunity_id="123456",
            title="RSS Title",
            agency="RSS Agency",
            link="https://www.grants.gov/view-opportunity.html?oppId=123456",
            description="RSS description",
        )

        result = agent._normalize_grant(entry, None)

        assert result.external_id == "123456"
        assert result.title == "RSS Title"  # Should use RSS title
        assert result.agency == "RSS Agency"
        assert result.description == "RSS description"

    @pytest.mark.asyncio
    async def test_fetch_rss_feed_success(self, agent, sample_rss_response):
        """Test successful RSS feed fetch."""
        with patch.object(agent, "_get_http_client") as mock_client_getter:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.text = sample_rss_response
            mock_response.raise_for_status = MagicMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_getter.return_value = mock_client

            with patch.object(agent.rate_limiter, "acquire", new_callable=AsyncMock):
                entries = await agent.fetch_rss_feed()

        assert len(entries) == 2
        assert entries[0].title == "Research Grant for Clean Energy"

    @pytest.mark.asyncio
    async def test_fetch_grant_details_success(self, agent, sample_api_response):
        """Test successful API details fetch."""
        with patch.object(agent, "_get_http_client") as mock_client_getter:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value=sample_api_response)
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_getter.return_value = mock_client

            with patch.object(agent.rate_limiter, "acquire", new_callable=AsyncMock):
                details = await agent.fetch_grant_details("123456")

        assert details is not None
        assert details.opportunity_id == "123456"
        assert details.title == "Research Grant for Clean Energy"
        assert details.award_ceiling == 500000

    @pytest.mark.asyncio
    async def test_fetch_grant_details_not_found(self, agent):
        """Test API fetch when grant not found."""
        with patch.object(agent, "_get_http_client") as mock_client_getter:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json = MagicMock(return_value={"oppHits": []})
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_getter.return_value = mock_client

            with patch.object(agent.rate_limiter, "acquire", new_callable=AsyncMock):
                details = await agent.fetch_grant_details("999999")

        assert details is None

    @pytest.mark.asyncio
    async def test_is_processed(self, agent):
        """Test checking if opportunity is processed."""
        with patch.object(agent, "_get_redis") as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis.sismember = AsyncMock(return_value=True)
            mock_redis_getter.return_value = mock_redis

            result = await agent.is_processed("123456")

        assert result is True
        mock_redis.sismember.assert_called_once_with("grants_gov:processed_ids", "123456")

    @pytest.mark.asyncio
    async def test_mark_processed(self, agent):
        """Test marking opportunity as processed."""
        with patch.object(agent, "_get_redis") as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis.sadd = AsyncMock()
            mock_redis.set = AsyncMock()
            mock_redis_getter.return_value = mock_redis

            await agent.mark_processed("123456")

        mock_redis.sadd.assert_called_once_with("grants_gov:processed_ids", "123456")
        mock_redis.set.assert_called_once_with("grants_gov:last_processed_id", "123456")

    @pytest.mark.asyncio
    async def test_publish_grant(self, agent):
        """Test publishing grant to Redis stream."""
        grant = DiscoveredGrant(
            external_id="123456",
            title="Test Grant",
            agency="DOE",
            url="https://example.com",
        )

        with patch.object(agent, "_get_redis") as mock_redis_getter:
            mock_redis = AsyncMock()
            mock_redis.xadd = AsyncMock(return_value="1234567890-0")
            mock_redis_getter.return_value = mock_redis

            message_id = await agent.publish_grant(grant)

        assert message_id == "1234567890-0"
        mock_redis.xadd.assert_called_once()

    @pytest.mark.asyncio
    async def test_close(self, agent):
        """Test closing agent connections."""
        mock_redis = AsyncMock()
        mock_http = AsyncMock()
        agent._redis = mock_redis
        agent._http_client = mock_http

        await agent.close()

        mock_redis.close.assert_called_once()
        mock_http.aclose.assert_called_once()
        assert agent._redis is None
        assert agent._http_client is None


# ============================================================================
# Integration Tests (require actual services)
# ============================================================================


@pytest.mark.integration
class TestGrantsGovRSSAgentIntegration:
    """Integration tests that require actual Redis/network access."""

    @pytest.mark.asyncio
    async def test_full_discovery_flow(self):
        """Test the complete discovery workflow."""
        # This test would require actual services
        # Skip in CI, run manually for integration testing
        pytest.skip("Integration test - requires actual services")


# ============================================================================
# Celery Task Tests
# ============================================================================


class TestCeleryTask:
    """Tests for Celery task configuration."""

    def test_celery_app_configuration(self):
        """Test Celery app is configured correctly."""
        from agents.discovery.grants_gov_rss import celery_app

        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_beat_schedule_configured(self):
        """Test Celery Beat schedule is configured."""
        from agents.discovery.grants_gov_rss import celery_app

        schedule = celery_app.conf.beat_schedule
        assert "discover-grants-gov-rss" in schedule
        assert schedule["discover-grants-gov-rss"]["schedule"] == 300.0  # 5 minutes
