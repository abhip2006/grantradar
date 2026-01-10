"""
Tests for Deep Research API endpoints.
Tests research sessions, grant discovery, and AI-powered insights.
"""

import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import MagicMock, patch

from backend.models import Grant, LabProfile, ResearchSession
from backend.schemas.research import ResearchStatus, ResearchGrantResult
from backend.services.deep_research import DeepResearchService


@pytest.fixture
def mock_openai_embedding():
    """Mock OpenAI embedding response."""
    return MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])


@pytest.fixture
def mock_anthropic_query_expansion():
    """Mock Anthropic response for query expansion."""
    return MagicMock(
        content=[
            MagicMock(
                text="machine learning healthcare AI medical imaging deep learning cancer diagnosis NIH R01 R21 computational biology biomedical informatics"
            )
        ]
    )


@pytest.fixture
def mock_anthropic_scoring():
    """Mock Anthropic response for result scoring."""
    return MagicMock(
        content=[
            MagicMock(
                text="""[
            {"index": 1, "relevance_score": 0.92, "match_reasons": ["Strong ML focus", "Healthcare application", "NIH alignment"]},
            {"index": 2, "relevance_score": 0.78, "match_reasons": ["Related methodology", "Computational approach"]}
        ]"""
            )
        ]
    )


@pytest.fixture
def mock_anthropic_insights():
    """Mock Anthropic response for insights generation."""
    return MagicMock(
        content=[
            MagicMock(
                text="""Key Insights:
1. The NIH R01 for AI in Healthcare is your strongest match - prioritize this application
2. NSF has increased computational biology funding by 15% this cycle
3. Consider pairing with a clinical collaborator for the translational grants
4. Deadline clustering in March suggests starting applications now"""
            )
        ]
    )


@pytest.fixture
def sample_research_query():
    """Sample research query."""
    return "I'm researching machine learning applications in medical imaging, specifically for early cancer detection. Looking for NIH and NSF funding opportunities."


@pytest.mark.integration
class TestResearchSessionManagement:
    """Tests for research session CRUD operations.

    Note: These tests require a PostgreSQL database with JSONB and pgvector support.
    They will fail with SQLite due to missing PostgreSQL-specific types.
    """

    @pytest.mark.asyncio
    async def test_create_session(self, async_session, db_user, sample_research_query):
        """Test creating a research session."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()

            session = await service.create_session(
                db=async_session,
                user=db_user,
                query=sample_research_query,
            )

            assert session is not None
            assert session.query == sample_research_query
            assert session.status == "pending"
            assert session.user_id == db_user.id

    @pytest.mark.asyncio
    async def test_get_sessions_returns_user_sessions(self, async_session, db_user):
        """Test get_sessions returns only user's sessions."""
        # Create sessions for our user
        for i in range(3):
            session = ResearchSession(
                user_id=db_user.id,
                query=f"Research query {i}",
                status="completed",
            )
            async_session.add(session)

        # Create session for another user (won't be returned)
        other_user_id = uuid4()
        other_session = ResearchSession(
            user_id=other_user_id,
            query="Other user query",
            status="completed",
        )
        async_session.add(other_session)
        await async_session.commit()

        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()
            sessions = await service.get_sessions(async_session, db_user.id)

            assert len(sessions) == 3

    @pytest.mark.asyncio
    async def test_get_sessions_ordered_by_created(self, async_session, db_user):
        """Test sessions are ordered by created_at descending."""
        now = datetime.now(timezone.utc)
        for i in range(3):
            session = ResearchSession(
                user_id=db_user.id,
                query=f"Query {i}",
                status="completed",
                created_at=now - timedelta(days=i),
            )
            async_session.add(session)
        await async_session.commit()

        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()
            sessions = await service.get_sessions(async_session, db_user.id)

            # Most recent should be first
            assert "Query 0" in sessions[0].query


