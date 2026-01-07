"""
Matching Engine Tests
Tests for vector similarity matching, LLM re-ranking, and score calculations.
"""
import json
import math
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.matching.models import (
    MatchResult,
    ProfileEmbedding,
    UserProfile,
    GrantData,
    ProfileMatch,
    BatchMatchRequest,
    BatchMatchResponse,
    FinalMatch,
)
from backend.core.events import MatchComputedEvent, PriorityLevel


# =============================================================================
# Vector Similarity Tests
# =============================================================================


class TestVectorSimilarity:
    """Tests for vector similarity calculations."""

    @pytest.fixture
    def similarity_calculator(self):
        """Create a similarity calculator."""
        class SimilarityCalculator:
            @staticmethod
            def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
                """Calculate cosine similarity between two vectors."""
                if len(vec1) != len(vec2):
                    raise ValueError("Vectors must have same dimension")

                dot_product = sum(a * b for a, b in zip(vec1, vec2))
                norm1 = math.sqrt(sum(a * a for a in vec1))
                norm2 = math.sqrt(sum(b * b for b in vec2))

                if norm1 == 0 or norm2 == 0:
                    return 0.0

                return dot_product / (norm1 * norm2)

            @staticmethod
            def euclidean_distance(vec1: list[float], vec2: list[float]) -> float:
                """Calculate euclidean distance between two vectors."""
                if len(vec1) != len(vec2):
                    raise ValueError("Vectors must have same dimension")

                return math.sqrt(sum((a - b) ** 2 for a, b in zip(vec1, vec2)))

        return SimilarityCalculator()

    def test_cosine_similarity_identical(self, similarity_calculator, sample_embedding):
        """Test cosine similarity for identical vectors."""
        similarity = similarity_calculator.cosine_similarity(sample_embedding, sample_embedding)
        assert similarity == pytest.approx(1.0, rel=1e-6)

    def test_cosine_similarity_similar(self, similarity_calculator, sample_embedding, high_similarity_embedding):
        """Test cosine similarity for similar vectors."""
        similarity = similarity_calculator.cosine_similarity(sample_embedding, high_similarity_embedding)
        assert similarity > 0.95  # Should be very high

    def test_cosine_similarity_different(self, similarity_calculator, sample_embedding, low_similarity_embedding):
        """Test cosine similarity for different vectors."""
        similarity = similarity_calculator.cosine_similarity(sample_embedding, low_similarity_embedding)
        assert similarity < 0.5  # Should be relatively low

    def test_cosine_similarity_orthogonal(self, similarity_calculator):
        """Test cosine similarity for orthogonal vectors."""
        vec1 = [1.0, 0.0, 0.0]
        vec2 = [0.0, 1.0, 0.0]
        similarity = similarity_calculator.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(0.0, abs=1e-6)

    def test_cosine_similarity_opposite(self, similarity_calculator):
        """Test cosine similarity for opposite vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [-1.0, -2.0, -3.0]
        similarity = similarity_calculator.cosine_similarity(vec1, vec2)
        assert similarity == pytest.approx(-1.0, rel=1e-6)

    def test_cosine_similarity_dimension_mismatch(self, similarity_calculator):
        """Test error handling for dimension mismatch."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [1.0, 2.0]
        with pytest.raises(ValueError):
            similarity_calculator.cosine_similarity(vec1, vec2)

    def test_cosine_similarity_zero_vector(self, similarity_calculator):
        """Test handling of zero vectors."""
        vec1 = [1.0, 2.0, 3.0]
        vec2 = [0.0, 0.0, 0.0]
        similarity = similarity_calculator.cosine_similarity(vec1, vec2)
        assert similarity == 0.0


# =============================================================================
# Profile Matching Model Tests
# =============================================================================


class TestUserProfile:
    """Tests for UserProfile model."""

    def test_user_profile_to_embedding_text(self):
        """Test generating embedding text from profile."""
        profile = UserProfile(
            user_id=uuid.uuid4(),
            research_areas=["machine learning", "NLP"],
            methods=["deep learning", "transformers"],
            past_grants=["NSF grant 2022", "NIH grant 2021"],
            institution="Stanford",
            department="Computer Science",
            keywords=["AI", "healthcare"],
        )

        text = profile.to_embedding_text()

        assert "Research areas: machine learning, NLP" in text
        assert "Methods: deep learning, transformers" in text
        assert "Institution: Stanford" in text

    def test_user_profile_partial_data(self):
        """Test embedding text with partial data."""
        profile = UserProfile(
            user_id=uuid.uuid4(),
            research_areas=["biology"],
        )

        text = profile.to_embedding_text()

        assert "Research areas: biology" in text
        assert "Methods:" not in text
        assert "Institution:" not in text


