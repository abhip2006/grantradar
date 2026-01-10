"""
Matching agent test fixtures.
Provides mock data and utilities for testing matching components.
"""

import pytest
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4


@pytest.fixture
def sample_grant_data():
    """Sample grant data for matching tests."""
    return {
        "id": uuid4(),
        "title": "Machine Learning for Climate Science",
        "description": "This project develops novel machine learning methods for climate modeling and prediction, focusing on neural network approaches to improve forecast accuracy.",
        "agency": "National Science Foundation",
        "amount_min": 500000,
        "amount_max": 750000,
        "deadline": datetime(2025, 6, 15, tzinfo=timezone.utc),
        "posted_at": datetime(2025, 1, 7, tzinfo=timezone.utc),
        "categories": ["ai_ml", "climate", "computer_science"],
        "eligibility": {
            "applicant_types": ["Universities", "Research Institutions"],
        },
        "embedding": [0.1] * 1536,  # Mock embedding vector
    }


@pytest.fixture
def sample_user_profile():
    """Sample user profile for matching tests."""
    return {
        "user_id": uuid4(),
        "research_areas": ["machine learning", "climate modeling", "deep learning"],
        "methods": ["neural networks", "statistical analysis", "simulation"],
        "past_grants": [
            "NSF Grant: Prior ML Research ($300,000)",
            "DOE Grant: Climate Modeling Project ($250,000)",
        ],
        "institution": "Stanford University",
        "department": "Computer Science",
        "keywords": ["AI", "climate", "prediction"],
        "profile_embedding": [0.15] * 1536,  # Mock embedding vector
    }


@pytest.fixture
def sample_match_result():
    """Sample LLM match result."""
    return {
        "user_id": str(uuid4()),
        "match_score": 85,
        "reasoning": "Strong alignment in research areas. The researcher has relevant experience in machine learning and climate modeling. Prior NSF grant experience is a plus.",
        "key_strengths": [
            "Direct ML expertise",
            "Climate modeling background",
            "Prior NSF funding",
        ],
        "concerns": [
            "No specific neural network climate publications",
        ],
        "predicted_success": 75,
    }


@pytest.fixture
def mock_anthropic_response(sample_match_result):
    """Mock Anthropic API response."""
    import json

    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=json.dumps([sample_match_result]))]
    return mock_response


@pytest.fixture
def mock_openai_embedding():
    """Mock OpenAI embedding response."""
    mock_response = MagicMock()
    mock_response.data = [MagicMock(embedding=[0.1] * 1536)]
    return mock_response


@pytest.fixture
def mock_db_session():
    """Mock SQLAlchemy session for testing."""
    session = MagicMock()
    session.execute = MagicMock()
    session.commit = MagicMock()
    return session


@pytest.fixture
def mock_db_engine(mock_db_session):
    """Mock SQLAlchemy engine for testing."""
    engine = MagicMock()

    # Make Session() return our mock session
    session_context = MagicMock()
    session_context.__enter__ = MagicMock(return_value=mock_db_session)
    session_context.__exit__ = MagicMock(return_value=False)

    return engine


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for matching tests."""
    redis = MagicMock()

    # Stream operations
    redis.xadd = MagicMock(return_value="1234567890-0")
    redis.xreadgroup = MagicMock(return_value=[])
    redis.xack = MagicMock(return_value=1)
    redis.xgroup_create = MagicMock()

    return redis


# =============================================================================
# GrantData fixtures
# =============================================================================


@pytest.fixture
def grant_data_minimal():
    """Minimal GrantData for testing."""
    from agents.matching.models import GrantData

    return GrantData(
        grant_id=uuid4(),
        title="Test Grant",
        description="A test grant description.",
    )


@pytest.fixture
def grant_data_full(sample_grant_data):
    """Full GrantData for testing."""
    from agents.matching.models import GrantData

    return GrantData(
        grant_id=sample_grant_data["id"],
        title=sample_grant_data["title"],
        description=sample_grant_data["description"],
        funding_agency=sample_grant_data["agency"],
        funding_amount=sample_grant_data["amount_max"],
        deadline=sample_grant_data["deadline"],
        eligibility_criteria=sample_grant_data["eligibility"]["applicant_types"],
        categories=sample_grant_data["categories"],
        keywords=sample_grant_data["categories"],
        embedding=sample_grant_data["embedding"],
    )


# =============================================================================
# UserProfile fixtures
# =============================================================================


@pytest.fixture
def user_profile_minimal():
    """Minimal UserProfile for testing."""
    from agents.matching.models import UserProfile

    return UserProfile(
        user_id=uuid4(),
        research_areas=["biology"],
    )


@pytest.fixture
def user_profile_full(sample_user_profile):
    """Full UserProfile for testing."""
    from agents.matching.models import UserProfile

    return UserProfile(
        user_id=sample_user_profile["user_id"],
        research_areas=sample_user_profile["research_areas"],
        methods=sample_user_profile["methods"],
        past_grants=sample_user_profile["past_grants"],
        institution=sample_user_profile["institution"],
        department=sample_user_profile["department"],
        keywords=sample_user_profile["keywords"],
    )


# =============================================================================
# ProfileMatch fixtures
# =============================================================================


@pytest.fixture
def profile_match(user_profile_full):
    """ProfileMatch for testing."""
    from agents.matching.models import ProfileMatch

    return ProfileMatch(
        user_id=user_profile_full.user_id,
        vector_similarity=0.85,
        profile=user_profile_full,
    )


# =============================================================================
# Helper functions
# =============================================================================


def create_mock_db_result(data: dict[str, Any]):
    """Create a mock database result row."""
    result = MagicMock()
    for key, value in data.items():
        setattr(result, key, value)
    return result
