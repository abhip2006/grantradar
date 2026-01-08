"""
GrantRadar Test Configuration and Fixtures
Shared pytest fixtures for all test modules.
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.models import Base, Grant, User, LabProfile, Match, AlertSent


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create an async SQLite engine for testing."""
    import tempfile
    import os

    # Use a unique temp file for each test to ensure complete isolation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()

    # Clean up the temp file
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create an async session for testing."""
    async_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="function")
def sync_engine():
    """Create a sync SQLite engine for testing."""
    import tempfile
    import os

    # Use a unique temp file for each test to ensure complete isolation
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        echo=False,
    )

    Base.metadata.create_all(engine)

    yield engine

    engine.dispose()

    # Clean up the temp file
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture(scope="function")
def sync_session(sync_engine) -> Generator[Session, None, None]:
    """Create a sync session for testing."""
    SessionLocal = sessionmaker(bind=sync_engine, autocommit=False, autoflush=False)
    session = SessionLocal()

    yield session

    session.rollback()
    session.close()


# =============================================================================
# Redis Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis_mock = MagicMock()
    redis_mock.xadd = AsyncMock(return_value="1234567890-0")
    redis_mock.xread = AsyncMock(return_value=[])
    redis_mock.xreadgroup = AsyncMock(return_value=[])
    redis_mock.xack = AsyncMock(return_value=1)
    redis_mock.xlen = AsyncMock(return_value=0)
    redis_mock.xinfo_stream = AsyncMock(return_value={"length": 0})
    redis_mock.xinfo_groups = AsyncMock(return_value=[])
    redis_mock.xgroup_create = AsyncMock(return_value=True)
    redis_mock.sismember = AsyncMock(return_value=False)
    redis_mock.sadd = AsyncMock(return_value=1)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.close = AsyncMock()
    redis_mock.aclose = AsyncMock()

    return redis_mock


@pytest.fixture
def mock_redis_stream_data():
    """Sample Redis stream data for testing."""
    return {
        "grants:discovered": [
            (
                "1704067200000-0",
                {
                    "payload": json.dumps({
                        "event_id": str(uuid.uuid4()),
                        "grant_id": str(uuid.uuid4()),
                        "source": "grants_gov",
                        "title": "Test Research Grant",
                        "url": "https://grants.gov/test",
                        "timestamp": datetime.utcnow().isoformat(),
                    }),
                    "event_type": "GrantDiscoveredEvent",
                    "published_at": datetime.utcnow().isoformat(),
                }
            )
        ]
    }


class FakeRedis:
    """Fake Redis implementation for testing."""

    def __init__(self):
        self.streams: dict[str, list] = {}
        self.sets: dict[str, set] = {}
        self.strings: dict[str, str] = {}
        self.hashes: dict[str, dict] = {}
        self._counter = 0

    async def xadd(self, stream: str, data: dict, maxlen: int = None, approximate: bool = True) -> str:
        """Add entry to stream."""
        if stream not in self.streams:
            self.streams[stream] = []

        self._counter += 1
        msg_id = f"{int(datetime.utcnow().timestamp() * 1000)}-{self._counter}"
        self.streams[stream].append((msg_id, data))
        return msg_id

    async def xread(self, streams: dict, count: int = None, block: int = None) -> list:
        """Read from streams."""
        result = []
        for stream_name, last_id in streams.items():
            if stream_name in self.streams:
                messages = self.streams[stream_name]
                result.append((stream_name, messages[-count:] if count else messages))
        return result

    async def xreadgroup(self, groupname: str, consumername: str, streams: dict, count: int = None, block: int = None) -> list:
        """Read from streams using consumer group."""
        return await self.xread(streams, count, block)

    async def xack(self, stream: str, group: str, msg_id: str) -> int:
        """Acknowledge message."""
        return 1

    async def xlen(self, stream: str) -> int:
        """Get stream length."""
        return len(self.streams.get(stream, []))

    async def sismember(self, key: str, value: str) -> bool:
        """Check set membership."""
        return value in self.sets.get(key, set())

    async def sadd(self, key: str, *values: str) -> int:
        """Add to set."""
        if key not in self.sets:
            self.sets[key] = set()
        added = 0
        for v in values:
            if v not in self.sets[key]:
                self.sets[key].add(v)
                added += 1
        return added

    async def set(self, key: str, value: str, ex: int = None) -> bool:
        """Set string value."""
        self.strings[key] = value
        return True

    async def get(self, key: str) -> str | None:
        """Get string value."""
        return self.strings.get(key)

    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration (no-op in fake)."""
        return True

    async def ping(self) -> bool:
        """Ping test."""
        return True

    async def close(self) -> None:
        """Close connection."""
        pass

    async def aclose(self) -> None:
        """Close async connection."""
        pass

    async def xgroup_create(self, stream: str, group: str, id: str = "0", mkstream: bool = False) -> bool:
        """Create consumer group."""
        if mkstream and stream not in self.streams:
            self.streams[stream] = []
        return True

    async def xinfo_stream(self, stream: str) -> dict:
        """Get stream info."""
        return {"length": len(self.streams.get(stream, []))}

    async def xinfo_groups(self, stream: str) -> list:
        """Get consumer groups info."""
        return []


