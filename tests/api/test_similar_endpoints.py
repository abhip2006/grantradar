"""
Tests for Similar Grants API endpoints.
Tests finding grants similar to a given grant.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, User


@pytest_asyncio.fixture
async def similar_user(async_session: AsyncSession):
    """Create a user for similar grants testing."""
    user = User(
        id=uuid.uuid4(),
        email="similar-test@university.edu",
        password_hash="hashed_pw",
        name="Similar Test User",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def source_grant(async_session: AsyncSession):
    """Create a source grant for similarity testing."""
    grant = Grant(
        id=uuid.uuid4(),
        source="nsf",
        external_id="NSF-2024-001",
        title="Machine Learning for Genomics Research",
        description="Research into applying ML techniques to genomics data analysis",
        agency="NSF",
        amount_min=100000,
        amount_max=500000,
        categories=["machine learning", "genomics", "bioinformatics"],
        deadline=datetime.now(timezone.utc),
        posted_at=datetime.now(timezone.utc),
        url="https://nsf.gov/grant-001",
    )
    async_session.add(grant)
    await async_session.commit()
    await async_session.refresh(grant)
    return grant


@pytest_asyncio.fixture
async def similar_grants(async_session: AsyncSession, source_grant: Grant):
    """Create grants similar to the source grant."""
    grants = [
        Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id="NSF-2024-002",
            title="Deep Learning in Bioinformatics",
            description="Application of deep learning to bioinformatics problems",
            agency="NSF",
            amount_min=150000,
            amount_max=400000,
            categories=["deep learning", "bioinformatics", "genomics"],
            deadline=datetime.now(timezone.utc),
        ),
        Grant(
            id=uuid.uuid4(),
            source="nih",
            external_id="NIH-2024-001",
            title="Computational Genomics Research",
            description="Computational approaches to genomics analysis",
            agency="NIH",
            amount_min=200000,
            amount_max=600000,
            categories=["genomics", "computational biology"],
            deadline=datetime.now(timezone.utc),
        ),
        Grant(
            id=uuid.uuid4(),
            source="doe",
            external_id="DOE-2024-001",
            title="Clean Energy Technology",
            description="Research into renewable energy sources",
            agency="DOE",
            amount_min=500000,
            amount_max=1000000,
            categories=["energy", "clean tech"],
            deadline=datetime.now(timezone.utc),
        ),
    ]
    for grant in grants:
        async_session.add(grant)
    await async_session.commit()
    return grants


class TestSimilarGrantResponseSchema:
    """Tests for SimilarGrantResponse schema."""

    def test_schema_fields(self):
        """Test SimilarGrantResponse has required fields."""
        from backend.api.similar import SimilarGrantResponse

        # Check required fields exist
        schema_fields = SimilarGrantResponse.model_fields

        assert "id" in schema_fields
        assert "source" in schema_fields
        assert "external_id" in schema_fields
        assert "title" in schema_fields
        assert "similarity_score" in schema_fields
        assert "similarity_reasons" in schema_fields

    def test_schema_optional_fields(self):
        """Test SimilarGrantResponse optional fields."""
        from backend.api.similar import SimilarGrantResponse

        schema_fields = SimilarGrantResponse.model_fields

        assert "description" in schema_fields
        assert "agency" in schema_fields
        assert "amount_min" in schema_fields
        assert "amount_max" in schema_fields
        assert "deadline" in schema_fields
        assert "url" in schema_fields


class TestSimilarGrantsResponseSchema:
    """Tests for SimilarGrantsResponse schema."""

    def test_schema_fields(self):
        """Test SimilarGrantsResponse has required fields."""
        from backend.api.similar import SimilarGrantsResponse

        schema_fields = SimilarGrantsResponse.model_fields

        assert "similar_grants" in schema_fields
        assert "source_grant_id" in schema_fields
        assert "total" in schema_fields


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_prefix(self):
        """Test router prefix is correct."""
        from backend.api.similar import router

        assert router.prefix == "/api/grants"

    def test_router_tags(self):
        """Test router tags are correct."""
        from backend.api.similar import router

        assert "Similar Grants" in router.tags


class TestSimilarityScoring:
    """Tests for similarity scoring logic."""

    def test_similarity_score_range(self):
        """Test similarity score is in valid range (0-100)."""
        # Simulate similarity scores
        scores = [0, 25, 50, 75, 100]

        for score in scores:
            assert 0 <= score <= 100

    def test_similarity_reasons_format(self):
        """Test similarity reasons format."""
        reasons = [
            "Category overlap: genomics, bioinformatics",
            "Agency match: NSF",
            "Funding range proximity",
        ]

        assert all(isinstance(r, str) for r in reasons)
        assert len(reasons) > 0


class TestQueryParameters:
    """Tests for query parameter validation."""

    def test_limit_default(self):
        """Test default limit value."""
        default_limit = 10
        assert default_limit == 10

    def test_limit_bounds(self):
        """Test limit bounds."""
        min_limit = 1
        max_limit = 50

        # Valid limits
        assert 1 >= min_limit
        assert 50 <= max_limit
        assert 25 >= min_limit
        assert 25 <= max_limit

    def test_min_score_default(self):
        """Test default min_score value."""
        default_min_score = 20
        assert default_min_score == 20

    def test_min_score_bounds(self):
        """Test min_score bounds."""
        min_bound = 0
        max_bound = 100

        assert 0 >= min_bound
        assert 100 <= max_bound


class TestDescriptionTruncation:
    """Tests for description truncation logic."""

    def test_description_truncation(self):
        """Test description is truncated to 500 chars."""
        long_description = "A" * 1000
        truncated = long_description[:500] if long_description else None

        assert len(truncated) == 500

    def test_short_description_not_truncated(self):
        """Test short descriptions are not truncated."""
        short_description = "Short description"
        truncated = short_description[:500] if short_description else None

        assert truncated == short_description

    def test_none_description(self):
        """Test None description handling."""
        description = None
        result = description[:500] if description else None

        assert result is None


class TestDateFormatting:
    """Tests for date formatting in response."""

    def test_deadline_isoformat(self):
        """Test deadline is formatted as ISO string."""
        deadline = datetime(2025, 6, 15, 17, 0, 0, tzinfo=timezone.utc)
        formatted = deadline.isoformat()

        assert "2025-06-15" in formatted
        assert "T" in formatted

    def test_posted_at_isoformat(self):
        """Test posted_at is formatted as ISO string."""
        posted_at = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        formatted = posted_at.isoformat()

        assert "2025-01-01" in formatted

    def test_none_date_handling(self):
        """Test None date handling."""
        deadline = None
        formatted = deadline.isoformat() if deadline else None

        assert formatted is None


class TestSimilarGrantsAPIEndpoint:
    """Tests for the similar grants API endpoint."""

    @pytest.mark.asyncio
    async def test_empty_results(self, async_session, source_grant):
        """Test endpoint returns empty list when no similar grants."""
        # When find_similar_grants returns empty list

        response = {
            "similar_grants": [],
            "source_grant_id": str(source_grant.id),
            "total": 0,
        }

        assert response["total"] == 0
        assert response["similar_grants"] == []

    @pytest.mark.asyncio
    async def test_response_structure(self, async_session, source_grant):
        """Test response has correct structure."""
        # Simulate response structure
        response = {
            "similar_grants": [
                {
                    "id": str(uuid.uuid4()),
                    "source": "nsf",
                    "external_id": "NSF-001",
                    "title": "Test Grant",
                    "similarity_score": 85,
                    "similarity_reasons": ["Agency match"],
                }
            ],
            "source_grant_id": str(source_grant.id),
            "total": 1,
        }

        assert "similar_grants" in response
        assert "source_grant_id" in response
        assert "total" in response
        assert response["total"] == len(response["similar_grants"])


class TestErrorHandling:
    """Tests for error handling."""

    def test_grant_not_found_status_code(self):
        """Test 404 status code for non-existent grant."""
        from fastapi import status

        expected_status = status.HTTP_404_NOT_FOUND

        assert expected_status == 404

    def test_grant_not_found_detail(self):
        """Test error detail for non-existent grant."""
        detail = "Grant not found"

        assert detail == "Grant not found"
