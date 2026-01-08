"""
Tests for Eligibility Check API endpoints.
Tests eligibility checking, follow-up conversations, and session management.
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import User, Grant, LabProfile, ChatSession, ChatMessage
from backend.schemas.eligibility import EligibilityStatus, EligibilityCriterion
from backend.services.eligibility_checker import EligibilityChecker


@pytest.fixture
def mock_anthropic_response():
    """Mock response from Anthropic API for eligibility check."""
    return MagicMock(
        content=[MagicMock(text='''{
            "overall_status": "eligible",
            "overall_confidence": 0.85,
            "criteria": [
                {
                    "criterion": "Career stage requirement",
                    "met": true,
                    "explanation": "Researcher is at appropriate career stage for R01",
                    "confidence": 0.9
                },
                {
                    "criterion": "Institutional eligibility",
                    "met": true,
                    "explanation": "Institution is eligible for NIH funding",
                    "confidence": 0.95
                },
                {
                    "criterion": "Research area alignment",
                    "met": true,
                    "explanation": "Research areas align well with grant objectives",
                    "confidence": 0.8
                }
            ],
            "summary": "The researcher appears eligible for this grant based on their profile.",
            "recommendations": [
                "Strengthen preliminary data section",
                "Consider adding a co-investigator with complementary expertise"
            ],
            "missing_info": [
                "Publication history in the specific research area"
            ]
        }''')]
    )


@pytest.fixture
def mock_anthropic_partial_response():
    """Mock response for partial eligibility."""
    return MagicMock(
        content=[MagicMock(text='''{
            "overall_status": "partial",
            "overall_confidence": 0.6,
            "criteria": [
                {
                    "criterion": "Career stage requirement",
                    "met": true,
                    "explanation": "Early career investigator status confirmed",
                    "confidence": 0.9
                },
                {
                    "criterion": "Previous funding",
                    "met": false,
                    "explanation": "Mechanism requires no prior R01 funding, but profile indicates previous R01",
                    "confidence": 0.7
                }
            ],
            "summary": "Partial eligibility - some requirements not met.",
            "recommendations": ["Consider R21 mechanism instead"],
            "missing_info": []
        }''')]
    )


@pytest.fixture
def sample_eligibility_request():
    """Sample eligibility check request data."""
    return {
        "grant_id": str(uuid4()),
        "additional_context": "I have 5 years of postdoc experience and 15 publications"
    }


class TestEligibilityService:
    """Tests for EligibilityChecker service."""

    @pytest.mark.asyncio
    async def test_check_eligibility_returns_eligible(
        self, async_session, db_user, db_grant, mock_anthropic_response
    ):
        """Test eligibility check returns eligible status."""
        # Create lab profile for user
        profile = LabProfile(
            user_id=db_user.id,
            institution="MIT",
            department="Biology",
            research_areas=["Cancer Research", "Immunology"],
            career_stage="assistant_professor",
        )
        async_session.add(profile)
        await async_session.commit()

        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_response

            checker = EligibilityChecker()
            # Override the client
            checker.client = mock_client.return_value

            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
            )

            assert result.overall_status == EligibilityStatus.ELIGIBLE
            assert result.overall_confidence >= 0.8
            assert len(result.criteria) >= 1
            assert result.summary is not None
            assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_check_eligibility_creates_chat_session(
        self, async_session, db_user, db_grant, mock_anthropic_response
    ):
        """Test that eligibility check creates a chat session for follow-up."""
        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
            )

            # Should have created a session
            assert result.session_id is not None

            # Verify session exists in database
            from sqlalchemy import select
            session_result = await async_session.execute(
                select(ChatSession).where(ChatSession.id == result.session_id)
            )
            session = session_result.scalar_one_or_none()

            assert session is not None
            assert session.session_type == "eligibility"
            assert session.context_grant_id == db_grant.id

    @pytest.mark.asyncio
    async def test_check_eligibility_with_additional_context(
        self, async_session, db_user, db_grant, mock_anthropic_response
    ):
        """Test eligibility check includes additional context."""
        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
                additional_context="I have NIH K99 award currently active",
            )

            # Verify API was called with context
            call_args = mock_client.return_value.messages.create.call_args
            assert "K99" in str(call_args)

    @pytest.mark.asyncio
    async def test_check_eligibility_grant_not_found(self, async_session, db_user):
        """Test eligibility check raises error for non-existent grant."""
        checker = EligibilityChecker()

        with pytest.raises(ValueError, match="not found"):
            await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=uuid4(),
            )

    @pytest.mark.asyncio
    async def test_check_eligibility_partial_status(
        self, async_session, db_user, db_grant, mock_anthropic_partial_response
    ):
        """Test eligibility check returns partial status correctly."""
        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_partial_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
            )

            assert result.overall_status == EligibilityStatus.PARTIAL
            # Should have at least one criterion not met
            unmet = [c for c in result.criteria if not c.met]
            assert len(unmet) >= 1


class TestEligibilityFollowUp:
    """Tests for eligibility follow-up conversations."""

    @pytest.mark.asyncio
    async def test_follow_up_continues_conversation(
        self, async_session, db_user, db_grant
    ):
        """Test follow-up adds to conversation history."""
        # Create existing session
        session = ChatSession(
            user_id=db_user.id,
            title="Test Eligibility Session",
            session_type="eligibility",
            context_grant_id=db_grant.id,
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        # Add initial messages
        user_msg = ChatMessage(session_id=session.id, role="user", content="Am I eligible?")
        asst_msg = ChatMessage(session_id=session.id, role="assistant", content="Yes, you appear eligible.")
        async_session.add_all([user_msg, asst_msg])
        await async_session.commit()

        mock_response = MagicMock(
            content=[MagicMock(text="Based on your K99 award, you're in a strong position.")]
        )

        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            result = await checker.follow_up(
                db=async_session,
                user=db_user,
                session_id=session.id,
                message="I also have a K99 award",
            )

            assert result.response is not None
            assert "K99" in result.response

    @pytest.mark.asyncio
    async def test_follow_up_wrong_user_denied(self, async_session, db_user):
        """Test follow-up rejects requests from wrong user."""
        # Create session for different user
        other_user_id = uuid4()
        session = ChatSession(
            user_id=other_user_id,
            title="Other User Session",
            session_type="eligibility",
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        checker = EligibilityChecker()

        with pytest.raises(ValueError, match="not found"):
            await checker.follow_up(
                db=async_session,
                user=db_user,
                session_id=session.id,
                message="Test message",
            )


class TestEligibilityContextBuilding:
    """Tests for context building methods."""

    def test_build_researcher_context_with_full_profile(self):
        """Test building researcher context includes all profile data."""
        user = MagicMock(spec=User)
        user.name = "Dr. Jane Smith"
        user.email = "jane@university.edu"

        profile = MagicMock(spec=LabProfile)
        profile.department = "Molecular Biology"
        profile.institution = "Stanford University"
        profile.research_areas = ["Genomics", "Cancer Biology"]
        profile.career_stage = "associate_professor"
        profile.orcid = "0000-0002-1234-5678"
        profile.publications = {"count": 45}
        profile.past_grants = {"awards": ["R21", "R03"]}

        checker = EligibilityChecker()
        context = checker._build_researcher_context(user, profile, None)

        assert "Dr. Jane Smith" in context
        assert "Molecular Biology" in context
        assert "Stanford University" in context
        assert "Genomics" in context
        assert "associate_professor" in context
        assert "0000-0002-1234-5678" in context
        assert "45" in context

    def test_build_researcher_context_minimal_profile(self):
        """Test building context with minimal user info."""
        user = MagicMock(spec=User)
        user.name = None
        user.email = "researcher@lab.org"

        checker = EligibilityChecker()
        context = checker._build_researcher_context(user, None, None)

        assert "researcher@lab.org" in context

    def test_build_researcher_context_with_additional_context(self):
        """Test building context includes additional context."""
        user = MagicMock(spec=User)
        user.name = "Dr. Test User"
        user.email = "test@lab.org"

        checker = EligibilityChecker()
        context = checker._build_researcher_context(user, None, "I have K99 award")

        assert "K99" in context

    def test_build_grant_context(self):
        """Test building grant context includes key fields."""
        grant = MagicMock(spec=Grant)
        grant.title = "Research on Machine Learning in Healthcare"
        grant.agency = "NIH"
        grant.source = "nih"
        grant.description = "A grant for ML healthcare research"
        grant.eligibility = {"institution_types": ["universities"]}
        grant.amount_min = 250000
        grant.amount_max = 500000
        grant.deadline = datetime(2025, 6, 1, tzinfo=timezone.utc)
        grant.categories = ["machine_learning", "healthcare"]

        checker = EligibilityChecker()
        context = checker._build_grant_context(grant)

        assert "Machine Learning" in context
        assert "NIH" in context
        assert "250,000" in context
        assert "500,000" in context
        assert "2025-06-01" in context

    def test_build_grant_context_minimal(self):
        """Test building grant context with minimal data."""
        grant = MagicMock(spec=Grant)
        grant.title = "Test Grant"
        grant.agency = None
        grant.source = None
        grant.description = None
        grant.eligibility = None
        grant.amount_min = None
        grant.amount_max = None
        grant.deadline = None
        grant.categories = None

        checker = EligibilityChecker()
        context = checker._build_grant_context(grant)

        assert "Test Grant" in context
        assert "Unknown" in context  # Default funder


class TestEligibilityResponseParsing:
    """Tests for response parsing."""

    def test_parse_valid_eligibility_response(self):
        """Test parsing a valid JSON response."""
        response_text = '''{
            "overall_status": "eligible",
            "overall_confidence": 0.9,
            "criteria": [
                {"criterion": "Test", "met": true, "explanation": "OK", "confidence": 0.9}
            ],
            "summary": "Test summary",
            "recommendations": ["Do this"],
            "missing_info": ["Need that"]
        }'''

        grant = MagicMock(spec=Grant)
        grant.id = uuid4()
        grant.title = "Test Grant"

        checker = EligibilityChecker()
        result = checker._parse_eligibility_response(response_text, grant)

        assert result.overall_status == EligibilityStatus.ELIGIBLE
        assert result.overall_confidence == 0.9
        assert len(result.criteria) == 1
        assert result.summary == "Test summary"
        assert result.recommendations == ["Do this"]
        assert result.missing_info == ["Need that"]

    def test_parse_malformed_response_returns_unknown(self):
        """Test parsing malformed JSON returns unknown status."""
        response_text = "This is not valid JSON at all"

        grant = MagicMock(spec=Grant)
        grant.id = uuid4()
        grant.title = "Test Grant"

        checker = EligibilityChecker()
        result = checker._parse_eligibility_response(response_text, grant)

        assert result.overall_status == EligibilityStatus.UNKNOWN
        assert result.overall_confidence == 0.0

    def test_parse_partial_json_response(self):
        """Test parsing JSON with missing fields uses defaults."""
        response_text = '''{
            "overall_status": "partial",
            "overall_confidence": 0.7
        }'''

        grant = MagicMock(spec=Grant)
        grant.id = uuid4()
        grant.title = "Test Grant"

        checker = EligibilityChecker()
        result = checker._parse_eligibility_response(response_text, grant)

        assert result.overall_status == EligibilityStatus.PARTIAL
        assert result.overall_confidence == 0.7
        assert result.criteria == []
        assert result.recommendations == []
        assert result.missing_info == []

    def test_parse_response_with_json_in_text(self):
        """Test parsing response with JSON embedded in text."""
        response_text = '''Here is my analysis:

        {
            "overall_status": "eligible",
            "overall_confidence": 0.85,
            "criteria": [],
            "summary": "You are eligible",
            "recommendations": [],
            "missing_info": []
        }

        Let me know if you have questions.'''

        grant = MagicMock(spec=Grant)
        grant.id = uuid4()
        grant.title = "Test Grant"

        checker = EligibilityChecker()
        result = checker._parse_eligibility_response(response_text, grant)

        assert result.overall_status == EligibilityStatus.ELIGIBLE
        assert result.overall_confidence == 0.85


class TestEligibilityPromptBuilding:
    """Tests for prompt building methods."""

    def test_build_eligibility_prompt_includes_contexts(self):
        """Test that eligibility prompt includes both contexts."""
        checker = EligibilityChecker()

        researcher_context = "Researcher: Dr. Smith\nInstitution: MIT"
        grant_context = "Grant: Cancer Research Fund\nFunder: NIH"

        prompt = checker._build_eligibility_prompt(researcher_context, grant_context)

        assert "RESEARCHER PROFILE:" in prompt
        assert "Dr. Smith" in prompt
        assert "GRANT OPPORTUNITY:" in prompt
        assert "Cancer Research Fund" in prompt
        assert "overall_status" in prompt  # JSON format instructions

    def test_build_eligibility_prompt_includes_criteria_focus(self):
        """Test that prompt includes key criteria to evaluate."""
        checker = EligibilityChecker()

        prompt = checker._build_eligibility_prompt("researcher", "grant")

        assert "Career stage" in prompt
        assert "Institutional" in prompt
        assert "Citizenship" in prompt or "visa" in prompt
        assert "Previous funding" in prompt or "funding" in prompt
        assert "Research area" in prompt


class TestEligibilityEdgeCases:
    """Tests for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_check_eligibility_no_profile(
        self, async_session, db_user, db_grant, mock_anthropic_response
    ):
        """Test eligibility check works without lab profile."""
        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            # User has no lab profile
            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
            )

            # Should still return a result
            assert result.grant_id == db_grant.id
            assert result.overall_status in EligibilityStatus

    @pytest.mark.asyncio
    async def test_follow_up_session_not_found(self, async_session, db_user):
        """Test follow-up with non-existent session."""
        checker = EligibilityChecker()

        with pytest.raises(ValueError, match="not found"):
            await checker.follow_up(
                db=async_session,
                user=db_user,
                session_id=uuid4(),  # Non-existent session
                message="Test message",
            )

    def test_eligibility_criterion_validation(self):
        """Test EligibilityCriterion model validation."""
        # Valid criterion
        criterion = EligibilityCriterion(
            criterion="Test criterion",
            met=True,
            explanation="Test explanation",
            confidence=0.9
        )
        assert criterion.criterion == "Test criterion"
        assert criterion.met is True
        assert criterion.confidence == 0.9

    def test_eligibility_criterion_confidence_bounds(self):
        """Test EligibilityCriterion confidence must be 0-1."""
        from pydantic import ValidationError

        # Confidence too high
        with pytest.raises(ValidationError):
            EligibilityCriterion(
                criterion="Test",
                met=True,
                explanation="Test",
                confidence=1.5
            )

        # Confidence too low
        with pytest.raises(ValidationError):
            EligibilityCriterion(
                criterion="Test",
                met=True,
                explanation="Test",
                confidence=-0.1
            )