class TestGrantData:
    """Tests for GrantData model."""

    def test_grant_data_to_matching_text(self):
        """Test generating matching text from grant."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="AI in Healthcare Research",
            description="Research grant for AI applications in medicine",
            funding_agency="NIH",
            funding_amount=500000.0,
            deadline=datetime(2024, 12, 31),
            eligibility_criteria=["US institutions", "Early career researchers"],
            categories=["AI", "healthcare"],
        )

        text = grant.to_matching_text()

        assert "Title: AI in Healthcare Research" in text
        assert "Funding Agency: NIH" in text
        assert "Funding Amount: $500,000.00" in text
        assert "Deadline: 2024-12-31" in text

    def test_grant_data_minimal(self):
        """Test matching text with minimal data."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="Test Grant",
            description="A test grant",
        )

        text = grant.to_matching_text()

        assert "Title: Test Grant" in text
        assert "Description: A test grant" in text
        assert "Funding Agency:" not in text


class TestFinalMatch:
    """Tests for FinalMatch model and score computation."""

    def test_compute_final_score(self):
        """Test weighted final score computation."""
        # 40% vector similarity + 60% LLM score
        vector_sim = 0.8  # 80 on 0-100 scale
        llm_score = 90.0

        final_score = FinalMatch.compute_final_score(vector_sim, llm_score)

        # Expected: (0.4 * 80) + (0.6 * 90) = 32 + 54 = 86
        assert final_score == pytest.approx(86.0, rel=1e-2)

    def test_compute_final_score_extremes(self):
        """Test final score computation at extremes."""
        # All zeros
        score_zero = FinalMatch.compute_final_score(0.0, 0.0)
        assert score_zero == 0.0

        # All max
        score_max = FinalMatch.compute_final_score(1.0, 100.0)
        assert score_max == 100.0

    def test_compute_final_score_vector_dominant(self):
        """Test when vector similarity is high but LLM is low."""
        score = FinalMatch.compute_final_score(1.0, 0.0)
        # Expected: (0.4 * 100) + (0.6 * 0) = 40
        assert score == pytest.approx(40.0, rel=1e-2)

    def test_compute_final_score_llm_dominant(self):
        """Test when LLM score is high but vector is low."""
        score = FinalMatch.compute_final_score(0.0, 100.0)
        # Expected: (0.4 * 0) + (0.6 * 100) = 60
        assert score == pytest.approx(60.0, rel=1e-2)


class TestMatchResult:
    """Tests for MatchResult model."""

    def test_match_result_valid(self):
        """Test creating a valid match result."""
        result = MatchResult(
            match_score=85.0,
            reasoning="Strong alignment in research focus",
            key_strengths=["Similar research area", "Prior funding experience"],
            concerns=["Timeline may be tight"],
            predicted_success=72.0,
        )

        assert result.match_score == 85.0
        assert len(result.key_strengths) == 2
        assert len(result.concerns) == 1

    def test_match_result_score_bounds(self):
        """Test match score bounds validation."""
        # Valid bounds
        result = MatchResult(
            match_score=0.0,
            reasoning="Test",
            predicted_success=0.0,
        )
        assert result.match_score == 0.0

        result = MatchResult(
            match_score=100.0,
            reasoning="Test",
            predicted_success=100.0,
        )
        assert result.match_score == 100.0

        # Invalid bounds should raise
        with pytest.raises(ValueError):
            MatchResult(
                match_score=-1.0,
                reasoning="Test",
                predicted_success=50.0,
            )

        with pytest.raises(ValueError):
            MatchResult(
                match_score=101.0,
                reasoning="Test",
                predicted_success=50.0,
            )


# =============================================================================
# LLM Re-ranking Tests
# =============================================================================


