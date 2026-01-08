"""
Integration tests for Grant Matcher.
Tests the full matching workflow with mocked external services.
"""
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from agents.matching.matcher import GrantMatcher
from agents.matching.models import (
    BatchMatchRequest,
    BatchMatchResponse,
    FinalMatch,
    GrantData,
    MatchResult,
    ProfileMatch,
    UserProfile,
)
from backend.core.events import PriorityLevel


class TestGrantDataFetching:
    """Tests for fetching grant data from database."""

    def test_fetch_grant_data_success(self, sample_grant_data, mock_db_engine):
        """Test successful grant data fetch."""
        from tests.agents.matching.conftest import create_mock_db_result

        mock_session = MagicMock()
        mock_result = create_mock_db_result({
            "grant_id": sample_grant_data["id"],
            "title": sample_grant_data["title"],
            "description": sample_grant_data["description"],
            "agency": sample_grant_data["agency"],
            "amount_min": sample_grant_data["amount_min"],
            "amount_max": sample_grant_data["amount_max"],
            "deadline": sample_grant_data["deadline"],
            "eligibility": sample_grant_data["eligibility"],
            "categories": sample_grant_data["categories"],
            "embedding": sample_grant_data["embedding"],
        })
        mock_session.execute.return_value.fetchone.return_value = mock_result

        matcher = GrantMatcher(mock_db_engine)
        grant = matcher.fetch_grant_data(sample_grant_data["id"], mock_session)

        assert grant is not None
        assert grant.title == sample_grant_data["title"]
        assert grant.funding_agency == sample_grant_data["agency"]

    def test_fetch_grant_data_not_found(self, mock_db_engine):
        """Test handling of missing grant."""
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None

        matcher = GrantMatcher(mock_db_engine)
        grant = matcher.fetch_grant_data(uuid4(), mock_session)

        assert grant is None


class TestVectorSearch:
    """Tests for vector similarity search."""

    def test_find_similar_profiles_returns_matches(self, mock_db_engine, sample_user_profile):
        """Test that vector search returns matching profiles."""
        from tests.agents.matching.conftest import create_mock_db_result

        mock_session = MagicMock()
        mock_results = [
            create_mock_db_result({
                "user_id": str(sample_user_profile["user_id"]),
                "similarity": 0.85,
                "research_areas": sample_user_profile["research_areas"],
                "methods": sample_user_profile["methods"],
                "past_grants": sample_user_profile["past_grants"],
                "institution": sample_user_profile["institution"],
                "department": sample_user_profile["department"],
                "keywords": sample_user_profile["keywords"],
            }),
        ]
        mock_session.execute.return_value.fetchall.return_value = mock_results

        matcher = GrantMatcher(mock_db_engine)
        embedding = [0.1] * 1536

        matches = matcher.find_similar_profiles(embedding, mock_session)

        assert len(matches) == 1
        assert matches[0].vector_similarity == 0.85
        assert matches[0].profile.institution == "Stanford University"

    def test_find_similar_profiles_empty(self, mock_db_engine):
        """Test handling of no matching profiles."""
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = []

        matcher = GrantMatcher(mock_db_engine)
        embedding = [0.1] * 1536

        matches = matcher.find_similar_profiles(embedding, mock_session)

        assert len(matches) == 0