@pytest.fixture
def fake_redis():
    """Provide a fake Redis instance for testing."""
    return FakeRedis()


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_grant_data() -> dict[str, Any]:
    """Sample grant data for testing."""
    return {
        "id": uuid.uuid4(),
        "source": "grants_gov",
        "external_id": "GRANT-2024-001",
        "title": "Research Grant for Machine Learning in Healthcare",
        "description": "This grant supports innovative research in applying machine learning techniques to healthcare challenges including disease prediction, drug discovery, and personalized medicine.",
        "agency": "National Institutes of Health",
        "amount_min": 100000,
        "amount_max": 500000,
        "deadline": datetime.now(timezone.utc) + timedelta(days=30),
        "posted_at": datetime.now(timezone.utc) - timedelta(days=5),
        "url": "https://grants.gov/view-opportunity.html?oppId=123456",
        "eligibility": {
            "institution_types": ["universities", "research_institutions"],
            "career_stages": ["early_career", "established"],
            "citizenship": ["us_citizen", "permanent_resident"],
        },
        "categories": ["machine_learning", "healthcare", "data_science"],
    }


@pytest.fixture
def sample_grant_list() -> list[dict[str, Any]]:
    """List of sample grants for testing."""
    return [
        {
            "id": uuid.uuid4(),
            "source": "grants_gov",
            "external_id": "GRANT-2024-001",
            "title": "AI in Healthcare Research",
            "description": "Research on AI applications in healthcare",
            "agency": "NIH",
            "amount_min": 100000,
            "amount_max": 500000,
            "deadline": datetime.now(timezone.utc) + timedelta(days=30),
            "categories": ["ai", "healthcare"],
        },
        {
            "id": uuid.uuid4(),
            "source": "nsf",
            "external_id": "NSF-2024-002",
            "title": "Climate Science Research",
            "description": "Research on climate change impacts",
            "agency": "NSF",
            "amount_min": 200000,
            "amount_max": 750000,
            "deadline": datetime.now(timezone.utc) + timedelta(days=60),
            "categories": ["climate", "environment"],
        },
        {
            "id": uuid.uuid4(),
            "source": "nih",
            "external_id": "NIH-2024-003",
            "title": "Cancer Research Initiative",
            "description": "Novel approaches to cancer treatment",
            "agency": "National Cancer Institute",
            "amount_min": 500000,
            "amount_max": 2000000,
            "deadline": datetime.now(timezone.utc) + timedelta(days=14),
            "categories": ["cancer", "oncology", "treatment"],
        },
    ]


@pytest.fixture
def sample_user_data() -> dict[str, Any]:
    """Sample user data for testing."""
    return {
        "id": uuid.uuid4(),
        "email": "researcher@university.edu",
        "password_hash": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4eqZzJMnE8mFJGSq",  # "password123"
        "name": "Dr. Jane Smith",
        "institution": "Stanford University",
        "phone": "+1-555-123-4567",
    }


@pytest.fixture
def sample_lab_profile_data() -> dict[str, Any]:
    """Sample lab profile data for testing."""
    return {
        "id": uuid.uuid4(),
        "research_areas": ["machine_learning", "natural_language_processing", "computer_vision"],
        "methods": ["deep_learning", "transformer_models", "convolutional_networks"],
        "career_stage": "established",
        "past_grants": {
            "awards": [
                {"agency": "NSF", "amount": 500000, "year": 2022},
                {"agency": "NIH", "amount": 300000, "year": 2021},
            ]
        },
        "publications": {
            "total": 45,
            "h_index": 18,
            "recent_topics": ["LLM", "healthcare AI", "federated learning"],
        },
        "orcid": "0000-0002-1234-5678",
    }