class TestLLMReRanking:
    """Tests for LLM-based match re-ranking."""

    @pytest.fixture
    def mock_llm_ranker(self, mock_anthropic):
        """Create a mock LLM ranker."""
        class LLMRanker:
            def __init__(self, client):
                self.client = client

            async def evaluate_match(self, grant: GrantData, profile: UserProfile) -> MatchResult:
                """Evaluate a single match using LLM."""
                prompt = f"""Evaluate this grant-researcher match and provide:
                1. Match score (0-100)
                2. Reasoning
                3. Key strengths
                4. Concerns
                5. Predicted success rate (0-100)

                Grant:
                {grant.to_matching_text()}

                Researcher Profile:
                {profile.to_embedding_text()}

                Return as JSON."""

                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=2000,
                    messages=[{"role": "user", "content": prompt}],
                )

                return MatchResult(**json.loads(response.content[0].text))

            async def batch_evaluate(self, request: BatchMatchRequest) -> BatchMatchResponse:
                """Evaluate multiple profiles against one grant."""
                import time
                start = time.time()

                results = []
                for profile_match in request.profiles:
                    result = await self.evaluate_match(request.grant, profile_match.profile)
                    results.append((profile_match.user_id, result))

                processing_time = (time.time() - start) * 1000

                return BatchMatchResponse(
                    grant_id=request.grant.grant_id,
                    results=results,
                    processing_time_ms=processing_time,
                )

        return LLMRanker(mock_anthropic.return_value)

    @pytest.mark.asyncio
    async def test_evaluate_single_match(self, mock_llm_ranker, mock_anthropic):
        """Test evaluating a single match."""
        mock_anthropic.return_value.messages.create.return_value.content[0].text = json.dumps({
            "match_score": 85,
            "reasoning": "Strong research alignment",
            "key_strengths": ["Similar focus area"],
            "concerns": [],
            "predicted_success": 72,
        })

        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="AI Research Grant",
            description="Funding for AI research",
        )

        profile = UserProfile(
            user_id=uuid.uuid4(),
            research_areas=["artificial intelligence"],
        )

        result = await mock_llm_ranker.evaluate_match(grant, profile)

        assert result.match_score == 85
        assert result.predicted_success == 72

    @pytest.mark.asyncio
    async def test_batch_evaluate(self, mock_llm_ranker, mock_anthropic):
        """Test batch evaluation of multiple profiles."""
        mock_anthropic.return_value.messages.create.return_value.content[0].text = json.dumps({
            "match_score": 80,
            "reasoning": "Good match",
            "key_strengths": [],
            "concerns": [],
            "predicted_success": 70,
        })

        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="Test Grant",
            description="Test description",
        )

        profiles = [
            ProfileMatch(
                user_id=uuid.uuid4(),
                vector_similarity=0.8,
                profile=UserProfile(user_id=uuid.uuid4(), research_areas=["area1"]),
            )
            for _ in range(3)
        ]

        request = BatchMatchRequest(grant=grant, profiles=profiles)
        response = await mock_llm_ranker.batch_evaluate(request)

        assert response.grant_id == grant.grant_id
        assert len(response.results) == 3
        assert response.processing_time_ms > 0


# =============================================================================
# Batch Processing Tests
# =============================================================================


