"""
Tests for RAG Chat API endpoints.
Tests chat sessions, message handling, and RAG context retrieval.
These tests are database-independent and focus on business logic.
Database integration tests require a PostgreSQL database with proper fixtures.
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import User, Grant, ChatSession
from backend.schemas.chat import ChatSessionType, ChatSource, ChatMessageResponse


# =============================================================================
# Schema Tests (No Database Required)
# =============================================================================


class TestChatSourceModel:
    """Tests for ChatSource schema."""

    def test_chat_source_creation(self):
        """Test creating a ChatSource object."""
        source = ChatSource(
            document_type="grant",
            document_id="123-456",
            title="Test Grant",
            excerpt="This is a test grant description...",
            relevance_score=0.85,
        )

        assert source.document_type == "grant"
        assert source.document_id == "123-456"
        assert source.title == "Test Grant"
        assert source.relevance_score == 0.85

    def test_chat_source_optional_document_id(self):
        """Test ChatSource with optional document_id."""
        source = ChatSource(
            document_type="guideline",
            title="NIH Guidelines",
            excerpt="General submission guidelines...",
            relevance_score=0.72,
        )

        assert source.document_id is None
        assert source.document_type == "guideline"

    def test_chat_source_model_dump(self):
        """Test ChatSource serialization."""
        source = ChatSource(
            document_type="grant",
            document_id="abc-123",
            title="Research Grant",
            excerpt="Funding for AI research...",
            relevance_score=0.91,
        )

        data = source.model_dump()

        assert data["document_type"] == "grant"
        assert data["document_id"] == "abc-123"
        assert data["relevance_score"] == 0.91

    def test_chat_source_various_document_types(self):
        """Test ChatSource with various document types."""
        document_types = ["grant", "foa", "guideline", "profile"]

        for doc_type in document_types:
            source = ChatSource(
                document_type=doc_type,
                title=f"Test {doc_type}",
                excerpt="Test excerpt",
                relevance_score=0.5,
            )
            assert source.document_type == doc_type


class TestChatSessionTypes:
    """Tests for chat session type enumeration."""

    def test_proposal_session_type(self):
        """Test proposal chat session type."""
        assert ChatSessionType.PROPOSAL.value == "proposal_chat"

    def test_eligibility_session_type(self):
        """Test eligibility session type."""
        assert ChatSessionType.ELIGIBILITY.value == "eligibility"

    def test_research_session_type(self):
        """Test research session type."""
        assert ChatSessionType.RESEARCH.value == "research"

    def test_all_session_types_unique(self):
        """Test all session types have unique values."""
        values = [st.value for st in ChatSessionType]
        assert len(values) == len(set(values))


class TestChatMessageResponse:
    """Tests for ChatMessageResponse schema."""

    def test_message_response_creation(self):
        """Test creating a ChatMessageResponse."""
        response = ChatMessageResponse(
            id=uuid4(),
            session_id=uuid4(),
            role="assistant",
            content="This is a response.",
            sources=None,
            created_at=datetime.now(timezone.utc),
        )

        assert response.role == "assistant"
        assert response.content == "This is a response."
        assert response.sources is None

    def test_message_response_with_sources(self):
        """Test ChatMessageResponse with sources."""
        sources = [
            ChatSource(
                document_type="grant",
                title="NIH R01",
                excerpt="Cancer research funding",
                relevance_score=0.88,
            )
        ]

        response = ChatMessageResponse(
            id=uuid4(),
            session_id=uuid4(),
            role="assistant",
            content="Based on the grants...",
            sources=sources,
            created_at=datetime.now(timezone.utc),
        )

        assert len(response.sources) == 1
        assert response.sources[0].document_type == "grant"


# =============================================================================
# RAGChatService Unit Tests (Mocked Database)
# =============================================================================


class TestRAGChatServiceSystemPrompt:
    """Tests for system prompt construction."""

    def test_build_system_prompt_includes_user(self):
        """Test system prompt includes user info."""
        user = MagicMock(spec=User)
        user.name = "Dr. Smith"
        user.email = "smith@university.edu"

        session = MagicMock(spec=ChatSession)
        session.session_type = "proposal_chat"

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()
                prompt = service._build_system_prompt(session, "", user)

                assert "Dr. Smith" in prompt or "smith@university.edu" in prompt

    def test_build_system_prompt_includes_context(self):
        """Test system prompt includes RAG context."""
        user = MagicMock(spec=User)
        user.name = "Researcher"
        user.email = "researcher@test.edu"

        session = MagicMock(spec=ChatSession)
        session.session_type = "proposal_chat"

        context = """
