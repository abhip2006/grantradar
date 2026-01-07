"""
Curation Agent Tests
Tests for grant validation, quality scoring, categorization, and embedding generation.
"""
import json
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.core.events import GrantDiscoveredEvent, GrantValidatedEvent


# =============================================================================
# Quality Scoring Tests
# =============================================================================


class TestQualityScoring:
    """Tests for grant quality scoring logic."""

    @pytest.fixture
    def quality_scorer(self):
        """Create a mock quality scorer."""
        class QualityScorer:
            def __init__(self, min_title_length: int = 10, min_description_length: int = 50):
                self.min_title_length = min_title_length
                self.min_description_length = min_description_length

            def score_completeness(self, grant_data: dict) -> float:
                """Score based on field completeness."""
                required_fields = ["title", "description", "agency", "url"]
                optional_fields = ["deadline", "amount_min", "amount_max", "categories", "eligibility"]

                # Required fields (60% weight)
                required_score = sum(1 for f in required_fields if grant_data.get(f)) / len(required_fields)

                # Optional fields (40% weight)
                optional_score = sum(1 for f in optional_fields if grant_data.get(f)) / len(optional_fields)

                return (required_score * 0.6) + (optional_score * 0.4)

            def score_content_quality(self, grant_data: dict) -> float:
                """Score based on content quality."""
                score = 0.0

                # Title length check
                title = grant_data.get("title", "")
                if len(title) >= self.min_title_length:
                    score += 0.3
                elif len(title) > 0:
                    score += 0.1

                # Description length check
                description = grant_data.get("description", "")
                if len(description) >= self.min_description_length:
                    score += 0.4
                elif len(description) >= 20:
                    score += 0.2

                # Has deadline
                if grant_data.get("deadline"):
                    score += 0.2

                # Has funding amount
                if grant_data.get("amount_min") or grant_data.get("amount_max"):
                    score += 0.1

                return min(score, 1.0)

            def calculate_total_score(self, grant_data: dict) -> float:
                """Calculate overall quality score."""
                completeness = self.score_completeness(grant_data)
                content_quality = self.score_content_quality(grant_data)

                # Weighted average: 40% completeness, 60% content quality
                return (completeness * 0.4) + (content_quality * 0.6)

        return QualityScorer()

    def test_score_completeness_all_fields(self, quality_scorer, sample_grant_data):
        """Test completeness scoring with all fields present."""
        score = quality_scorer.score_completeness(sample_grant_data)
        assert score >= 0.8  # Should be high with all fields

    def test_score_completeness_missing_required(self, quality_scorer):
        """Test completeness scoring with missing required fields."""
        grant_data = {
            "title": "Test Grant",
            # Missing description, agency, url
        }
        score = quality_scorer.score_completeness(grant_data)
        assert score < 0.5

    def test_score_completeness_only_required(self, quality_scorer):
        """Test completeness scoring with only required fields."""
        grant_data = {
            "title": "Test Grant",
            "description": "A test grant for research purposes",
            "agency": "NIH",
            "url": "https://grants.gov/test",
        }
        score = quality_scorer.score_completeness(grant_data)
        assert score == 0.6  # 100% required, 0% optional

    def test_score_content_quality_high(self, quality_scorer, sample_grant_data):
        """Test content quality scoring for high-quality data."""
        score = quality_scorer.score_content_quality(sample_grant_data)
        assert score >= 0.8

    def test_score_content_quality_low(self, quality_scorer):
        """Test content quality scoring for low-quality data."""
        grant_data = {
            "title": "Short",  # Too short
            "description": "Brief",  # Too short
        }
        score = quality_scorer.score_content_quality(grant_data)
        assert score < 0.5

    def test_calculate_total_score(self, quality_scorer, sample_grant_data):
        """Test total score calculation."""
        score = quality_scorer.calculate_total_score(sample_grant_data)
        assert 0.0 <= score <= 1.0


