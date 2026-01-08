"""
API test fixtures.
Fixtures for testing deadline API endpoints and other API tests.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock
from uuid import uuid4

from backend.models import (
    Base,
    Grant,
    User,
    LabProfile,
    Match,
    AlertSent,
    Deadline,
    ChatSession,
    ChatMessage,
    ResearchSession,
    FundingAlertPreference,
)


@pytest_asyncio.fixture
async def db_deadline(async_session, db_user):
    """Create a test deadline in the database."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Test API Deadline",
        description="A test deadline for API testing",
        funder="NIH",
        mechanism="R01",
        sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=30),
        internal_deadline=datetime.now(timezone.utc) + timedelta(days=25),
        status="active",
        priority="high",
        url="https://grants.nih.gov/test",
        notes="Test notes",
        color="#3B82F6",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_deadlines_varied(async_session, db_user):
    """Create a varied set of deadlines for testing filters and sorting."""
    now = datetime.now(timezone.utc)
    deadlines = []

    # Create deadlines with different statuses
    for status in ["active", "completed", "archived"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{status.capitalize()} Deadline",
            sponsor_deadline=now + timedelta(days=30),
            status=status,
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines with different priorities
    for priority in ["low", "medium", "high"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{priority.capitalize()} Priority Deadline",
            sponsor_deadline=now + timedelta(days=45),
            priority=priority,
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines with different funders
    for funder in ["NIH", "NSF", "DOE"]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"{funder} Grant Deadline",
            sponsor_deadline=now + timedelta(days=60),
            funder=funder,
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    # Create deadlines at different times
    for days in [7, 14, 30, 60, 90]:
        deadline = Deadline(
            user_id=db_user.id,
            title=f"Deadline in {days} days",
            sponsor_deadline=now + timedelta(days=days),
            status="active",
        )
        deadlines.append(deadline)
        async_session.add(deadline)

    await async_session.commit()

    for deadline in deadlines:
        await async_session.refresh(deadline)

    return deadlines


@pytest_asyncio.fixture
async def db_deadline_with_grant(async_session, db_user, db_grant):
    """Create a deadline linked to a grant."""
    deadline = Deadline(
        user_id=db_user.id,
        grant_id=db_grant.id,
        title=db_grant.title,
        funder=db_grant.agency,
        sponsor_deadline=db_grant.deadline,
        url=db_grant.url,
        status="active",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_overdue_deadline(async_session, db_user):
    """Create an overdue deadline for testing."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Overdue Deadline",
        sponsor_deadline=datetime.now(timezone.utc) - timedelta(days=5),
        status="active",
        priority="high",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


@pytest_asyncio.fixture
async def db_urgent_deadline(async_session, db_user):
    """Create an urgent deadline (within 7 days) for testing."""
    deadline = Deadline(
        user_id=db_user.id,
        title="Urgent Deadline",
        sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=3),
        status="active",
        priority="high",
    )
    async_session.add(deadline)
    await async_session.commit()
    await async_session.refresh(deadline)
    return deadline


# ===== AI Tools Fixtures =====

@pytest_asyncio.fixture
async def db_chat_session(async_session, db_user):
    """Create a test chat session in the database."""
    session = ChatSession(
        user_id=db_user.id,
        title="Test Chat Session",
        session_type="proposal_chat",
    )
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def db_chat_session_with_messages(async_session, db_user):
    """Create a chat session with sample messages."""
    session = ChatSession(
        user_id=db_user.id,
        title="Chat with Messages",
        session_type="proposal_chat",
    )
    async_session.add(session)
    await async_session.flush()

    messages = [
        ChatMessage(session_id=session.id, role="user", content="What grants are available for AI research?"),
        ChatMessage(session_id=session.id, role="assistant", content="There are several NIH and NSF grants available for AI research."),
        ChatMessage(session_id=session.id, role="user", content="Which one has the highest funding?"),
    ]
    for msg in messages:
        async_session.add(msg)

    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def db_research_session(async_session, db_user):
    """Create a test research session in the database."""
    session = ResearchSession(
        user_id=db_user.id,
        query="machine learning applications in healthcare",
        status="pending",
    )
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def db_completed_research_session(async_session, db_user):
    """Create a completed research session with results."""
    session = ResearchSession(
        user_id=db_user.id,
        query="cancer immunotherapy funding opportunities",
        status="completed",
        results=[
            {
                "id": str(uuid4()),
                "title": "NIH Cancer Immunotherapy Grant",
                "funder": "NIH",
                "mechanism": "R01",
                "relevance_score": 0.92,
                "match_reasons": ["Strong alignment", "Methodology match"],
            }
        ],
        insights="Focus on the NIH R01 opportunity for cancer immunotherapy.",
        grants_found=5,
        processing_time_ms=3500,
        completed_at=datetime.now(timezone.utc),
    )
    async_session.add(session)
    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def db_funding_alert_preferences(async_session, db_user):
    """Create funding alert preferences for a user."""
    prefs = FundingAlertPreference(
        user_id=db_user.id,
        enabled=True,
        frequency="weekly",
        min_match_score=75,
        include_deadlines=True,
        include_new_grants=True,
        include_insights=True,
        preferred_funders=["NIH", "NSF"],
    )
    async_session.add(prefs)
    await async_session.commit()
    await async_session.refresh(prefs)
    return prefs


@pytest_asyncio.fixture
async def db_eligibility_session(async_session, db_user, db_grant):
    """Create an eligibility check chat session."""
    session = ChatSession(
        user_id=db_user.id,
        title=f"Eligibility: {db_grant.title[:50]}",
        session_type="eligibility",
        context_grant_id=db_grant.id,
        metadata_={"grant_title": db_grant.title, "initial_status": "eligible"},
    )
    async_session.add(session)
    await async_session.flush()

    messages = [
        ChatMessage(session_id=session.id, role="user", content=f"Check my eligibility for: {db_grant.title}"),
        ChatMessage(session_id=session.id, role="assistant", content="Based on your profile, you appear eligible for this grant."),
    ]
    for msg in messages:
        async_session.add(msg)

    await async_session.commit()
    await async_session.refresh(session)
    return session


@pytest_asyncio.fixture
async def db_lab_profile(async_session, db_user):
    """Create a lab profile for the test user."""
    profile = LabProfile(
        user_id=db_user.id,
        institution="MIT",
        department="Computer Science",
        research_areas=["Machine Learning", "Healthcare AI", "Computer Vision"],
        career_stage="assistant_professor",
        publications_count=25,
        nih_era_commons_id="TESTUSER123",
    )
    async_session.add(profile)
    await async_session.commit()
    await async_session.refresh(profile)
    return profile


# ===== Mock Fixtures for External APIs =====

@pytest.fixture
def mock_anthropic_client():
    """Create a mock Anthropic client for testing."""
    mock = MagicMock()
    mock.messages.create.return_value = MagicMock(
        content=[MagicMock(text='{"status": "success"}')]
    )
    return mock


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client for testing."""
    mock = MagicMock()
    mock.embeddings.create.return_value = MagicMock(
        data=[MagicMock(embedding=[0.1] * 1536)]
    )
    return mock


@pytest.fixture
def mock_sendgrid_client():
    """Create a mock SendGrid client for testing."""
    mock = MagicMock()
    mock.send.return_value = MagicMock(status_code=202)
    return mock