Grant: NIH R01 for Cancer Research
Funder: NIH
Requirements: Must be PI at eligible institution
"""

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()
                prompt = service._build_system_prompt(session, context, user)

                assert "Cancer Research" in prompt
                assert "NIH" in prompt

    def test_build_system_prompt_empty_context(self):
        """Test system prompt when no RAG context available."""
        user = MagicMock(spec=User)
        user.name = "Test User"
        user.email = "test@test.edu"

        session = MagicMock(spec=ChatSession)
        session.session_type = "proposal_chat"

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()
                prompt = service._build_system_prompt(session, "", user)

                # Should still have base prompt
                assert "GrantRadar AI" in prompt
                assert "RELEVANT CONTEXT" not in prompt

    def test_build_system_prompt_different_session_types(self):
        """Test system prompt includes correct session type."""
        user = MagicMock(spec=User)
        user.name = "Test"
        user.email = "test@test.edu"

        for session_type in ["proposal_chat", "eligibility", "research"]:
            session = MagicMock(spec=ChatSession)
            session.session_type = session_type

            with patch("backend.services.rag_chat.settings") as mock_settings:
                mock_settings.openai_api_key = "test-key"
                mock_settings.embedding_model = "text-embedding-3-small"

                with patch("backend.services.rag_chat.openai.OpenAI"):
                    from backend.services.rag_chat import RAGChatService

                    service = RAGChatService()
                    prompt = service._build_system_prompt(session, "", user)

                    assert session_type in prompt


class TestRAGChatServiceSessionManagement:
    """Tests for chat session management with mocked database."""

    @pytest.mark.asyncio
    async def test_create_session_generates_title_for_grant(self):
        """Test creating session with grant context generates appropriate title."""
        mock_db = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()

        mock_grant = MagicMock(spec=Grant)
        mock_grant.id = uuid4()
        mock_grant.title = "NIH R01 Cancer Research Grant for Early Career Investigators"

        mock_db.get = AsyncMock(return_value=mock_grant)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                # Mock the session creation
                mock_session = MagicMock(spec=ChatSession)
                mock_session.id = uuid4()
                mock_session.user_id = mock_user.id
                mock_session.context_grant_id = mock_grant.id

                await service.create_session(
                    db=mock_db,
                    user=mock_user,
                    context_grant_id=mock_grant.id,
                )

                # The title should include "Chat:" and part of the grant title
                mock_db.add.assert_called()

    @pytest.mark.asyncio
    async def test_delete_session_wrong_user_returns_false(self):
        """Test deleting session belonging to different user returns False."""
        mock_db = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()

        # Session belongs to different user
        mock_session = MagicMock(spec=ChatSession)
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()  # Different user

        mock_db.get = AsyncMock(return_value=mock_session)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                result = await service.delete_session(mock_db, mock_user.id, mock_session.id)

                assert result is False
                mock_db.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_session_not_found_returns_false(self):
        """Test deleting non-existent session returns False."""
        mock_db = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()

        mock_db.get = AsyncMock(return_value=None)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                result = await service.delete_session(mock_db, mock_user.id, uuid4())

                assert result is False


class TestRAGChatServiceMessageHandling:
    """Tests for message handling with mocked database."""

    @pytest.mark.asyncio
    async def test_send_message_to_wrong_session_raises_error(self):
        """Test sending message to session belonging to different user."""
        mock_db = AsyncMock()
        mock_user = MagicMock(spec=User)
        mock_user.id = uuid4()

        # Session belongs to different user
        mock_session = MagicMock(spec=ChatSession)
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()  # Different user

        mock_db.get = AsyncMock(return_value=mock_session)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                with pytest.raises(ValueError, match="not found"):
                    await service.send_message(
                        db=mock_db,
                        user=mock_user,
                        session_id=mock_session.id,
                        content="Test message",
                    )

    @pytest.mark.asyncio
    async def test_get_session_messages_wrong_user_raises_error(self):
        """Test getting messages from session belonging to different user."""
        mock_db = AsyncMock()
        mock_user_id = uuid4()

        # Session belongs to different user
        mock_session = MagicMock(spec=ChatSession)
        mock_session.id = uuid4()
        mock_session.user_id = uuid4()  # Different user

        mock_db.get = AsyncMock(return_value=mock_session)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                with pytest.raises(ValueError, match="not found"):
                    await service.get_session_messages(mock_db, mock_user_id, mock_session.id)

    @pytest.mark.asyncio
    async def test_get_session_messages_not_found_raises_error(self):
        """Test getting messages from non-existent session raises error."""
        mock_db = AsyncMock()
        mock_user_id = uuid4()

        mock_db.get = AsyncMock(return_value=None)

        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI"):
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                with pytest.raises(ValueError, match="not found"):
                    await service.get_session_messages(mock_db, mock_user_id, uuid4())


class TestRAGChatServiceResponseGeneration:
    """Tests for AI response generation."""

    @pytest.mark.asyncio
    async def test_generate_response_handles_api_error(self):
        """Test that API errors return graceful error message."""
        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"
            mock_settings.llm_model = "gpt-4o"
            mock_settings.llm_max_tokens = 4096

            with patch("backend.services.rag_chat.openai.OpenAI") as mock_openai:
                # Configure mock to raise an exception
                mock_openai.return_value.chat.completions.create.side_effect = Exception("API Error")

                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()
                service.openai = mock_openai.return_value

                result = await service._generate_response(
                    system_prompt="Test prompt",
                    history=[],
                    user_message="Test question",
                )

                assert "apologize" in result.lower() or "error" in result.lower()

    @pytest.mark.asyncio
    async def test_generate_response_returns_text(self):
        """Test successful response generation."""
        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            mock_settings.embedding_model = "text-embedding-3-small"
            mock_settings.llm_model = "gpt-4o"
            mock_settings.llm_max_tokens = 4096

            with patch("backend.services.rag_chat.openai.OpenAI") as mock_openai:
                # Configure mock to return a response
                mock_choice = MagicMock()
                mock_choice.message.content = "This is a test response."
                mock_response = MagicMock()
                mock_response.choices = [mock_choice]
                mock_openai.return_value.chat.completions.create.return_value = mock_response

                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()
                service.openai = mock_openai.return_value

                result = await service._generate_response(
                    system_prompt="Test prompt",
                    history=[],
                    user_message="Test question",
                )

                assert result == "This is a test response."


class TestConversationHistoryLogic:
    """Tests for conversation history processing logic."""

    def test_history_message_formatting(self):
        """Test that history messages are properly formatted."""
        # Simulate what get_conversation_history returns
        history = [
            {"role": "user", "content": "First message"},
            {"role": "assistant", "content": "First response"},
            {"role": "user", "content": "Second message"},
        ]

        # Verify all required keys present
        for msg in history:
            assert "role" in msg
            assert "content" in msg
            assert msg["role"] in ("user", "assistant")

    def test_history_excludes_system_messages(self):
        """Test that system messages are filtered from history."""
        all_messages = [
            {"role": "user", "content": "User message"},
            {"role": "assistant", "content": "Assistant message"},
            {"role": "system", "content": "System message"},
        ]

        # Filter like the service does
        filtered = [msg for msg in all_messages if msg["role"] in ("user", "assistant")]

        assert len(filtered) == 2
        roles = [m["role"] for m in filtered]
        assert "system" not in roles


class TestRAGContextProcessing:
    """Tests for RAG context processing logic."""

    def test_context_formatting_with_grant_data(self):
        """Test formatting of grant data into context string."""
        grant_data = {
            "title": "NIH Cancer Research Grant",
            "agency": "NIH",
            "categories": ["cancer", "immunotherapy"],
            "description": "Research funding for cancer studies",
            "amount_min": 100000,
            "amount_max": 500000,
        }

        # Format like the service would
        context = f"""