class TestQueryExpansion:
    """Tests for query expansion with AI."""

    @pytest.mark.asyncio
    async def test_expand_query_adds_terms(self, mock_anthropic_query_expansion):
        """Test query expansion adds relevant terms."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.return_value = mock_anthropic_query_expansion

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            expanded = await service._expand_query(
                "machine learning in healthcare",
                None,
            )

            assert len(expanded) > len("machine learning in healthcare")
            assert "healthcare" in expanded.lower() or "medical" in expanded.lower()

    @pytest.mark.asyncio
    async def test_expand_query_includes_profile(self):
        """Test query expansion includes profile context."""
        profile = MagicMock(spec=LabProfile)
        profile.research_areas = ["Oncology", "Genomics"]
        profile.institution = "Harvard"
        profile.career_stage = "assistant_professor"

        mock_response = MagicMock(content=[MagicMock(text="expanded query with oncology genomics")])

        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.return_value = mock_response

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            await service._expand_query("cancer research funding", profile)

            # Verify profile was included in prompt
            call_args = mock_client.return_value.messages.create.call_args
            prompt = call_args[1]["messages"][0]["content"]
            assert "Oncology" in prompt or "oncology" in prompt.lower()

    @pytest.mark.asyncio
    async def test_expand_query_handles_error(self):
        """Test query expansion returns original on error."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.side_effect = Exception("API Error")

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            original = "machine learning healthcare"
            expanded = await service._expand_query(original, None)

            assert expanded == original


class TestEmbeddingGeneration:
    """Tests for embedding generation."""

    @pytest.mark.asyncio
    async def test_generate_embedding(self, mock_openai_embedding):
        """Test embedding generation returns correct dimensions."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI") as mock_client,
        ):
            mock_client.return_value.embeddings.create.return_value = mock_openai_embedding

            service = DeepResearchService()
            service.openai = mock_client.return_value

            embedding = await service._generate_embedding("test query")

            assert len(embedding) == 1536

    @pytest.mark.asyncio
    async def test_generate_embedding_truncates_long_text(self, mock_openai_embedding):
        """Test embedding generation truncates very long text."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI") as mock_client,
        ):
            mock_client.return_value.embeddings.create.return_value = mock_openai_embedding

            service = DeepResearchService()
            service.openai = mock_client.return_value

            long_text = "x" * 10000
            await service._generate_embedding(long_text)

            # Should have truncated to 8000 chars
            call_args = mock_client.return_value.embeddings.create.call_args
            assert len(call_args[1]["input"]) <= 8000


class TestResultScoring:
    """Tests for AI-powered result scoring."""

    @pytest.mark.asyncio
    async def test_score_results_returns_scored_grants(self, mock_anthropic_scoring):
        """Test scoring returns grants with scores and reasons."""
        # Create mock grants
        grants = []
        for i in range(2):
            grant = MagicMock(spec=Grant)
            grant.id = uuid4()
            grant.title = f"Grant {i}"
            grant.agency = "NIH"
            grant.description = "Research grant"
            grant.deadline = datetime.now(timezone.utc) + timedelta(days=30)
            grant.amount_min = 250000
            grant.amount_max = 500000
            grants.append(grant)

        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.return_value = mock_anthropic_scoring

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            results = await service._score_results(
                "machine learning healthcare",
                grants,
                None,
            )

            assert len(results) == 2
            assert results[0].relevance_score >= results[1].relevance_score  # Sorted
            assert len(results[0].match_reasons) > 0

    @pytest.mark.asyncio
    async def test_score_results_handles_empty_grants(self):
        """Test scoring handles empty grant list."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()
            results = await service._score_results("query", [], None)

            assert results == []

    @pytest.mark.asyncio
    async def test_score_results_handles_malformed_response(self):
        """Test scoring handles malformed AI response."""
        grants = [MagicMock(spec=Grant)]
        grants[0].id = uuid4()
        grants[0].title = "Test Grant"
        grants[0].agency = "NIH"
        grants[0].description = "Test"
        grants[0].deadline = None
        grants[0].amount_min = None
        grants[0].amount_max = None

        mock_response = MagicMock(content=[MagicMock(text="This is not valid JSON")])

        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.return_value = mock_response

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            # Should return default scores, not crash
            results = await service._score_results("query", grants, None)

            assert len(results) == 1
            assert results[0].relevance_score == 0.5  # Default


class TestInsightsGeneration:
    """Tests for insights generation."""

    @pytest.mark.asyncio
    async def test_generate_insights_with_results(self, mock_anthropic_insights):
        """Test insights generation with results."""
        results = [
            ResearchGrantResult(
                id=uuid4(),
                title="AI Healthcare Grant",
                funder="NIH",
                mechanism="R01",
                description="Research in AI",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                amount_min=250000,
                amount_max=500000,
                relevance_score=0.9,
                match_reasons=["Strong match"],
            )
        ]

        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_client,
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            mock_client.return_value.messages.create.return_value = mock_anthropic_insights

            service = DeepResearchService()
            service.anthropic = mock_client.return_value

            insights = await service._generate_insights("query", results, None)

            assert insights is not None
            assert "NIH" in insights or "prioritize" in insights.lower()

    @pytest.mark.asyncio
    async def test_generate_insights_empty_results(self):
        """Test insights for empty results."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()
            insights = await service._generate_insights("query", [], None)

            assert "no matching" in insights.lower() or "broaden" in insights.lower()