class TestLLMEvaluation:
    """Tests for LLM batch evaluation."""

    @patch("agents.matching.matcher.anthropic")
    def test_evaluate_matches_batch_success(
        self, mock_anthropic, mock_db_engine, grant_data_full, profile_match, sample_match_result
    ):
        """Test successful batch LLM evaluation."""
        # Setup mock response
        sample_match_result["user_id"] = str(profile_match.user_id)
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps([sample_match_result]))]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        # Create matcher and evaluate
        matcher = GrantMatcher(mock_db_engine)
        request = BatchMatchRequest(
            grant=grant_data_full,
            profiles=[profile_match],
        )

        response = matcher.evaluate_matches_batch(request)

        assert response.grant_id == grant_data_full.grant_id
        assert len(response.results) == 1
        assert response.results[0][1].match_score == 85

    @patch("agents.matching.matcher.anthropic")
    def test_evaluate_matches_batch_json_error(
        self, mock_anthropic, mock_db_engine, grant_data_full, profile_match
    ):
        """Test handling of invalid JSON response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="invalid json")]

        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.Anthropic.return_value = mock_client

        matcher = GrantMatcher(mock_db_engine)
        request = BatchMatchRequest(
            grant=grant_data_full,
            profiles=[profile_match],
        )

        with pytest.raises(json.JSONDecodeError):
            matcher.evaluate_matches_batch(request)


class TestPriorityComputation:
    """Tests for priority level computation."""

    def test_critical_priority_high_score_urgent(self, mock_db_engine):
        """Test CRITICAL priority for high score + urgent deadline."""
        matcher = GrantMatcher(mock_db_engine)

        # Score 95, deadline in 3 days
        deadline = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        from datetime import timedelta
        deadline = deadline + timedelta(days=3)

        priority = matcher._compute_priority_level(95, deadline)

        assert priority == PriorityLevel.CRITICAL

    def test_high_priority_good_score(self, mock_db_engine):
        """Test HIGH priority for good score."""
        matcher = GrantMatcher(mock_db_engine)

        priority = matcher._compute_priority_level(85, None)

        assert priority == PriorityLevel.HIGH

    def test_medium_priority_decent_score(self, mock_db_engine):
        """Test MEDIUM priority for decent score."""
        matcher = GrantMatcher(mock_db_engine)

        priority = matcher._compute_priority_level(75, None)

        assert priority == PriorityLevel.MEDIUM

    def test_low_priority_below_threshold(self, mock_db_engine):
        """Test LOW priority for below-threshold score."""
        matcher = GrantMatcher(mock_db_engine)

        priority = matcher._compute_priority_level(60, None)

        assert priority == PriorityLevel.LOW


class TestMatchStorage:
    """Tests for match storage."""

    def test_store_match_executes_query(self, mock_db_engine):
        """Test that store_match executes upsert query."""
        mock_session = MagicMock()

        matcher = GrantMatcher(mock_db_engine)
        match = FinalMatch(
            match_id=uuid4(),
            grant_id=uuid4(),
            user_id=uuid4(),
            vector_similarity=0.85,
            llm_match_score=80,
            final_score=82,
            reasoning="Good match",
            key_strengths=["Strong background"],
            concerns=["Limited experience"],
            predicted_success=75,
            created_at=datetime.now(timezone.utc),
        )

        matcher.store_match(match, mock_session)

        mock_session.execute.assert_called_once()


class TestMatchPublishing:
    """Tests for match publishing to Redis."""

    def test_publish_match_success(self, mock_db_engine, mock_redis_client, grant_data_full):
        """Test successful match publishing."""
        matcher = GrantMatcher(mock_db_engine)
        matcher._redis_client = mock_redis_client

        match = FinalMatch(
            match_id=uuid4(),
            grant_id=grant_data_full.grant_id,
            user_id=uuid4(),
            vector_similarity=0.85,
            llm_match_score=80,
            final_score=82,
            reasoning="Good match",
            key_strengths=["Strong background"],
            concerns=[],
            predicted_success=75,
            created_at=datetime.now(timezone.utc),
        )

        message_id = matcher.publish_match(match, grant_data_full)

        assert message_id == "1234567890-0"
        mock_redis_client.xadd.assert_called_once()


class TestFinalScoreComputation:
    """Tests for final score computation."""

    def test_compute_final_score_balanced(self):
        """Test balanced final score (40% vector + 60% LLM)."""
        # Vector: 0.8 (80%), LLM: 85
        score = FinalMatch.compute_final_score(0.8, 85)

        # Expected: 0.4 * 80 + 0.6 * 85 = 32 + 51 = 83
        assert score == 83

    def test_compute_final_score_high_vector(self):
        """Test with high vector similarity."""
        score = FinalMatch.compute_final_score(1.0, 70)

        # Expected: 0.4 * 100 + 0.6 * 70 = 40 + 42 = 82
        assert score == 82

    def test_compute_final_score_high_llm(self):
        """Test with high LLM score."""
        score = FinalMatch.compute_final_score(0.5, 100)

        # Expected: 0.4 * 50 + 0.6 * 100 = 20 + 60 = 80
        assert score == 80


class TestProcessGrantWorkflow:
    """Integration tests for the full process_grant workflow."""

    @patch("agents.matching.matcher.anthropic")
    def test_process_grant_no_embedding(self, mock_anthropic, mock_db_engine):
        """Test that grants without embeddings are skipped."""
        from tests.agents.matching.conftest import create_mock_db_result

        mock_session = MagicMock()
        # Grant exists but has no embedding
        mock_result = create_mock_db_result({
            "grant_id": uuid4(),
            "title": "Test Grant",
            "description": "Description",
            "agency": "NSF",
            "amount_min": None,
            "amount_max": None,
            "deadline": None,
            "eligibility": None,
            "categories": None,
            "embedding": None,  # No embedding
        })
        mock_session.execute.return_value.fetchone.return_value = mock_result

        matcher = GrantMatcher(mock_db_engine)

        with patch("agents.matching.matcher.Session") as mock_session_class:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_session)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_context

            stats = matcher.process_grant(uuid4())

        assert stats["matches_stored"] == 0
        assert stats["candidates_found"] == 0

    @patch("agents.matching.matcher.anthropic")
    def test_process_grant_no_candidates(self, mock_anthropic, mock_db_engine, sample_grant_data):
        """Test handling when no candidates match."""
        from tests.agents.matching.conftest import create_mock_db_result

        mock_session = MagicMock()

        # First call returns grant data
        mock_grant = create_mock_db_result({
            "grant_id": sample_grant_data["id"],
            "title": sample_grant_data["title"],
            "description": sample_grant_data["description"],
            "agency": sample_grant_data["agency"],
            "amount_min": sample_grant_data["amount_min"],
            "amount_max": sample_grant_data["amount_max"],
            "deadline": sample_grant_data["deadline"],
            "eligibility": sample_grant_data["eligibility"],
            "categories": sample_grant_data["categories"],
            "embedding": sample_grant_data["embedding"],
        })

        # Configure mock to return grant first, then empty candidates
        call_count = [0]
        def mock_execute(*args, **kwargs):
            call_count[0] += 1
            result = MagicMock()
            if call_count[0] == 1:
                # First call - fetch grant
                result.fetchone.return_value = mock_grant
            else:
                # Second call - find profiles (none found)
                result.fetchall.return_value = []
            return result

        mock_session.execute = mock_execute

        matcher = GrantMatcher(mock_db_engine)

        with patch("agents.matching.matcher.Session") as mock_session_class:
            mock_context = MagicMock()
            mock_context.__enter__ = MagicMock(return_value=mock_session)
            mock_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_context

            stats = matcher.process_grant(sample_grant_data["id"])

        assert stats["candidates_found"] == 0
        assert stats["llm_evaluated"] == 0
