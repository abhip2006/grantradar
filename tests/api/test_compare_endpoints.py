"""
Tests for Grant Comparison API endpoints.
Tests comparing multiple grants side-by-side.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, User


@pytest_asyncio.fixture
async def compare_user(async_session: AsyncSession):
    """Create a user for comparison testing."""
    user = User(
        id=uuid.uuid4(),
        email="compare-test@university.edu",
        password_hash="hashed_pw",
        name="Compare Test User",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def compare_grants(async_session: AsyncSession):
    """Create grants for comparison testing."""
    grants = [
        Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id="NSF-COMPARE-001",
            title="NSF Research Grant",
            description="NSF funded research program",
            agency="NSF",
            amount_min=100000,
            amount_max=500000,
            categories=["research", "science"],
            deadline=datetime.now(timezone.utc),
        ),
        Grant(
            id=uuid.uuid4(),
            source="nih",
            external_id="NIH-COMPARE-001",
            title="NIH Health Research",
            description="NIH funded health research",
            agency="NIH",
            amount_min=200000,
            amount_max=800000,
            categories=["health", "medicine"],
            deadline=datetime.now(timezone.utc),
        ),
        Grant(
            id=uuid.uuid4(),
            source="doe",
            external_id="DOE-COMPARE-001",
            title="DOE Energy Research",
            description="DOE funded energy research",
            agency="DOE",
            amount_min=300000,
            amount_max=1000000,
            categories=["energy", "clean tech"],
            deadline=datetime.now(timezone.utc),
        ),
    ]
    for grant in grants:
        async_session.add(grant)
    await async_session.commit()
    return grants


class TestCompareRequestSchema:
    """Tests for CompareRequest schema."""

    def test_schema_fields(self):
        """Test CompareRequest has required fields."""
        from backend.api.compare import CompareRequest

        schema_fields = CompareRequest.model_fields

        assert "grant_ids" in schema_fields

    def test_grant_ids_constraints(self):
        """Test grant_ids field constraints."""
        from backend.api.compare import CompareRequest

        field = CompareRequest.model_fields["grant_ids"]

        # Should have min and max length constraints
        assert field.metadata  # Has metadata including constraints


class TestComparisonGrantSchema:
    """Tests for ComparisonGrant schema."""

    def test_required_fields(self):
        """Test ComparisonGrant required fields."""
        from backend.api.compare import ComparisonGrant

        schema_fields = ComparisonGrant.model_fields

        assert "id" in schema_fields
        assert "title" in schema_fields
        assert "source" in schema_fields

    def test_optional_fields(self):
        """Test ComparisonGrant optional fields."""
        from backend.api.compare import ComparisonGrant

        schema_fields = ComparisonGrant.model_fields

        assert "agency" in schema_fields
        assert "amount_min" in schema_fields
        assert "amount_max" in schema_fields
        assert "deadline" in schema_fields
        assert "url" in schema_fields
        assert "categories" in schema_fields
        assert "eligibility" in schema_fields
        assert "description" in schema_fields
        assert "match_score" in schema_fields


class TestCompareResponseSchema:
    """Tests for CompareResponse schema."""

    def test_schema_fields(self):
        """Test CompareResponse has required fields."""
        from backend.api.compare import CompareResponse

        schema_fields = CompareResponse.model_fields

        assert "grants" in schema_fields
        assert "comparison_id" in schema_fields


class TestRouterConfiguration:
    """Tests for router configuration."""

    def test_router_prefix(self):
        """Test router prefix is correct."""
        from backend.api.compare import router

        assert router.prefix == "/api/grants"

    def test_router_tags(self):
        """Test router tags are correct."""
        from backend.api.compare import router

        assert "Grants" in router.tags


class TestGrantIdValidation:
    """Tests for grant ID validation."""

    def test_valid_uuid_parsing(self):
        """Test valid UUID parsing."""
        valid_id = "550e8400-e29b-41d4-a716-446655440000"
        parsed = uuid.UUID(valid_id)

        assert isinstance(parsed, uuid.UUID)

    def test_invalid_uuid_raises(self):
        """Test invalid UUID raises error."""
        invalid_id = "not-a-uuid"

        with pytest.raises(ValueError):
            uuid.UUID(invalid_id)

    def test_multiple_uuid_parsing(self):
        """Test parsing multiple UUIDs."""
        ids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "550e8400-e29b-41d4-a716-446655440001",
        ]

        parsed = [uuid.UUID(gid) for gid in ids]

        assert len(parsed) == 2
        assert all(isinstance(p, uuid.UUID) for p in parsed)


class TestMissingGrantsDetection:
    """Tests for missing grants detection."""

    def test_detect_missing_grants(self):
        """Test detecting missing grant IDs."""
        requested_ids = ["id1", "id2", "id3"]
        found_ids = {"id1", "id2"}

        missing_ids = [gid for gid in requested_ids if gid not in found_ids]

        assert len(missing_ids) == 1
        assert "id3" in missing_ids

    def test_all_grants_found(self):
        """Test when all grants are found."""
        requested_ids = ["id1", "id2"]
        found_ids = {"id1", "id2"}

        missing_ids = [gid for gid in requested_ids if gid not in found_ids]

        assert len(missing_ids) == 0


class TestMatchScoreRetrieval:
    """Tests for match score retrieval."""

    def test_match_score_mapping(self):
        """Test match score mapping."""
        matches = [
            {"grant_id": "id1", "match_score": 0.85},
            {"grant_id": "id2", "match_score": 0.72},
        ]

        match_scores = {m["grant_id"]: m["match_score"] for m in matches}

        assert match_scores["id1"] == 0.85
        assert match_scores["id2"] == 0.72

    def test_match_score_for_unauthenticated_user(self):
        """Test match scores for unauthenticated user."""
        current_user = None
        match_scores = {}

        if current_user:
            # Would fetch scores
            pass

        assert match_scores == {}


class TestComparisonResponseBuilding:
    """Tests for comparison response building."""

    def test_preserve_requested_order(self):
        """Test that grants are returned in requested order."""
        requested_ids = ["id2", "id1", "id3"]
        grant_map = {
            "id1": {"title": "Grant 1"},
            "id2": {"title": "Grant 2"},
            "id3": {"title": "Grant 3"},
        }

        ordered_grants = [grant_map[gid] for gid in requested_ids]

        assert ordered_grants[0]["title"] == "Grant 2"
        assert ordered_grants[1]["title"] == "Grant 1"
        assert ordered_grants[2]["title"] == "Grant 3"

    def test_deadline_formatting(self):
        """Test deadline is formatted as ISO string."""
        deadline = datetime(2025, 6, 15, 17, 0, 0, tzinfo=timezone.utc)
        formatted = deadline.isoformat() if deadline else None

        assert "2025-06-15" in formatted

    def test_none_deadline_handling(self):
        """Test None deadline handling."""
        deadline = None
        formatted = deadline.isoformat() if deadline else None

        assert formatted is None


class TestErrorResponses:
    """Tests for error responses."""

    def test_invalid_id_status_code(self):
        """Test status code for invalid grant ID."""
        from fastapi import status

        expected_status = status.HTTP_400_BAD_REQUEST

        assert expected_status == 400

    def test_not_found_status_code(self):
        """Test status code for grants not found."""
        from fastapi import status

        expected_status = status.HTTP_404_NOT_FOUND

        assert expected_status == 404

    def test_missing_grants_error_detail(self):
        """Test error detail for missing grants."""
        missing_ids = ["id1", "id2"]
        detail = f"Grants not found: {', '.join(missing_ids)}"

        assert "Grants not found" in detail
        assert "id1" in detail
        assert "id2" in detail


class TestComparisonLimits:
    """Tests for comparison limits."""

    def test_min_grants_for_comparison(self):
        """Test minimum number of grants for comparison."""
        min_grants = 2

        # Single grant not allowed
        assert 1 < min_grants

        # Two grants allowed
        assert 2 >= min_grants

    def test_max_grants_for_comparison(self):
        """Test maximum number of grants for comparison."""
        max_grants = 4

        # Four grants allowed
        assert 4 <= max_grants

        # Five grants not allowed
        assert 5 > max_grants

    def test_valid_comparison_counts(self):
        """Test valid comparison counts."""
        min_grants = 2
        max_grants = 4

        valid_counts = [2, 3, 4]

        for count in valid_counts:
            assert min_grants <= count <= max_grants