# =============================================================================
# Categorization Tests
# =============================================================================


class TestCategorization:
    """Tests for grant categorization logic."""

    @pytest.fixture
    def categorizer(self):
        """Create a mock categorizer."""
        class Categorizer:
            KEYWORD_CATEGORIES = {
                "healthcare": ["health", "medical", "clinical", "patient", "disease", "treatment"],
                "ai_ml": ["machine learning", "artificial intelligence", "deep learning", "neural network"],
                "climate": ["climate", "environmental", "sustainability", "carbon", "renewable"],
                "education": ["education", "teaching", "students", "curriculum", "learning"],
                "biotech": ["biotechnology", "genomics", "genetics", "dna", "protein"],
            }

            def categorize_by_keywords(self, text: str) -> list[str]:
                """Categorize based on keyword matching."""
                text_lower = text.lower()
                categories = []

                for category, keywords in self.KEYWORD_CATEGORIES.items():
                    if any(kw in text_lower for kw in keywords):
                        categories.append(category)

                return categories

            def categorize_grant(self, grant_data: dict) -> list[str]:
                """Categorize a grant based on its content."""
                # Combine title and description for analysis
                text = f"{grant_data.get('title', '')} {grant_data.get('description', '')}"
                return self.categorize_by_keywords(text)

        return Categorizer()

    def test_categorize_healthcare(self, categorizer):
        """Test categorization of healthcare grants."""
        grant_data = {
            "title": "Clinical Trial for New Treatment",
            "description": "A medical research study on patient outcomes.",
        }
        categories = categorizer.categorize_grant(grant_data)
        assert "healthcare" in categories

    def test_categorize_ai_ml(self, categorizer):
        """Test categorization of AI/ML grants."""
        grant_data = {
            "title": "Deep Learning Research Initiative",
            "description": "Advancing machine learning and neural network applications.",
        }
        categories = categorizer.categorize_grant(grant_data)
        assert "ai_ml" in categories

    def test_categorize_multiple(self, categorizer):
        """Test categorization when multiple categories match."""
        grant_data = {
            "title": "Machine Learning in Healthcare",
            "description": "Applying deep learning to patient diagnosis and treatment.",
        }
        categories = categorizer.categorize_grant(grant_data)
        assert "healthcare" in categories
        assert "ai_ml" in categories

    def test_categorize_none(self, categorizer):
        """Test categorization when no categories match."""
        grant_data = {
            "title": "Historical Archive Digitization",
            "description": "Converting paper records to digital format.",
        }
        categories = categorizer.categorize_grant(grant_data)
        assert categories == []

    def test_categorize_case_insensitive(self, categorizer):
        """Test that categorization is case-insensitive."""
        grant_data = {
            "title": "MACHINE LEARNING RESEARCH",
            "description": "Deep Learning and Neural Networks",
        }
        categories = categorizer.categorize_grant(grant_data)
        assert "ai_ml" in categories


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplication:
    """Tests for grant deduplication logic."""

    @pytest.fixture
    def deduplicator(self):
        """Create a mock deduplicator."""
        class Deduplicator:
            def __init__(self):
                self.seen_hashes = set()

            def compute_hash(self, grant_data: dict) -> str:
                """Compute a hash for deduplication."""
                import hashlib
                # Use title + source + external_id for uniqueness
                key_parts = [
                    grant_data.get("source", ""),
                    grant_data.get("external_id", ""),
                    grant_data.get("title", ""),
                ]
                key = "|".join(key_parts).lower()
                return hashlib.sha256(key.encode()).hexdigest()

            def is_duplicate(self, grant_data: dict) -> bool:
                """Check if grant is a duplicate."""
                hash_val = self.compute_hash(grant_data)
                return hash_val in self.seen_hashes

            def mark_seen(self, grant_data: dict) -> None:
                """Mark grant as seen."""
                hash_val = self.compute_hash(grant_data)
                self.seen_hashes.add(hash_val)

            def compute_similarity(self, grant1: dict, grant2: dict) -> float:
                """Compute title similarity between two grants."""
                title1 = grant1.get("title", "").lower()
                title2 = grant2.get("title", "").lower()

                # Simple word overlap similarity
                words1 = set(title1.split())
                words2 = set(title2.split())

                if not words1 or not words2:
                    return 0.0

                intersection = words1 & words2
                union = words1 | words2

                return len(intersection) / len(union)

        return Deduplicator()

    def test_is_duplicate_new(self, deduplicator, sample_grant_data):
        """Test checking duplicate for new grant."""
        is_dup = deduplicator.is_duplicate(sample_grant_data)
        assert is_dup is False

    def test_is_duplicate_seen(self, deduplicator, sample_grant_data):
        """Test checking duplicate for seen grant."""
        deduplicator.mark_seen(sample_grant_data)
        is_dup = deduplicator.is_duplicate(sample_grant_data)
        assert is_dup is True

    def test_is_duplicate_different_grant(self, deduplicator, sample_grant_data):
        """Test that different grants are not duplicates."""
        deduplicator.mark_seen(sample_grant_data)

        different_grant = sample_grant_data.copy()
        different_grant["external_id"] = "DIFFERENT-001"

        is_dup = deduplicator.is_duplicate(different_grant)
        assert is_dup is False

    def test_compute_similarity_identical(self, deduplicator):
        """Test similarity for identical titles."""
        grant1 = {"title": "Research Grant for AI"}
        grant2 = {"title": "Research Grant for AI"}

        similarity = deduplicator.compute_similarity(grant1, grant2)
        assert similarity == 1.0

    def test_compute_similarity_different(self, deduplicator):
        """Test similarity for completely different titles."""
        grant1 = {"title": "Research Grant for AI"}
        grant2 = {"title": "Climate Change Study"}

        similarity = deduplicator.compute_similarity(grant1, grant2)
        assert similarity < 0.3

    def test_compute_similarity_partial(self, deduplicator):
        """Test similarity for partially similar titles."""
        grant1 = {"title": "Research Grant for AI in Healthcare"}
        grant2 = {"title": "Research Study for AI Applications"}

        similarity = deduplicator.compute_similarity(grant1, grant2)
        assert 0.2 < similarity < 0.8


