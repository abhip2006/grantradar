"""
Tests for NSF Award Search API Discovery Agent.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, AsyncMock

from agents.discovery.nsf_api import (
    NSFDiscoveryAgent,
    NSFAward,
    NSFSearchParams,
    DiscoveredGrant,
)


class TestNSFAward:
    """Tests for NSFAward Pydantic model."""

    def test_valid_award(self, sample_nsf_award):
        """Test creating valid award from sample data."""
        award = NSFAward.model_validate(sample_nsf_award)

        assert award.id == "2529183"
        assert award.title == "Machine Learning for Climate Science Research"
        assert award.agency == "NSF"

    def test_get_amount(self, sample_nsf_award):
        """Test amount parsing to Decimal."""
        award = NSFAward.model_validate(sample_nsf_award)

        amount = award.get_amount()
        assert amount == Decimal("797762")

    def test_get_amount_with_commas(self):
        """Test amount parsing with commas."""
        award = NSFAward(id="123", title="Test", fundsObligatedAmt="1,234,567")

        assert award.get_amount() == Decimal("1234567")

    def test_get_amount_with_currency(self):
        """Test amount parsing with currency symbol."""
        award = NSFAward(id="123", title="Test", fundsObligatedAmt="$500,000")

        assert award.get_amount() == Decimal("500000")

    def test_get_amount_none(self):
        """Test amount returns None when not set."""
        award = NSFAward(id="123", title="Test")

        assert award.get_amount() is None

    def test_get_pi_name(self, sample_nsf_award):
        """Test PI name construction."""
        award = NSFAward.model_validate(sample_nsf_award)

        pi_name = award.get_pi_name()
        assert pi_name == "Jane A Smith"

    def test_get_pi_name_partial(self):
        """Test PI name with partial info."""
        award = NSFAward(id="123", title="Test", piFirstName="John", piLastName="Doe")

        assert award.get_pi_name() == "John Doe"

    def test_get_pi_name_none(self):
        """Test PI name returns None when not set."""
        award = NSFAward(id="123", title="Test")

        assert award.get_pi_name() is None

    def test_parse_list_fields(self):
        """Test fields that come as lists are joined."""
        award = NSFAward(
            id="123",
            title="Test",
            fundProgramName=["Computer Science", "AI Research"],
            cfdaNumber=["47.070", "47.041"],
        )

        assert award.fundProgramName == "Computer Science; AI Research"
        assert award.cfdaNumber == "47.070; 47.041"


class TestNSFSearchParams:
    """Tests for NSFSearchParams model."""

    def test_default_params(self):
        """Test default parameter values."""
        params = NSFSearchParams()

        assert params.offset == 1
        assert params.rpp == 25

    def test_to_query_params(self):
        """Test conversion to query parameters."""
        params = NSFSearchParams(
            dateStart="01/01/2025",
            dateEnd="01/31/2025",
            rpp=10,
        )

        query = params.to_query_params()

        assert query["dateStart"] == "01/01/2025"
        assert query["dateEnd"] == "01/31/2025"
        assert query["rpp"] == "10"

    def test_excludes_none_values(self):
        """Test None values are excluded from query params."""
        params = NSFSearchParams(offset=1, rpp=25)

        query = params.to_query_params()

        assert "dateStart" not in query
        assert "keyword" not in query


class TestDiscoveredGrant:
    """Tests for DiscoveredGrant model."""

    def test_create_discovered_grant(self):
        """Test creating a discovered grant."""
        grant = DiscoveredGrant(
            external_id="1234567",
            source="nsf",
            title="Test Grant",
            amount=Decimal("500000"),
        )

        assert grant.external_id == "1234567"
        assert grant.source == "nsf"
        assert grant.funding_agency == "NSF"

    def test_json_serialization(self):
        """Test JSON serialization handles Decimal."""
        grant = DiscoveredGrant(
            external_id="1234567",
            source="nsf",
            title="Test Grant",
            amount=Decimal("500000.50"),
        )

        json_data = grant.model_dump(mode="json")

        # Decimal should be serialized as string
        assert json_data["amount"] == "500000.50"


class TestNSFDiscoveryAgent:
    """Tests for NSFDiscoveryAgent class."""

    def test_agent_initialization(self):
        """Test agent initializes with correct source name."""
        agent = NSFDiscoveryAgent()

        assert agent.source_name == "nsf"
        assert agent.API_URL is not None

    def test_parse_nsf_date_valid(self, mock_nsf_agent):
        """Test date parsing with valid MM/DD/YYYY format."""
        result = mock_nsf_agent._parse_nsf_date("01/15/2025")

        assert result == "2025-01-15"

    def test_parse_nsf_date_invalid(self, mock_nsf_agent):
        """Test date parsing with invalid format returns None."""
        result = mock_nsf_agent._parse_nsf_date("2025-01-15")  # Wrong format

        assert result is None

    def test_parse_nsf_date_none(self, mock_nsf_agent):
        """Test date parsing with None returns None."""
        result = mock_nsf_agent._parse_nsf_date(None)

        assert result is None

    def test_format_date_for_api(self, mock_nsf_agent):
        """Test date formatting for API requests."""
        dt = datetime(2025, 1, 15)
        result = mock_nsf_agent._format_date_for_api(dt)

        assert result == "01/15/2025"

    def test_normalize_award(self, mock_nsf_agent, sample_nsf_award):
        """Test award normalization to DiscoveredGrant."""
        award = NSFAward.model_validate(sample_nsf_award)
        grant = mock_nsf_agent._normalize_award(award)

        assert grant.external_id == "2529183"
        assert grant.source == "nsf"
        assert grant.title == "Machine Learning for Climate Science Research"
        assert grant.amount == Decimal("797762")
        assert grant.funding_agency == "NSF"
        assert "nsf.gov/awardsearch" in grant.source_url
        assert grant.pi_name == "Jane A Smith"
        assert grant.institution_name == "Stanford University"

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, mock_nsf_agent, sample_nsf_api_response):
        """Test successful API page fetch."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nsf_api_response
        mock_response.raise_for_status = MagicMock()

        # Create async mock that returns the response directly
        async def mock_get(*args, **kwargs):
            return mock_response

        mock_nsf_agent.http_client = AsyncMock()
        mock_nsf_agent.http_client.get = mock_get

        params = NSFSearchParams(dateStart="01/01/2025", dateEnd="01/07/2025")
        result = await mock_nsf_agent._fetch_page(params)

        assert "response" in result
        assert "award" in result["response"]
        assert len(result["response"]["award"]) == 1

    @pytest.mark.asyncio
    async def test_discover_filters_duplicates(self, mock_nsf_agent, sample_nsf_api_response):
        """Test that duplicates are filtered during discovery."""
        # Setup mock to return same award twice
        doubled_response = sample_nsf_api_response.copy()
        doubled_response["response"]["award"] = [
            sample_nsf_api_response["response"]["award"][0],
            sample_nsf_api_response["response"]["award"][0],  # Duplicate
        ]

        mock_response = MagicMock()
        mock_response.json.return_value = doubled_response
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_nsf_agent.http_client = AsyncMock()
        mock_nsf_agent.http_client.get = mock_get

        # First call not duplicate, second call is duplicate
        mock_nsf_agent._redis_client.sismember.side_effect = [False, True]

        grants = await mock_nsf_agent.discover()

        # Should only return 1 grant (duplicate filtered)
        assert len(grants) == 1

    @pytest.mark.asyncio
    async def test_discover_marks_as_seen(self, mock_nsf_agent, sample_nsf_api_response):
        """Test that discovered grants are marked as seen."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nsf_api_response
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_nsf_agent.http_client = AsyncMock()
        mock_nsf_agent.http_client.get = mock_get

        await mock_nsf_agent.discover()

        # Should have called sadd to mark as seen
        mock_nsf_agent._redis_client.sadd.assert_called()

    @pytest.mark.asyncio
    async def test_run_publishes_to_stream(self, mock_nsf_agent, sample_nsf_api_response):
        """Test that run() publishes grants to Redis stream."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nsf_api_response
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_nsf_agent.http_client = AsyncMock()
        mock_nsf_agent.http_client.get = mock_get
        mock_nsf_agent.http_client.aclose = AsyncMock()

        # Save reference to redis client before run() (close() may set it to None)
        redis_client = mock_nsf_agent._redis_client

        count = await mock_nsf_agent.run()

        assert count == 1
        # Should have called xadd to publish
        redis_client.xadd.assert_called()

    @pytest.mark.asyncio
    async def test_run_updates_last_check_time(self, mock_nsf_agent, sample_nsf_api_response):
        """Test that run() updates last check time."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nsf_api_response
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_nsf_agent.http_client = AsyncMock()
        mock_nsf_agent.http_client.get = mock_get
        mock_nsf_agent.http_client.aclose = AsyncMock()

        # Save reference to redis client before run() (close() may set it to None)
        redis_client = mock_nsf_agent._redis_client

        await mock_nsf_agent.run()

        # Should have called set for last check time
        redis_client.set.assert_called()

    @pytest.mark.asyncio
    async def test_close_async(self, mock_nsf_agent):
        """Test async resource cleanup."""
        # Create a proper mock http_client
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()
        mock_nsf_agent.http_client = mock_client

        await mock_nsf_agent.close_async()

        mock_client.aclose.assert_called_once()
        assert mock_nsf_agent.http_client is None