class TestChatSessionMessages:
    """Tests for chat session and message handling."""

    @pytest.mark.asyncio
    async def test_eligibility_check_saves_messages(
        self, async_session, db_user, db_grant, mock_anthropic_response
    ):
        """Test that eligibility check saves initial messages."""
        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            result = await checker.check_eligibility(
                db=async_session,
                user=db_user,
                grant_id=db_grant.id,
            )

            # Verify messages were saved
            from sqlalchemy import select
            messages_result = await async_session.execute(
                select(ChatMessage).where(ChatMessage.session_id == result.session_id)
            )
            messages = messages_result.scalars().all()

            # Should have user message and assistant response
            assert len(messages) >= 2
            roles = [m.role for m in messages]
            assert "user" in roles
            assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_follow_up_saves_new_messages(
        self, async_session, db_user, db_grant
    ):
        """Test that follow-up saves new messages to session."""
        # Create session with initial messages
        session = ChatSession(
            user_id=db_user.id,
            title="Test Session",
            session_type="eligibility",
            context_grant_id=db_grant.id,
        )
        async_session.add(session)
        await async_session.commit()
        await async_session.refresh(session)

        initial_msg = ChatMessage(
            session_id=session.id,
            role="user",
            content="Initial question"
        )
        async_session.add(initial_msg)
        await async_session.commit()

        mock_response = MagicMock(
            content=[MagicMock(text="Here is the follow-up response.")]
        )

        with patch('backend.services.eligibility_checker.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_response

            checker = EligibilityChecker()
            checker.client = mock_client.return_value

            await checker.follow_up(
                db=async_session,
                user=db_user,
                session_id=session.id,
                message="Follow-up question",
            )

            # Check messages were added
            from sqlalchemy import select
            messages_result = await async_session.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session.id)
                .order_by(ChatMessage.created_at)
            )
            messages = messages_result.scalars().all()

            # Should have initial + user follow-up + assistant response
            assert len(messages) >= 3
            assert messages[-2].content == "Follow-up question"
            assert messages[-1].content == "Here is the follow-up response."
