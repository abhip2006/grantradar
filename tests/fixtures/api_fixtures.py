"""
API Test Fixtures
Fixtures for testing FastAPI endpoints with authentication and database setup.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    ApplicationStage,
    Grant,
    GrantApplication,
    LabProfile,
    Match,
    SavedSearch,
    User,
)
from .factories import (
    GrantApplicationFactory,
    GrantFactory,
    LabProfileFactory,
    MatchFactory,
    SavedSearchFactory,
    UserFactory,
)


# =============================================================================
# Authentication Fixtures
# =============================================================================


def create_test_token(user_id: uuid.UUID, expires_delta: timedelta = timedelta(hours=1)) -> str:
    """Create a test JWT token for authentication."""
    from jose import jwt
    from backend.core.config import settings

    expire = datetime.utcnow() + expires_delta
    to_encode = {"sub": str(user_id), "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret_key, algorithm="HS256")


@pytest.fixture
def auth_headers(db_user: User) -> dict[str, str]:
    """Create authorization headers for API requests."""
    token = create_test_token(db_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def expired_auth_headers(db_user: User) -> dict[str, str]:
    """Create expired authorization headers for testing."""
    token = create_test_token(db_user.id, expires_delta=timedelta(hours=-1))
    return {"Authorization": f"Bearer {token}"}


# =============================================================================
# Database Setup Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_user_with_profile(async_session: AsyncSession) -> tuple[User, LabProfile]:
    """Create a user with a complete lab profile."""
    user = UserFactory.create()
    async_session.add(user)
    await async_session.flush()

    profile = LabProfileFactory.create(user_id=user.id)
    async_session.add(profile)
    await async_session.commit()

    await async_session.refresh(user)
    await async_session.refresh(profile)
    return user, profile


@pytest_asyncio.fixture
async def db_grants_varied(async_session: AsyncSession) -> list[Grant]:
    """Create a varied set of grants for testing."""
    grants = []

    # Create grants from different sources
    for source in ["grants_gov", "nsf", "nih"]:
        for i in range(3):
            grant = GrantFactory.create(source=source)
            grants.append(grant)
            async_session.add(grant)

    # Add some expired grants
    for i in range(2):
        grant = GrantFactory.create_expired(days_ago=i + 1)
        grants.append(grant)
        async_session.add(grant)

    # Add some urgent grants
    for i in range(2):
        grant = GrantFactory.create_urgent(days_until=i + 1)
        grants.append(grant)
        async_session.add(grant)

    await async_session.commit()

    for grant in grants:
        await async_session.refresh(grant)

    return grants


@pytest_asyncio.fixture
async def db_matches_for_user(
    async_session: AsyncSession,
    db_user: User,
    db_grants_varied: list[Grant],
) -> list[Match]:
    """Create matches between a user and multiple grants."""
    matches = []

    for i, grant in enumerate(db_grants_varied[:10]):
        # Create varied scores
        score = 0.5 + (i % 5) * 0.1
        match = MatchFactory.create(
            user_id=db_user.id,
            grant_id=grant.id,
            match_score=score,
        )
        matches.append(match)
        async_session.add(match)

    await async_session.commit()

    for match in matches:
        await async_session.refresh(match)

    return matches


@pytest_asyncio.fixture
async def db_pipeline_full(
    async_session: AsyncSession,
    db_user: User,
    db_grants_varied: list[Grant],
) -> list[GrantApplication]:
    """Create a full pipeline with applications at each stage."""
    applications = []

    stages = list(ApplicationStage)

    for i, grant in enumerate(db_grants_varied[:len(stages) * 2]):
        stage = stages[i % len(stages)]
        app = GrantApplicationFactory.create(
            user_id=db_user.id,
            grant_id=grant.id,
            stage=stage,
        )
        applications.append(app)
        async_session.add(app)

    await async_session.commit()

    for app in applications:
        await async_session.refresh(app)

    return applications


@pytest_asyncio.fixture
async def db_saved_searches(
    async_session: AsyncSession,
    db_user: User,
) -> list[SavedSearch]:
    """Create saved searches for a user."""
    searches = []

    search_configs = [
        {"name": "AI Healthcare", "filters": {"categories": ["machine_learning", "healthcare"]}},
        {"name": "Climate Research", "filters": {"categories": ["climate", "environment"]}},
        {"name": "High Value Grants", "filters": {"amount_min": 500000}},
        {"name": "NSF Only", "filters": {"source": ["nsf"]}},
    ]

    for config in search_configs:
        search = SavedSearchFactory.create(
            user_id=db_user.id,
            name=config["name"],
            filters=config["filters"],
        )
        searches.append(search)
        async_session.add(search)

    await async_session.commit()

    for search in searches:
        await async_session.refresh(search)

    return searches


# =============================================================================
# Analytics Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_analytics_data(
    async_session: AsyncSession,
    db_user: User,
) -> dict:
    """Create comprehensive data for analytics testing."""
    # Create grants with varied agencies and categories
    agencies = ["NIH", "NSF", "DOE", "DARPA", "NCI"]
    categories_list = [
        ["machine_learning", "healthcare"],
        ["climate", "environment"],
        ["cancer", "oncology"],
        ["ai", "robotics"],
        ["neuroscience", "brain"],
    ]

    grants = []
    for i in range(20):
        grant = GrantFactory.create(
            agency=agencies[i % len(agencies)],
            categories=categories_list[i % len(categories_list)],
        )
        grants.append(grant)
        async_session.add(grant)

    await async_session.flush()

    # Create applications at different stages
    applications = []
    stages = [
        ApplicationStage.RESEARCHING,
        ApplicationStage.RESEARCHING,
        ApplicationStage.WRITING,
        ApplicationStage.WRITING,
        ApplicationStage.SUBMITTED,
        ApplicationStage.SUBMITTED,
        ApplicationStage.SUBMITTED,
        ApplicationStage.AWARDED,
        ApplicationStage.AWARDED,
        ApplicationStage.REJECTED,
    ]

    for i, grant in enumerate(grants):
        stage = stages[i % len(stages)]
        app = GrantApplicationFactory.create(
            user_id=db_user.id,
            grant_id=grant.id,
            stage=stage,
        )
        applications.append(app)
        async_session.add(app)

    await async_session.commit()

    return {
        "grants": grants,
        "applications": applications,
        "user": db_user,
    }


# =============================================================================
# Forecast Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_forecast_data(
    async_session: AsyncSession,
) -> list[Grant]:
    """Create grants with varied deadlines for forecast testing."""
    grants = []
    now = datetime.now(timezone.utc)

    # Create grants with deadlines spread across the year
    for month_offset in range(-6, 12):
        for i in range(3):
            deadline = now + timedelta(days=month_offset * 30 + i * 5)
            grant = GrantFactory.create(
                deadline=deadline,
                posted_at=deadline - timedelta(days=90),
            )
            grants.append(grant)
            async_session.add(grant)

    await async_session.commit()

    return grants


# =============================================================================
# Funder Insights Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_funder_data(
    async_session: AsyncSession,
    db_user: User,
) -> dict:
    """Create data for funder insights testing."""
    funders = {
        "National Institutes of Health": [],
        "National Science Foundation": [],
        "Department of Energy": [],
    }

    for funder_name in funders.keys():
        for i in range(10):
            grant = GrantFactory.create(agency=funder_name)
            funders[funder_name].append(grant)
            async_session.add(grant)

    await async_session.flush()

    # Create some applications for user history
    applications = []
    all_grants = [g for grants in funders.values() for g in grants]

    for i, grant in enumerate(all_grants[:15]):
        stage = [ApplicationStage.SUBMITTED, ApplicationStage.AWARDED, ApplicationStage.REJECTED][i % 3]
        app = GrantApplicationFactory.create(
            user_id=db_user.id,
            grant_id=grant.id,
            stage=stage,
        )
        applications.append(app)
        async_session.add(app)

    await async_session.commit()

    return {
        "funders": funders,
        "applications": applications,
        "user": db_user,
    }


# =============================================================================
# Calendar Test Data Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def db_calendar_data(
    async_session: AsyncSession,
    db_user: User,
) -> dict:
    """Create data for calendar testing."""
    now = datetime.now(timezone.utc)
    grants = []
    applications = []

    # Create grants with deadlines at various times
    deadline_configs = [
        ("today", now),
        ("tomorrow", now + timedelta(days=1)),
        ("this_week", now + timedelta(days=3)),
        ("next_week", now + timedelta(days=10)),
        ("this_month", now + timedelta(days=20)),
        ("next_month", now + timedelta(days=45)),
    ]

    for name, deadline in deadline_configs:
        grant = GrantFactory.create(
            title=f"Grant deadline {name}",
            deadline=deadline,
        )
        grants.append(grant)
        async_session.add(grant)

    await async_session.flush()

    # Add grants to pipeline
    for grant in grants:
        app = GrantApplicationFactory.create(
            user_id=db_user.id,
            grant_id=grant.id,
            stage=ApplicationStage.WRITING,
            target_date=grant.deadline - timedelta(days=7),
        )
        applications.append(app)
        async_session.add(app)

    await async_session.commit()

    return {
        "grants": grants,
        "applications": applications,
        "user": db_user,
    }


# =============================================================================
# HTTP Client Mock Fixtures
# =============================================================================


@pytest.fixture
def mock_external_apis():
    """Mock all external API dependencies."""
    with patch("httpx.AsyncClient") as mock_httpx, \
         patch("openai.OpenAI") as mock_openai, \
         patch("anthropic.Anthropic") as mock_anthropic:

        # Setup httpx mock
        httpx_instance = AsyncMock()
        httpx_instance.get = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {}))
        httpx_instance.post = AsyncMock(return_value=MagicMock(status_code=200, json=lambda: {}))
        mock_httpx.return_value.__aenter__.return_value = httpx_instance

        # Setup OpenAI mock
        openai_instance = MagicMock()
        openai_instance.embeddings.create = MagicMock(
            return_value=MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
        )
        mock_openai.return_value = openai_instance

        # Setup Anthropic mock
        anthropic_instance = MagicMock()
        anthropic_instance.messages.create = MagicMock(
            return_value=MagicMock(content=[MagicMock(text='{"match_score": 85}')])
        )
        mock_anthropic.return_value = anthropic_instance

        yield {
            "httpx": mock_httpx,
            "openai": mock_openai,
            "anthropic": mock_anthropic,
        }