class TestBatchProcessing:
    """Tests for batch matching operations."""

    @pytest.fixture
    def batch_matcher(self):
        """Create a mock batch matcher."""
        class BatchMatcher:
            def __init__(self, batch_size: int = 5):
                self.batch_size = batch_size

            def create_batches(self, profiles: list, grant: GrantData) -> list[BatchMatchRequest]:
                """Split profiles into batches."""
                batches = []
                for i in range(0, len(profiles), self.batch_size):
                    batch_profiles = profiles[i:i + self.batch_size]
                    batches.append(BatchMatchRequest(
                        grant=grant,
                        profiles=batch_profiles,
                    ))
                return batches

            async def process_all_batches(
                self,
                batches: list[BatchMatchRequest],
                llm_ranker
            ) -> list[tuple[uuid.UUID, MatchResult]]:
                """Process all batches and aggregate results."""
                all_results = []
                for batch in batches:
                    response = await llm_ranker.batch_evaluate(batch)
                    all_results.extend(response.results)
                return all_results

        return BatchMatcher()

    def test_create_batches_even_split(self, batch_matcher):
        """Test batch creation with even split."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="Test",
            description="Test",
        )

        profiles = [
            ProfileMatch(
                user_id=uuid.uuid4(),
                vector_similarity=0.8,
                profile=UserProfile(user_id=uuid.uuid4()),
            )
            for _ in range(10)
        ]

        batches = batch_matcher.create_batches(profiles, grant)

        assert len(batches) == 2
        assert len(batches[0].profiles) == 5
        assert len(batches[1].profiles) == 5

    def test_create_batches_uneven_split(self, batch_matcher):
        """Test batch creation with uneven split."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="Test",
            description="Test",
        )

        profiles = [
            ProfileMatch(
                user_id=uuid.uuid4(),
                vector_similarity=0.8,
                profile=UserProfile(user_id=uuid.uuid4()),
            )
            for _ in range(7)
        ]

        batches = batch_matcher.create_batches(profiles, grant)

        assert len(batches) == 2
        assert len(batches[0].profiles) == 5
        assert len(batches[1].profiles) == 2

    def test_create_batches_single(self, batch_matcher):
        """Test batch creation with fewer than batch size."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="Test",
            description="Test",
        )

        profiles = [
            ProfileMatch(
                user_id=uuid.uuid4(),
                vector_similarity=0.8,
                profile=UserProfile(user_id=uuid.uuid4()),
            )
            for _ in range(3)
        ]

        batches = batch_matcher.create_batches(profiles, grant)

        assert len(batches) == 1
        assert len(batches[0].profiles) == 3


# =============================================================================
# Score Calculation Tests
# =============================================================================


class TestScoreCalculation:
    """Tests for various score calculation methods."""

    @pytest.fixture
    def score_calculator(self):
        """Create a score calculator."""
        class ScoreCalculator:
            @staticmethod
            def normalize_score(score: float, min_val: float, max_val: float) -> float:
                """Normalize a score to 0-1 range."""
                if max_val == min_val:
                    return 0.5
                return (score - min_val) / (max_val - min_val)

            @staticmethod
            def calculate_priority(
                match_score: float,
                deadline: datetime | None,
                threshold_critical: float = 0.95,
                threshold_high: float = 0.85,
                threshold_medium: float = 0.70,
            ) -> PriorityLevel:
                """Calculate priority level based on score and deadline."""
                now = datetime.now(timezone.utc)
                days_to_deadline = float("inf")

                if deadline:
                    days_to_deadline = (deadline - now).days

                # Critical: high score AND urgent deadline
                if match_score >= threshold_critical and days_to_deadline <= 14:
                    return PriorityLevel.CRITICAL

                # High: high score OR (good score AND approaching deadline)
                if match_score >= threshold_high:
                    return PriorityLevel.HIGH
                if match_score >= threshold_medium and days_to_deadline <= 30:
                    return PriorityLevel.HIGH

                # Medium: decent score
                if match_score >= threshold_medium:
                    return PriorityLevel.MEDIUM

                # Low: below threshold
                return PriorityLevel.LOW

            @staticmethod
            def decay_score_by_time(
                base_score: float,
                elapsed_hours: float,
                half_life_hours: float = 168.0,  # 1 week
            ) -> float:
                """Apply time decay to a score."""
                decay_factor = 0.5 ** (elapsed_hours / half_life_hours)
                return base_score * decay_factor

        return ScoreCalculator()

    def test_normalize_score(self, score_calculator):
        """Test score normalization."""
        # Middle value
        normalized = score_calculator.normalize_score(50.0, 0.0, 100.0)
        assert normalized == 0.5

        # Min value
        normalized = score_calculator.normalize_score(0.0, 0.0, 100.0)
        assert normalized == 0.0

        # Max value
        normalized = score_calculator.normalize_score(100.0, 0.0, 100.0)
        assert normalized == 1.0

    def test_calculate_priority_critical(self, score_calculator):
        """Test critical priority calculation."""
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        priority = score_calculator.calculate_priority(0.96, deadline)
        assert priority == PriorityLevel.CRITICAL

    def test_calculate_priority_high(self, score_calculator):
        """Test high priority calculation."""
        # High score alone
        priority = score_calculator.calculate_priority(0.90, None)
        assert priority == PriorityLevel.HIGH

        # Medium score with approaching deadline
        deadline = datetime.now(timezone.utc) + timedelta(days=20)
        priority = score_calculator.calculate_priority(0.75, deadline)
        assert priority == PriorityLevel.HIGH

    def test_calculate_priority_medium(self, score_calculator):
        """Test medium priority calculation."""
        priority = score_calculator.calculate_priority(0.75, None)
        assert priority == PriorityLevel.MEDIUM

    def test_calculate_priority_low(self, score_calculator):
        """Test low priority calculation."""
        priority = score_calculator.calculate_priority(0.50, None)
        assert priority == PriorityLevel.LOW

    def test_decay_score_by_time(self, score_calculator):
        """Test time decay on scores."""
        base_score = 100.0

        # No decay at time 0
        decayed = score_calculator.decay_score_by_time(base_score, 0.0)
        assert decayed == 100.0

        # Half decay at half-life
        decayed = score_calculator.decay_score_by_time(base_score, 168.0)
        assert decayed == pytest.approx(50.0, rel=1e-2)

        # Quarter at 2x half-life
        decayed = score_calculator.decay_score_by_time(base_score, 336.0)
        assert decayed == pytest.approx(25.0, rel=1e-2)


# =============================================================================
# Edge Case Tests
# =============================================================================


class TestMatchingEdgeCases:
    """Tests for edge cases in matching."""

    def test_no_matches_found(self):
        """Test handling when no matches are found."""
        matches = []
        filtered = [m for m in matches if m.get("score", 0) >= 0.7]
        assert len(filtered) == 0

    def test_all_matches_high_score(self):
        """Test handling when all matches have high scores."""
        matches = [
            {"user_id": uuid.uuid4(), "score": 0.95},
            {"user_id": uuid.uuid4(), "score": 0.92},
            {"user_id": uuid.uuid4(), "score": 0.90},
        ]
        filtered = [m for m in matches if m["score"] >= 0.7]
        assert len(filtered) == 3

    def test_duplicate_user_matches(self):
        """Test deduplication of user matches."""
        user_id = uuid.uuid4()
        grant_id1 = uuid.uuid4()
        grant_id2 = uuid.uuid4()

        matches = [
            {"user_id": user_id, "grant_id": grant_id1, "score": 0.85},
            {"user_id": user_id, "grant_id": grant_id1, "score": 0.80},  # Duplicate
            {"user_id": user_id, "grant_id": grant_id2, "score": 0.90},
        ]

        # Keep highest score per user-grant pair
        seen = {}
        for m in matches:
            key = (m["user_id"], m["grant_id"])
            if key not in seen or m["score"] > seen[key]["score"]:
                seen[key] = m

        deduped = list(seen.values())
        assert len(deduped) == 2

    def test_empty_profile_matching(self):
        """Test matching with empty profile."""
        profile = UserProfile(user_id=uuid.uuid4())

        text = profile.to_embedding_text()
        assert text == ""

    def test_empty_grant_matching(self):
        """Test matching with minimal grant data."""
        grant = GrantData(
            grant_id=uuid.uuid4(),
            title="",
            description="",
        )

        text = grant.to_matching_text()
        assert "Title:" in text
        assert "Description:" in text


# =============================================================================
# Event Generation Tests
# =============================================================================


class TestMatchEventGeneration:
    """Tests for generating match events."""

    def test_create_match_computed_event(self):
        """Test creating a MatchComputedEvent."""
        event = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            match_score=0.87,
            priority_level=PriorityLevel.HIGH,
            matching_criteria=["research_area", "methods"],
            explanation="Strong alignment in AI research focus.",
            grant_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        )

        assert event.match_score == 0.87
        assert event.priority_level == PriorityLevel.HIGH
        assert len(event.matching_criteria) == 2

    def test_match_event_serialization(self, sample_match_computed_event):
        """Test match event JSON serialization."""
        json_str = sample_match_computed_event.model_dump_json()
        parsed = json.loads(json_str)

        assert "match_id" in parsed
        assert "match_score" in parsed
        assert "priority_level" in parsed

    def test_match_event_deserialization(self):
        """Test match event deserialization."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "match_id": str(uuid.uuid4()),
            "grant_id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "match_score": 0.75,
            "priority_level": "medium",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        event = MatchComputedEvent(**event_data)

        assert event.match_score == 0.75
        assert event.priority_level == PriorityLevel.MEDIUM


