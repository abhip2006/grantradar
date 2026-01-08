"""
Tests for NIH Reporter API Discovery Agent.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock

from agents.discovery.nih_reporter import (
    NIHReporterDiscoveryAgent,
    NIHReporterProject,
    NIHSearchRequest,
    NIHSearchCriteria,
    DiscoveredGrant,
)


class TestNIHReporterProject:
    """Tests for NIHReporterProject model."""

    def test_valid_project(self, sample_nih_reporter_project):
        """Test creating valid project from sample data."""
        project = NIHReporterProject.model_validate(sample_nih_reporter_project)
        assert project.project_num == "1R01CA123456-01"
        assert project.award_amount == 750000

    def test_get_agency_name(self, sample_nih_reporter_project):
        """Test agency name extraction."""
        project = NIHReporterProject.model_validate(sample_nih_reporter_project)
        assert project.get_agency_name() == "National Cancer Institute"

    def test_get_primary_pi(self, sample_nih_reporter_project):
        """Test PI extraction."""
        project = NIHReporterProject.model_validate(sample_nih_reporter_project)
        pi = project.get_primary_pi()
        assert pi.get_full_name() == "John B Doe"

    def test_get_project_url(self, sample_nih_reporter_project):
        """Test URL generation."""
        project = NIHReporterProject.model_validate(sample_nih_reporter_project)
        assert "reporter.nih.gov/project-details" in project.get_project_url()


class TestNIHReporterDiscoveryAgent:
    """Tests for NIHReporterDiscoveryAgent class."""

    def test_agent_initialization(self):
        """Test agent initializes correctly."""
        agent = NIHReporterDiscoveryAgent()
        assert agent.source_name == "nih_reporter"

    def test_parse_nih_date(self, mock_nih_reporter_agent):
        """Test date parsing."""
        assert mock_nih_reporter_agent._parse_nih_date("2025-01-15") == "2025-01-15"
        assert mock_nih_reporter_agent._parse_nih_date(None) is None

    def test_normalize_project(self, mock_nih_reporter_agent, sample_nih_reporter_project):
        """Test project normalization."""
        project = NIHReporterProject.model_validate(sample_nih_reporter_project)
        grant = mock_nih_reporter_agent._normalize_project(project)

        assert grant.external_id == "1R01CA123456-01"
        assert grant.source == "nih_reporter"
        assert grant.amount == 750000
        assert "National Cancer Institute" in grant.funding_agency
        assert grant.pi_name == "John B Doe"

    @pytest.mark.asyncio
    async def test_fetch_page_success(self, mock_nih_reporter_agent, sample_nih_reporter_api_response):
        """Test successful API page fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nih_reporter_api_response
        mock_response.raise_for_status = MagicMock()

        # Create async mock that returns the response directly
        async def mock_post(*args, **kwargs):
            return mock_response
        mock_nih_reporter_agent.http_client = AsyncMock()
        mock_nih_reporter_agent.http_client.post = mock_post

        request = NIHSearchRequest(criteria=NIHSearchCriteria(fiscal_years=[2025]))
        result = await mock_nih_reporter_agent._fetch_page(request)

        assert "results" in result
        assert len(result["results"]) == 1

    @pytest.mark.asyncio
    async def test_run_publishes_to_stream(self, mock_nih_reporter_agent, sample_nih_reporter_api_response):
        """Test run() publishes to Redis stream."""
        mock_response = MagicMock()
        mock_response.json.return_value = sample_nih_reporter_api_response
        mock_response.raise_for_status = MagicMock()

        # Create proper async mock
        async def mock_post(*args, **kwargs):
            return mock_response
        mock_nih_reporter_agent.http_client = AsyncMock()
        mock_nih_reporter_agent.http_client.post = mock_post
        mock_nih_reporter_agent.http_client.aclose = AsyncMock()

        # Save reference to redis client before run() (close() may set it to None)
        redis_client = mock_nih_reporter_agent._redis_client

        count = await mock_nih_reporter_agent.run()

        assert count == 1
        redis_client.xadd.assert_called()