@pytest.fixture
def sample_match_data() -> dict[str, Any]:
    """Sample match data for testing."""
    return {
        "id": uuid.uuid4(),
        "match_score": 0.87,
        "reasoning": "Strong alignment between research focus on machine learning in healthcare and grant objectives. Prior NIH funding experience is a positive factor.",
        "predicted_success": 0.72,
        "user_action": None,
    }


# =============================================================================
# Database Model Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_user(async_session: AsyncSession, sample_user_data) -> User:
    """Create a test user in the database."""
    user = User(
        id=sample_user_data["id"],
        email=sample_user_data["email"],
        password_hash=sample_user_data["password_hash"],
        name=sample_user_data["name"],
        institution=sample_user_data["institution"],
        phone=sample_user_data["phone"],
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def db_lab_profile(async_session: AsyncSession, db_user: User, sample_lab_profile_data) -> LabProfile:
    """Create a test lab profile in the database."""
    profile = LabProfile(
        id=sample_lab_profile_data["id"],
        user_id=db_user.id,
        research_areas=sample_lab_profile_data["research_areas"],
        methods=sample_lab_profile_data["methods"],
        career_stage=sample_lab_profile_data["career_stage"],
        past_grants=sample_lab_profile_data["past_grants"],
        publications=sample_lab_profile_data["publications"],
        orcid=sample_lab_profile_data["orcid"],
    )
    async_session.add(profile)
    await async_session.commit()
    await async_session.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def db_grant(async_session: AsyncSession, sample_grant_data) -> Grant:
    """Create a test grant in the database."""
    # Remove embedding field for SQLite compatibility (no pgvector)
    grant_data = {k: v for k, v in sample_grant_data.items() if k != "embedding"}

    grant = Grant(**grant_data)
    async_session.add(grant)
    await async_session.commit()
    await async_session.refresh(grant)
    return grant


@pytest_asyncio.fixture
async def db_match(async_session: AsyncSession, db_user: User, db_grant: Grant, sample_match_data) -> Match:
    """Create a test match in the database."""
    match = Match(
        id=sample_match_data["id"],
        grant_id=db_grant.id,
        user_id=db_user.id,
        match_score=sample_match_data["match_score"],
        reasoning=sample_match_data["reasoning"],
        predicted_success=sample_match_data["predicted_success"],
    )
    async_session.add(match)
    await async_session.commit()
    await async_session.refresh(match)
    return match


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for testing."""
    client = AsyncMock()

    async def mock_get(url, **kwargs):
        response = AsyncMock()
        response.status_code = 200
        response.text = "<html><body>Test</body></html>"
        response.json.return_value = {"data": []}
        response.raise_for_status = MagicMock()
        return response

    async def mock_post(url, **kwargs):
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = {"oppHits": []}
        response.raise_for_status = MagicMock()
        return response

    client.get = mock_get
    client.post = mock_post
    client.aclose = AsyncMock()

    return client


# =============================================================================
# RSS Feed Fixtures
# =============================================================================


@pytest.fixture
def sample_rss_feed():
    """Sample RSS feed XML for testing."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Grants.gov RSS Feed</title>
            <link>https://www.grants.gov</link>
            <description>New Grant Opportunities</description>
            <item>
                <title>Research Grant Opportunity</title>
                <link>https://www.grants.gov/view-opportunity.html?oppId=123456</link>
                <guid>123456</guid>
                <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                <description>This is a test grant opportunity for research.</description>
            </item>
            <item>
                <title>Education Grant Opportunity</title>
                <link>https://www.grants.gov/view-opportunity.html?oppId=123457</link>
                <guid>123457</guid>
                <pubDate>Tue, 02 Jan 2024 00:00:00 GMT</pubDate>
                <description>This is a test grant opportunity for education.</description>
            </item>
        </channel>
    </rss>"""


@pytest.fixture
def malformed_rss_feed():
    """Malformed RSS feed for error handling tests."""
    return """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
        <channel>
            <title>Broken Feed</title>
            <item>
                <title>Incomplete Item
            </item>
        </channel>
    </rss>"""


# =============================================================================
# Mock External Services
# =============================================================================


@pytest.fixture
def mock_sendgrid():
    """Mock SendGrid client for email testing."""
    with patch("sendgrid.SendGridAPIClient") as mock:
        instance = MagicMock()
        instance.send = MagicMock(return_value=MagicMock(status_code=202))
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_twilio():
    """Mock Twilio client for SMS testing."""
    with patch("twilio.rest.Client") as mock:
        instance = MagicMock()
        message_mock = MagicMock()
        message_mock.sid = "SM1234567890"
        message_mock.status = "queued"
        instance.messages.create = MagicMock(return_value=message_mock)
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_anthropic():
    """Mock Anthropic client for LLM testing."""
    with patch("anthropic.Anthropic") as mock:
        instance = MagicMock()

        # Mock message response
        message_response = MagicMock()
        message_response.content = [MagicMock(text='{"match_score": 85, "reasoning": "Good match"}')]
        instance.messages.create = MagicMock(return_value=message_response)

        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_openai():
    """Mock OpenAI client for embedding generation."""
    with patch("openai.OpenAI") as mock:
        instance = MagicMock()

        # Mock embedding response
        embedding_response = MagicMock()
        embedding_response.data = [MagicMock(embedding=[0.1] * 1536)]
        instance.embeddings.create = MagicMock(return_value=embedding_response)

        mock.return_value = instance
        yield mock


# =============================================================================
# Event Fixtures
# =============================================================================


@pytest.fixture
def sample_grant_discovered_event():
    """Sample GrantDiscoveredEvent for testing."""
    from backend.core.events import GrantDiscoveredEvent

    return GrantDiscoveredEvent(
        event_id=uuid.uuid4(),
        grant_id=uuid.uuid4(),
        source="grants_gov",
        title="Test Research Grant",
        url="https://grants.gov/test",
        funding_agency="NIH",
        estimated_amount=250000.0,
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
    )


@pytest.fixture
def sample_grant_validated_event():
    """Sample GrantValidatedEvent for testing."""
    from backend.core.events import GrantValidatedEvent

    return GrantValidatedEvent(
        event_id=uuid.uuid4(),
        grant_id=uuid.uuid4(),
        quality_score=0.92,
        categories=["machine_learning", "healthcare"],
        embedding_generated=True,
        keywords=["AI", "health", "research"],
    )


@pytest.fixture
def sample_match_computed_event():
    """Sample MatchComputedEvent for testing."""
    from backend.core.events import MatchComputedEvent, PriorityLevel

    return MatchComputedEvent(
        event_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        grant_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        match_score=0.87,
        priority_level=PriorityLevel.HIGH,
        matching_criteria=["research_area", "career_stage"],
        explanation="Strong match based on research focus alignment.",
    )


@pytest.fixture
def sample_alert_pending_event():
    """Sample AlertPendingEvent for testing."""
    from backend.core.events import AlertPendingEvent, AlertChannel

    return AlertPendingEvent(
        event_id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        match_id=uuid.uuid4(),
        channel=AlertChannel.EMAIL,
        user_email="test@university.edu",
        alert_title="New Grant Match: AI in Healthcare",
        alert_body="A new grant opportunity matches your research profile.",
    )


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def freeze_time():
    """Context manager to freeze time for testing."""
    from unittest.mock import patch
    from datetime import datetime

    frozen_time = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)

    with patch("datetime.datetime") as mock_dt:
        mock_dt.now.return_value = frozen_time
        mock_dt.utcnow.return_value = frozen_time.replace(tzinfo=None)
        mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
        yield frozen_time


@pytest.fixture
def sample_embedding():
    """Sample 1536-dimensional embedding vector."""
    import random
    random.seed(42)
    return [random.uniform(-1, 1) for _ in range(1536)]


@pytest.fixture
def high_similarity_embedding(sample_embedding):
    """Embedding with high similarity to sample_embedding."""
    import random
    random.seed(43)
    # Add small noise to create similar but not identical embedding
    return [v + random.uniform(-0.01, 0.01) for v in sample_embedding]


@pytest.fixture
def low_similarity_embedding():
    """Embedding with low similarity to sample_embedding."""
    import random
    random.seed(99)
    return [random.uniform(-1, 1) for _ in range(1536)]