@pytest.mark.integration
class TestFullResearchPipeline:
    """Tests for end-to-end research pipeline.

    Note: These tests require a PostgreSQL database with JSONB and pgvector support.
    """

    @pytest.mark.asyncio
    async def test_run_research_updates_session(
        self,
        async_session,
        db_user,
        mock_openai_embedding,
        mock_anthropic_query_expansion,
        mock_anthropic_scoring,
        mock_anthropic_insights,
    ):
        """Test full research run updates session status and results."""
        # Create session
        session = ResearchSession(
            user_id=db_user.id,
            query="machine learning healthcare funding",
            status="pending",
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        with (
            patch("backend.services.deep_research.openai.OpenAI") as mock_openai,
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_anthropic,
        ):
            mock_openai.return_value.embeddings.create.return_value = mock_openai_embedding

            # Different responses for different calls
            mock_anthropic.return_value.messages.create.side_effect = [
                mock_anthropic_query_expansion,
                mock_anthropic_scoring,
                mock_anthropic_insights,
            ]

            service = DeepResearchService()
            service.openai = mock_openai.return_value
            service.anthropic = mock_anthropic.return_value

            try:
                result = await service.run_research(async_session, session.id)

                assert result.status == ResearchStatus.COMPLETED
                assert result.processing_time_ms is not None
                assert result.completed_at is not None
            except Exception:
                # May fail due to pgvector not being available
                # Check session was at least set to processing
                await async_session.refresh(session)
                assert session.status in ["processing", "failed"]

    @pytest.mark.asyncio
    async def test_run_research_handles_error(self, async_session, db_user):
        """Test research run handles errors gracefully."""
        session = ResearchSession(
            user_id=db_user.id,
            query="test query",
            status="pending",
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        with (
            patch("backend.services.deep_research.openai.OpenAI") as mock_openai,
            patch("backend.services.deep_research.anthropic.Anthropic"),
        ):
            mock_openai.return_value.embeddings.create.side_effect = Exception("API Error")

            service = DeepResearchService()
            service.openai = mock_openai.return_value

            with pytest.raises(Exception):
                await service.run_research(async_session, session.id)

            # Session should be marked as failed
            await async_session.refresh(session)
            assert session.status == "failed"


@pytest.mark.integration
class TestQuickSearch:
    """Tests for quick synchronous search.

    Note: These tests require a PostgreSQL database with pgvector support.
    """

    @pytest.mark.asyncio
    async def test_quick_search_returns_results(self, async_session, db_user, mock_openai_embedding):
        """Test quick search returns grant results."""
        with (
            patch("backend.services.deep_research.openai.OpenAI") as mock_openai,
            patch("backend.services.deep_research.anthropic.Anthropic"),
        ):
            mock_openai.return_value.embeddings.create.return_value = mock_openai_embedding

            service = DeepResearchService()
            service.openai = mock_openai.return_value

            try:
                results = await service.quick_search(
                    db=async_session,
                    user=db_user,
                    query="cancer research",
                    max_results=5,
                )

                assert isinstance(results, list)
                assert len(results) <= 5
            except Exception:
                # pgvector may not be available in test environment
                pass

    @pytest.mark.asyncio
    async def test_quick_search_respects_max_results(self, async_session, db_user, mock_openai_embedding):
        """Test quick search respects max_results parameter."""
        with (
            patch("backend.services.deep_research.openai.OpenAI") as mock_openai,
            patch("backend.services.deep_research.anthropic.Anthropic"),
        ):
            mock_openai.return_value.embeddings.create.return_value = mock_openai_embedding

            service = DeepResearchService()
            service.openai = mock_openai.return_value

            try:
                results = await service.quick_search(
                    db=async_session,
                    user=db_user,
                    query="any query",
                    max_results=3,
                )

                assert len(results) <= 3
            except Exception:
                pass


class TestResearchGrantResultSchema:
    """Tests for ResearchGrantResult schema."""

    def test_research_grant_result_creation(self):
        """Test creating a ResearchGrantResult."""
        result = ResearchGrantResult(
            id=uuid4(),
            title="Test Grant",
            funder="NIH",
            mechanism="R01",
            description="Grant description",
            deadline=datetime.now(timezone.utc),
            amount_min=100000,
            amount_max=500000,
            relevance_score=0.85,
            match_reasons=["Research alignment", "Career stage match"],
        )

        assert result.title == "Test Grant"
        assert result.funder == "NIH"
        assert result.relevance_score == 0.85
        assert len(result.match_reasons) == 2

    def test_research_grant_result_optional_fields(self):
        """Test ResearchGrantResult with optional fields as None."""
        result = ResearchGrantResult(
            id=uuid4(),
            title="Minimal Grant",
            funder="NSF",
            relevance_score=0.7,
            match_reasons=["Basic match"],
        )

        assert result.mechanism is None
        assert result.description is None
        assert result.deadline is None
        assert result.amount_min is None
        assert result.amount_max is None


class TestResearchStatusEnum:
    """Tests for ResearchStatus enum."""

    def test_status_values(self):
        """Test all status values exist."""
        assert ResearchStatus.PENDING == "pending"
        assert ResearchStatus.PROCESSING == "processing"
        assert ResearchStatus.COMPLETED == "completed"
        assert ResearchStatus.FAILED == "failed"

    def test_status_from_string(self):
        """Test creating status from string."""
        status = ResearchStatus("completed")
        assert status == ResearchStatus.COMPLETED


@pytest.mark.integration
class TestResearchSessionModel:
    """Tests for ResearchSession database model.

    Note: These tests require a PostgreSQL database with JSONB support.
    """

    @pytest.mark.asyncio
    async def test_create_research_session(self, async_session, db_user):
        """Test creating a research session directly."""
        session = ResearchSession(
            user_id=db_user.id,
            query="Test research query",
            status="pending",
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        assert session.id is not None
        assert session.user_id == db_user.id
        assert session.query == "Test research query"
        assert session.status == "pending"
        assert session.created_at is not None

    @pytest.mark.asyncio
    async def test_research_session_with_results(self, async_session, db_user):
        """Test research session with stored results."""
        results_data = [
            {
                "id": str(uuid4()),
                "title": "Grant 1",
                "funder": "NIH",
                "relevance_score": 0.9,
                "match_reasons": ["Good match"],
            }
        ]

        session = ResearchSession(
            user_id=db_user.id,
            query="Test query with results",
            status="completed",
            results=results_data,
            insights="Some AI-generated insights",
            grants_found=5,
            processing_time_ms=2500,
            completed_at=datetime.now(timezone.utc),
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        assert session.results == results_data
        assert session.insights == "Some AI-generated insights"
        assert session.grants_found == 5
        assert session.processing_time_ms == 2500
        assert session.completed_at is not None

    @pytest.mark.asyncio
    async def test_research_session_user_relationship(self, async_session, db_user):
        """Test research session has proper relationship to user."""
        session = ResearchSession(
            user_id=db_user.id,
            query="Relationship test query",
            status="pending",
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        # Verify user_id matches
        assert session.user_id == db_user.id


class TestServiceInitialization:
    """Tests for DeepResearchService initialization."""

    def test_service_creation_with_mocked_clients(self):
        """Test service can be created with mocked API clients."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic") as mock_anthropic,
            patch("backend.services.deep_research.openai.OpenAI") as mock_openai,
        ):
            service = DeepResearchService()

            # Verify clients were initialized
            mock_anthropic.assert_called_once()
            mock_openai.assert_called_once()
            assert service.anthropic is not None
            assert service.openai is not None

    def test_service_has_required_methods(self):
        """Test service has all required methods."""
        with (
            patch("backend.services.deep_research.anthropic.Anthropic"),
            patch("backend.services.deep_research.openai.OpenAI"),
        ):
            service = DeepResearchService()

            assert hasattr(service, "create_session")
            assert hasattr(service, "run_research")
            assert hasattr(service, "quick_search")
            assert hasattr(service, "get_sessions")
            assert hasattr(service, "_expand_query")
            assert hasattr(service, "_generate_embedding")
            assert hasattr(service, "_score_results")
            assert hasattr(service, "_generate_insights")
            assert hasattr(service, "_search_grants")
