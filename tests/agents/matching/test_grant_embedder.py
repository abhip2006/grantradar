"""
Tests for Grant Embedder.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

from agents.matching.grant_embedder import GrantEmbedder


class TestGrantToText:
    """Tests for grant to text conversion."""

    def test_full_grant_to_text(self, sample_grant_data):
        """Test converting full grant to text."""
        embedder = GrantEmbedder(MagicMock())

        text = embedder._grant_to_text(sample_grant_data)

        assert "Machine Learning for Climate Science" in text
        assert "National Science Foundation" in text
        assert "climate modeling" in text
        assert "$750,000" in text or "750000" in text

    def test_minimal_grant_to_text(self):
        """Test converting minimal grant to text."""
        embedder = GrantEmbedder(MagicMock())

        grant = {"title": "Test Grant"}
        text = embedder._grant_to_text(grant)

        assert "Test Grant" in text

    def test_truncates_long_description(self):
        """Test that long descriptions are truncated."""
        embedder = GrantEmbedder(MagicMock())

        grant = {
            "title": "Test",
            "description": "x" * 5000,  # Very long description
        }
        text = embedder._grant_to_text(grant)

        assert len(text) < 5000
        assert "..." in text

    def test_handles_list_categories(self):
        """Test handling of list categories."""
        embedder = GrantEmbedder(MagicMock())

        grant = {
            "title": "Test",
            "categories": ["AI", "ML", "Climate"],
        }
        text = embedder._grant_to_text(grant)

        assert "AI" in text
        assert "ML" in text
        assert "Climate" in text

    def test_handles_dict_eligibility(self):
        """Test handling of dict eligibility."""
        embedder = GrantEmbedder(MagicMock())

        grant = {
            "title": "Test",
            "eligibility": {
                "applicant_types": ["Universities", "Nonprofits"],
            },
        }
        text = embedder._grant_to_text(grant)

        assert "Universities" in text
        assert "Nonprofits" in text


class TestTextHash:
    """Tests for text hash computation."""

    def test_hash_is_deterministic(self):
        """Test that same text produces same hash."""
        embedder = GrantEmbedder(MagicMock())

        text = "Test grant description"
        hash1 = embedder._compute_text_hash(text)
        hash2 = embedder._compute_text_hash(text)

        assert hash1 == hash2

    def test_different_text_different_hash(self):
        """Test that different text produces different hash."""
        embedder = GrantEmbedder(MagicMock())

        hash1 = embedder._compute_text_hash("Text one")
        hash2 = embedder._compute_text_hash("Text two")

        assert hash1 != hash2

    def test_hash_is_64_chars(self):
        """Test that hash is SHA-256 hex (64 chars)."""
        embedder = GrantEmbedder(MagicMock())

        hash_value = embedder._compute_text_hash("Test")

        assert len(hash_value) == 64


class TestBuildEmbedding:
    """Tests for embedding generation."""

    @patch("agents.matching.grant_embedder.openai")
    def test_build_embedding_success(self, mock_openai, mock_openai_embedding):
        """Test successful embedding generation."""
        # Setup mocks
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_engine.begin = MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=mock_session), __exit__=MagicMock()))

        # Mock grant fetch
        grant_id = uuid4()
        mock_result = MagicMock()
        mock_result.has_embedding = False
        mock_result.title = "Test Grant"
        mock_result.description = "Description"
        mock_result.agency = "NSF"
        mock_result.amount_min = 100000
        mock_result.amount_max = 200000
        mock_result.categories = ["ai"]
        mock_result.eligibility = None

        mock_session.execute.return_value.fetchone.return_value = mock_result

        # Mock OpenAI
        mock_openai.OpenAI.return_value.embeddings.create.return_value = mock_openai_embedding

        # Create embedder with Session mock
        embedder = GrantEmbedder(mock_engine)

        with patch("agents.matching.grant_embedder.Session") as mock_session_class:
            mock_session_context = MagicMock()
            mock_session_context.__enter__ = MagicMock(return_value=mock_session)
            mock_session_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_session_context

            result = embedder.build_embedding(grant_id, force=True)

        # Verify
        assert result is not None
        assert result["grant_id"] == str(grant_id)
        assert result["dimensions"] == 1536

    def test_build_embedding_grant_not_found(self):
        """Test handling of missing grant."""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchone.return_value = None

        embedder = GrantEmbedder(mock_engine)

        with patch("agents.matching.grant_embedder.Session") as mock_session_class:
            mock_session_context = MagicMock()
            mock_session_context.__enter__ = MagicMock(return_value=mock_session)
            mock_session_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_session_context

            result = embedder.build_embedding(uuid4())

        assert result is None

    def test_build_embedding_skips_existing(self):
        """Test that existing embeddings are skipped without force."""
        mock_engine = MagicMock()
        mock_session = MagicMock()

        mock_result = MagicMock()
        mock_result.has_embedding = True
        mock_session.execute.return_value.fetchone.return_value = mock_result

        embedder = GrantEmbedder(mock_engine)

        with patch("agents.matching.grant_embedder.Session") as mock_session_class:
            mock_session_context = MagicMock()
            mock_session_context.__enter__ = MagicMock(return_value=mock_session)
            mock_session_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_session_context

            result = embedder.build_embedding(uuid4(), force=False)

        assert result is None


class TestBatchEmbedding:
    """Tests for batch embedding generation."""

    def test_batch_stats_structure(self):
        """Test batch operation returns correct stats structure."""
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_session.execute.return_value.fetchall.return_value = []

        embedder = GrantEmbedder(mock_engine)

        with patch("agents.matching.grant_embedder.Session") as mock_session_class:
            mock_session_context = MagicMock()
            mock_session_context.__enter__ = MagicMock(return_value=mock_session)
            mock_session_context.__exit__ = MagicMock(return_value=False)
            mock_session_class.return_value = mock_session_context

            stats = embedder.build_embeddings_batch([uuid4(), uuid4()])

        assert "requested" in stats
        assert "processed" in stats
        assert "generated" in stats
        assert "skipped" in stats
        assert "errors" in stats