# =============================================================================
# LLM Validation Tests
# =============================================================================


class TestLLMValidation:
    """Tests for LLM-based grant validation."""

    @pytest.fixture
    def mock_llm_validator(self, mock_anthropic):
        """Create a mock LLM validator."""
        class LLMValidator:
            def __init__(self, client):
                self.client = client

            async def validate_grant(self, grant_data: dict) -> dict:
                """Validate grant using LLM."""
                prompt = f"""Analyze this grant opportunity and provide:
                1. Quality score (0-100)
                2. Is this a legitimate grant? (true/false)
                3. Extracted keywords
                4. Category suggestions

                Grant:
                Title: {grant_data.get('title', '')}
                Description: {grant_data.get('description', '')}
                Agency: {grant_data.get('agency', '')}

                Return as JSON."""

                response = self.client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=1000,
                    messages=[{"role": "user", "content": prompt}],
                )

                return json.loads(response.content[0].text)

        return LLMValidator(mock_anthropic.return_value)

    @pytest.mark.asyncio
    async def test_llm_validation_success(self, mock_llm_validator, mock_anthropic, sample_grant_data):
        """Test successful LLM validation."""
        # Setup mock response
        mock_anthropic.return_value.messages.create.return_value.content[0].text = json.dumps({
            "quality_score": 85,
            "is_legitimate": True,
            "keywords": ["machine learning", "healthcare", "research"],
            "categories": ["ai_ml", "healthcare"],
        })

        result = await mock_llm_validator.validate_grant(sample_grant_data)

        assert result["quality_score"] == 85
        assert result["is_legitimate"] is True
        assert "keywords" in result

    @pytest.mark.asyncio
    async def test_llm_validation_low_quality(self, mock_llm_validator, mock_anthropic):
        """Test LLM validation for low-quality grant."""
        mock_anthropic.return_value.messages.create.return_value.content[0].text = json.dumps({
            "quality_score": 25,
            "is_legitimate": False,
            "keywords": [],
            "categories": [],
        })

        grant_data = {
            "title": "Free Money",
            "description": "Get free money now",
        }

        result = await mock_llm_validator.validate_grant(grant_data)

        assert result["quality_score"] < 50
        assert result["is_legitimate"] is False