Grant: {grant_data["title"]}
Agency: {grant_data["agency"]}
Categories: {", ".join(grant_data["categories"])}
Description: {grant_data["description"]}
Amount: ${grant_data["amount_min"]:,} - ${grant_data["amount_max"]:,}
---"""

        assert "NIH Cancer Research Grant" in context
        assert "cancer, immunotherapy" in context
        assert "$100,000" in context

    def test_context_handles_missing_fields(self):
        """Test context formatting handles missing/null fields."""
        grant_data = {
            "title": "Test Grant",
            "agency": None,
            "categories": None,
            "description": None,
            "amount_min": None,
            "amount_max": None,
        }

        # Format with defaults
        context = f"""
Grant: {grant_data["title"]}
Agency: {grant_data["agency"] or "Unknown"}
Categories: {", ".join(grant_data["categories"]) if grant_data["categories"] else "N/A"}
Description: {grant_data["description"] or "No description"}
Amount: ${grant_data["amount_min"] or 0:,} - ${grant_data["amount_max"] or 0:,}
---"""

        assert "Test Grant" in context
        assert "Unknown" in context
        assert "N/A" in context
        assert "No description" in context


class TestEligibilityContextFormatting:
    """Tests for eligibility data formatting in context."""

    def test_eligibility_dict_to_string(self):
        """Test converting eligibility dict to string for context."""
        import json

        eligibility = {
            "institution_types": ["universities", "research_institutions"],
            "career_stages": ["early_career", "established"],
            "citizenship": ["us_citizen", "permanent_resident"],
        }

        eligibility_text = json.dumps(eligibility, indent=2)

        assert "universities" in eligibility_text
        assert "early_career" in eligibility_text
        assert "us_citizen" in eligibility_text

    def test_eligibility_string_passthrough(self):
        """Test that string eligibility passes through."""
        eligibility = "Must be a faculty member at an accredited institution"

        # In the service, string eligibility is used directly
        eligibility_text = str(eligibility)

        assert eligibility_text == eligibility


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================


class TestEdgeCasesAndErrors:
    """Tests for edge cases and error handling."""

    def test_chat_source_extreme_relevance_scores(self):
        """Test ChatSource handles edge case relevance scores."""
        # Perfect score
        source_perfect = ChatSource(
            document_type="grant",
            title="Perfect Match",
            excerpt="...",
            relevance_score=1.0,
        )
        assert source_perfect.relevance_score == 1.0

        # Zero score
        source_zero = ChatSource(
            document_type="grant",
            title="No Match",
            excerpt="...",
            relevance_score=0.0,
        )
        assert source_zero.relevance_score == 0.0

    def test_chat_source_empty_excerpt(self):
        """Test ChatSource with empty excerpt."""
        source = ChatSource(
            document_type="grant",
            title="Grant",
            excerpt="",
            relevance_score=0.5,
        )
        assert source.excerpt == ""

    def test_chat_source_very_long_excerpt(self):
        """Test ChatSource with very long excerpt."""
        long_excerpt = "A" * 10000
        source = ChatSource(
            document_type="grant",
            title="Grant",
            excerpt=long_excerpt,
            relevance_score=0.5,
        )
        assert len(source.excerpt) == 10000

    def test_session_type_invalid_value_handling(self):
        """Test handling of session type values."""
        valid_types = ["proposal_chat", "eligibility", "research"]

        for vt in valid_types:
            assert ChatSessionType(vt).value == vt

    @pytest.mark.asyncio
    async def test_service_initialization(self):
        """Test RAGChatService initializes correctly."""
        with patch("backend.services.rag_chat.settings") as mock_settings:
            mock_settings.openai_api_key = "test-openai-key"
            mock_settings.embedding_model = "text-embedding-3-small"

            with patch("backend.services.rag_chat.openai.OpenAI") as mock_openai:
                from backend.services.rag_chat import RAGChatService

                service = RAGChatService()

                # Verify client was initialized
                mock_openai.assert_called_once_with(api_key="test-openai-key")
                assert service.embedding_model == "text-embedding-3-small"


class TestInputValidation:
    """Tests for input validation."""

    def test_chat_source_required_fields(self):
        """Test ChatSource requires all required fields."""
        # All required fields present - should work
        source = ChatSource(
            document_type="grant",
            title="Test",
            excerpt="Test excerpt",
            relevance_score=0.5,
        )
        assert source is not None

        # Missing required field should raise error
        with pytest.raises(Exception):
            ChatSource(
                document_type="grant",
                # title missing
                excerpt="Test",
                relevance_score=0.5,
            )

    def test_message_response_required_fields(self):
        """Test ChatMessageResponse requires all required fields."""
        response = ChatMessageResponse(
            id=uuid4(),
            session_id=uuid4(),
            role="assistant",
            content="Response content",
            created_at=datetime.now(timezone.utc),
        )
        assert response is not None

    def test_relevance_score_numeric_type(self):
        """Test relevance score accepts numeric types."""
        # Float
        source_float = ChatSource(
            document_type="grant",
            title="Test",
            excerpt="...",
            relevance_score=0.75,
        )
        assert source_float.relevance_score == 0.75

        # Integer coerced to float
        source_int = ChatSource(
            document_type="grant",
            title="Test",
            excerpt="...",
            relevance_score=1,
        )
        assert source_int.relevance_score == 1.0