# =============================================================================
# Performance Tests
# =============================================================================


class TestMatchingPerformance:
    """Tests for matching performance characteristics."""

    @pytest.mark.slow
    def test_large_batch_processing(self):
        """Test processing a large batch of profiles."""
        import time

        num_profiles = 100
        profiles = [
            ProfileMatch(
                user_id=uuid.uuid4(),
                vector_similarity=0.5 + (i / 200),  # Varying similarities
                profile=UserProfile(
                    user_id=uuid.uuid4(),
                    research_areas=[f"area_{i}"],
                ),
            )
            for i in range(num_profiles)
        ]

        # Simulate sorting by similarity (common operation)
        start = time.time()
        sorted_profiles = sorted(profiles, key=lambda p: p.vector_similarity, reverse=True)
        elapsed = time.time() - start

        assert len(sorted_profiles) == num_profiles
        assert sorted_profiles[0].vector_similarity > sorted_profiles[-1].vector_similarity
        assert elapsed < 0.1  # Should be very fast

    @pytest.mark.slow
    def test_embedding_dimension_consistency(self, sample_embedding):
        """Test that embeddings maintain consistent dimensions."""
        embeddings = [sample_embedding for _ in range(100)]

        # All should have same dimension
        dimensions = set(len(e) for e in embeddings)
        assert len(dimensions) == 1
        assert 1536 in dimensions