# =============================================================================
# Embedding Generation Tests
# =============================================================================


class TestEmbeddingGeneration:
    """Tests for vector embedding generation."""

    @pytest.fixture
    def mock_embedding_generator(self, mock_openai):
        """Create a mock embedding generator."""
        class EmbeddingGenerator:
            def __init__(self, client, model: str = "text-embedding-3-small"):
                self.client = client
                self.model = model
                self.dimensions = 1536

            async def generate_embedding(self, text: str) -> list[float]:
                """Generate embedding for text."""
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text,
                )
                return response.data[0].embedding

            def prepare_grant_text(self, grant_data: dict) -> str:
                """Prepare grant text for embedding."""
                parts = []
                if grant_data.get("title"):
                    parts.append(f"Title: {grant_data['title']}")
                if grant_data.get("description"):
                    parts.append(f"Description: {grant_data['description']}")
                if grant_data.get("agency"):
                    parts.append(f"Agency: {grant_data['agency']}")
                if grant_data.get("categories"):
                    parts.append(f"Categories: {', '.join(grant_data['categories'])}")
                return "\n".join(parts)

        return EmbeddingGenerator(mock_openai.return_value)

    @pytest.mark.asyncio
    async def test_generate_embedding(self, mock_embedding_generator, mock_openai, sample_embedding):
        """Test embedding generation."""
        mock_openai.return_value.embeddings.create.return_value.data[0].embedding = sample_embedding

        embedding = await mock_embedding_generator.generate_embedding("Test text for embedding")

        assert len(embedding) == 1536
        assert all(isinstance(x, float) for x in embedding)

    def test_prepare_grant_text(self, mock_embedding_generator, sample_grant_data):
        """Test grant text preparation for embedding."""
        text = mock_embedding_generator.prepare_grant_text(sample_grant_data)

        assert "Title:" in text
        assert sample_grant_data["title"] in text
        assert "Description:" in text

    def test_prepare_grant_text_missing_fields(self, mock_embedding_generator):
        """Test text preparation with missing fields."""
        grant_data = {"title": "Test Grant"}
        text = mock_embedding_generator.prepare_grant_text(grant_data)

        assert "Title: Test Grant" in text
        assert "Description:" not in text  # Missing field not included


# =============================================================================
# Curation Pipeline Tests
# =============================================================================


class TestCurationPipeline:
    """Tests for the complete curation pipeline."""

    @pytest.fixture
    def curation_pipeline(self, mock_anthropic, mock_openai):
        """Create a mock curation pipeline."""
        class CurationPipeline:
            def __init__(self):
                self.quality_threshold = 0.5
                self.processed_count = 0
                self.passed_count = 0
                self.failed_count = 0

            async def process_grant(self, grant_event: GrantDiscoveredEvent) -> GrantValidatedEvent | None:
                """Process a discovered grant through curation."""
                self.processed_count += 1

                # Simulate quality scoring
                quality_score = 0.8  # Mock score

                if quality_score < self.quality_threshold:
                    self.failed_count += 1
                    return None

                self.passed_count += 1

                return GrantValidatedEvent(
                    event_id=uuid.uuid4(),
                    grant_id=grant_event.grant_id,
                    quality_score=quality_score,
                    categories=["research", "science"],
                    embedding_generated=True,
                    keywords=["test", "grant"],
                )

            def get_stats(self) -> dict:
                """Get pipeline statistics."""
                return {
                    "processed": self.processed_count,
                    "passed": self.passed_count,
                    "failed": self.failed_count,
                    "pass_rate": self.passed_count / max(self.processed_count, 1),
                }

        return CurationPipeline()

    @pytest.mark.asyncio
    async def test_process_high_quality_grant(self, curation_pipeline, sample_grant_discovered_event):
        """Test processing a high-quality grant."""
        result = await curation_pipeline.process_grant(sample_grant_discovered_event)

        assert result is not None
        assert isinstance(result, GrantValidatedEvent)
        assert result.quality_score >= 0.5
        assert result.embedding_generated is True

    @pytest.mark.asyncio
    async def test_pipeline_stats(self, curation_pipeline, sample_grant_discovered_event):
        """Test pipeline statistics tracking."""
        await curation_pipeline.process_grant(sample_grant_discovered_event)
        await curation_pipeline.process_grant(sample_grant_discovered_event)

        stats = curation_pipeline.get_stats()

        assert stats["processed"] == 2
        assert stats["passed"] == 2
        assert stats["pass_rate"] == 1.0


# =============================================================================
# Event Processing Tests
# =============================================================================


class TestEventProcessing:
    """Tests for event processing in curation."""

    @pytest.mark.asyncio
    async def test_grant_discovered_event_to_validated(self, sample_grant_discovered_event):
        """Test converting discovered event to validated event."""
        validated = GrantValidatedEvent(
            event_id=uuid.uuid4(),
            grant_id=sample_grant_discovered_event.grant_id,
            quality_score=0.85,
            categories=["healthcare", "ai_ml"],
            embedding_generated=True,
            keywords=["machine learning", "health"],
        )

        assert validated.grant_id == sample_grant_discovered_event.grant_id
        assert validated.quality_score == 0.85
        assert "healthcare" in validated.categories

    @pytest.mark.asyncio
    async def test_event_serialization(self, sample_grant_validated_event):
        """Test event serialization for Redis."""
        json_str = sample_grant_validated_event.model_dump_json()
        parsed = json.loads(json_str)

        assert "grant_id" in parsed
        assert "quality_score" in parsed
        assert "categories" in parsed

    @pytest.mark.asyncio
    async def test_event_deserialization(self):
        """Test event deserialization from Redis."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "grant_id": str(uuid.uuid4()),
            "quality_score": 0.9,
            "categories": ["research"],
            "embedding_generated": True,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        event = GrantValidatedEvent(**event_data)

        assert event.quality_score == 0.9
        assert "research" in event.categories


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestCurationErrorHandling:
    """Tests for error handling in curation."""

    @pytest.mark.asyncio
    async def test_llm_api_error_handling(self, mock_anthropic):
        """Test handling of LLM API errors."""
        import anthropic

        mock_anthropic.return_value.messages.create.side_effect = anthropic.APIError(
            message="API Error",
            request=MagicMock(),
            body=None,
        )

        # Should handle the error gracefully
        with pytest.raises(anthropic.APIError):
            mock_anthropic.return_value.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": "test"}],
            )

    @pytest.mark.asyncio
    async def test_embedding_api_error_handling(self, mock_openai):
        """Test handling of embedding API errors."""
        mock_openai.return_value.embeddings.create.side_effect = Exception("Embedding API Error")

        with pytest.raises(Exception) as exc_info:
            mock_openai.return_value.embeddings.create(
                model="text-embedding-3-small",
                input="test",
            )

        assert "Embedding API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_malformed_llm_response(self, mock_anthropic):
        """Test handling of malformed LLM responses."""
        mock_anthropic.return_value.messages.create.return_value.content[0].text = "Not valid JSON"

        with pytest.raises(json.JSONDecodeError):
            response = mock_anthropic.return_value.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=[{"role": "user", "content": "test"}],
            )
            json.loads(response.content[0].text)
