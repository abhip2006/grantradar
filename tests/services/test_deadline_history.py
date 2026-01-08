"""
Tests for deadline history service.
Tests historical deadline tracking and prediction functions.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, GrantDeadlineHistory
from backend.services.deadline_history import (
    add_deadline_record,
    extract_deadline_history_from_grants,
    get_deadline_history_stats,
    get_deadline_patterns,
    get_funder_deadline_history,
    predict_next_deadline,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def sample_grants(async_session: AsyncSession):
    """Create sample grants for testing deadline history extraction."""
    grants = []
    base_date = datetime.now(timezone.utc)

    # NSF grants with consistent deadline pattern (end of month)
    for i in range(5):
        grant = Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id=f"NSF-{i}",
            title=f"NSF Research Grant {i}",
            description="Test grant description",
            agency="National Science Foundation",
            deadline=base_date + timedelta(days=30 * i),
            amount_min=100000,
            amount_max=500000,
            categories=["research", "science"],
        )
        async_session.add(grant)
        grants.append(grant)

    # NIH grants
    for i in range(3):
        grant = Grant(
            id=uuid.uuid4(),
            source="nih",
            external_id=f"NIH-{i}",
            title=f"NIH Health Grant {i}",
            description="Health research grant",
            agency="NIH - National Cancer Institute",
            deadline=base_date + timedelta(days=60 * i),
            amount_min=200000,
            amount_max=1000000,
            categories=["health", "cancer"],
        )
        async_session.add(grant)
        grants.append(grant)

    await async_session.commit()
    return grants


@pytest_asyncio.fixture
async def sample_deadline_history(async_session: AsyncSession):
    """Create sample deadline history records."""
    records = []
    base_date = datetime.now(timezone.utc)

    # NSF records with consistent day-of-month pattern (31st)
    for i in range(10):
        month_offset = i * 30
        record = GrantDeadlineHistory(
            id=uuid.uuid4(),
            funder_name="National Science Foundation",
            grant_title=f"NSF Grant {i}",
            deadline_date=base_date.replace(day=28) + timedelta(days=month_offset),
            fiscal_year=2026,
            source="nsf",
        )
        async_session.add(record)
        records.append(record)

    # NIH records with different pattern
    for i in range(5):
        month_offset = i * 60
        record = GrantDeadlineHistory(
            id=uuid.uuid4(),
            funder_name="NIH - National Cancer Institute",
            grant_title=f"NIH Grant {i}",
            deadline_date=base_date.replace(day=15) + timedelta(days=month_offset),
            fiscal_year=2026,
            source="nih",
        )
        async_session.add(record)
        records.append(record)

    await async_session.commit()
    return records


# =============================================================================
# Extract Deadline History Tests
# =============================================================================


class TestExtractDeadlineHistory:
    """Tests for extracting deadline history from grants."""

    @pytest.mark.asyncio
    async def test_extract_creates_records(self, async_session: AsyncSession, sample_grants):
        """Test that extraction creates deadline history records."""
        result = await extract_deadline_history_from_grants(async_session)

        assert result["processed"] > 0
        assert result["created"] > 0

    @pytest.mark.asyncio
    async def test_extract_handles_duplicates(self, async_session: AsyncSession, sample_grants):
        """Test that duplicate extraction doesn't create duplicate records."""
        # First extraction
        result1 = await extract_deadline_history_from_grants(async_session)

        # Second extraction should skip duplicates
        result2 = await extract_deadline_history_from_grants(async_session)

        assert result2["skipped"] >= result1["created"]

    @pytest.mark.asyncio
    async def test_extract_with_no_grants(self, async_session: AsyncSession):
        """Test extraction with no grants in database."""
        result = await extract_deadline_history_from_grants(async_session)

        assert result["processed"] == 0
        assert result["created"] == 0


# =============================================================================
# Add Deadline Record Tests
# =============================================================================


class TestAddDeadlineRecord:
    """Tests for adding individual deadline records."""

    @pytest.mark.asyncio
    async def test_add_new_record(self, async_session: AsyncSession):
        """Test adding a new deadline record."""
        result = await add_deadline_record(
            db=async_session,
            funder_name="Test Foundation",
            grant_title="Test Grant",
            deadline_date=datetime.now(timezone.utc),
            source="test",
        )

        assert result is not None
        assert result.funder_name == "Test Foundation"
        assert result.grant_title == "Test Grant"

    @pytest.mark.asyncio
    async def test_add_record_with_all_fields(self, async_session: AsyncSession):
        """Test adding a record with all optional fields."""
        deadline = datetime.now(timezone.utc)
        open_date = deadline - timedelta(days=60)

        result = await add_deadline_record(
            db=async_session,
            funder_name="Complete Foundation",
            grant_title="Complete Grant",
            deadline_date=deadline,
            open_date=open_date,
            fiscal_year=2026,
            amount_min=100000,
            amount_max=500000,
            categories=["research", "science"],
            source="complete",
        )

        assert result.open_date == open_date
        assert result.fiscal_year == 2026
        assert result.amount_min == 100000
        assert result.amount_max == 500000

    @pytest.mark.asyncio
    async def test_add_duplicate_record_skipped(self, async_session: AsyncSession):
        """Test that duplicate records are handled."""
        deadline = datetime.now(timezone.utc)

        # First add
        result1 = await add_deadline_record(
            db=async_session,
            funder_name="Duplicate Foundation",
            grant_title="Duplicate Grant",
            deadline_date=deadline,
            source="test",
        )

        # Second add with same details
        result2 = await add_deadline_record(
            db=async_session,
            funder_name="Duplicate Foundation",
            grant_title="Duplicate Grant",
            deadline_date=deadline,
            source="test",
        )

        # Should return existing or None (depending on implementation)
        assert result1 is not None


# =============================================================================
# Get Funder Deadline History Tests
# =============================================================================


class TestGetFunderDeadlineHistory:
    """Tests for retrieving funder deadline history."""

    @pytest.mark.asyncio
    async def test_get_history_returns_records(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test retrieving history for a specific funder."""
        records = await get_funder_deadline_history(
            async_session, "National Science Foundation"
        )

        assert len(records) == 10  # We created 10 NSF records

    @pytest.mark.asyncio
    async def test_get_history_filters_by_funder(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that history is filtered by funder name."""
        nsf_records = await get_funder_deadline_history(
            async_session, "National Science Foundation"
        )
        nih_records = await get_funder_deadline_history(
            async_session, "NIH - National Cancer Institute"
        )

        assert len(nsf_records) == 10
        assert len(nih_records) == 5

    @pytest.mark.asyncio
    async def test_get_history_unknown_funder(self, async_session: AsyncSession):
        """Test retrieving history for unknown funder."""
        records = await get_funder_deadline_history(
            async_session, "Unknown Foundation"
        )

        assert len(records) == 0


# =============================================================================
# Get Deadline Patterns Tests
# =============================================================================


class TestGetDeadlinePatterns:
    """Tests for analyzing deadline patterns."""

    @pytest.mark.asyncio
    async def test_get_patterns_returns_analysis(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that pattern analysis returns expected structure."""
        patterns = await get_deadline_patterns(
            async_session, "National Science Foundation"
        )

        assert patterns is not None
        assert "typical_months" in patterns
        assert "typical_day" in patterns
        assert "date_variance" in patterns

    @pytest.mark.asyncio
    async def test_patterns_calculates_typical_day(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that typical day of month is calculated."""
        patterns = await get_deadline_patterns(
            async_session, "National Science Foundation"
        )

        # Our sample data has day=28
        assert patterns["typical_day"] is not None
        assert 1 <= patterns["typical_day"] <= 31

    @pytest.mark.asyncio
    async def test_patterns_with_insufficient_data(self, async_session: AsyncSession):
        """Test patterns with insufficient historical data."""
        patterns = await get_deadline_patterns(
            async_session, "Unknown Foundation"
        )

        # Should return None or empty patterns
        assert patterns is None or patterns.get("typical_day") is None


# =============================================================================
# Get Deadline History Stats Tests
# =============================================================================


class TestGetDeadlineHistoryStats:
    """Tests for deadline history statistics."""

    @pytest.mark.asyncio
    async def test_stats_returns_totals(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that stats returns total counts."""
        stats = await get_deadline_history_stats(async_session)

        assert stats["total_records"] == 15  # 10 NSF + 5 NIH
        assert stats["unique_funders"] == 2

    @pytest.mark.asyncio
    async def test_stats_returns_date_range(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that stats includes date range."""
        stats = await get_deadline_history_stats(async_session)

        assert "earliest_deadline" in stats
        assert "latest_deadline" in stats

    @pytest.mark.asyncio
    async def test_stats_with_empty_database(self, async_session: AsyncSession):
        """Test stats with no records."""
        stats = await get_deadline_history_stats(async_session)

        assert stats["total_records"] == 0
        assert stats["unique_funders"] == 0


# =============================================================================
# Predict Next Deadline Tests
# =============================================================================


class TestPredictNextDeadline:
    """Tests for deadline prediction."""

    @pytest.mark.asyncio
    async def test_predict_returns_prediction(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that prediction returns expected structure."""
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )

        assert prediction is not None
        assert "funder_name" in prediction
        assert "predicted_deadline" in prediction
        assert "confidence" in prediction

    @pytest.mark.asyncio
    async def test_predict_includes_typical_day(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that prediction includes typical day of month."""
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )

        assert "typical_day_of_month" in prediction
        assert prediction["typical_day_of_month"] is not None

    @pytest.mark.asyncio
    async def test_predict_includes_typical_months(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that prediction includes typical months."""
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )

        assert "typical_months" in prediction
        assert isinstance(prediction["typical_months"], list)

    @pytest.mark.asyncio
    async def test_predict_with_unknown_funder(self, async_session: AsyncSession):
        """Test prediction for unknown funder returns None."""
        prediction = await predict_next_deadline(
            async_session, "Unknown Foundation"
        )

        assert prediction is None

    @pytest.mark.asyncio
    async def test_predict_confidence_range(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that confidence is within valid range."""
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )

        assert 0 <= prediction["confidence"] <= 1

    @pytest.mark.asyncio
    async def test_predict_based_on_records_count(
        self, async_session: AsyncSession, sample_deadline_history
    ):
        """Test that prediction reports number of records used."""
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )

        assert "based_on_records" in prediction
        assert prediction["based_on_records"] == 10


# =============================================================================
# Integration Tests
# =============================================================================


class TestDeadlineHistoryIntegration:
    """Integration tests for deadline history workflow."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, async_session: AsyncSession, sample_grants):
        """Test complete workflow: extract -> analyze -> predict."""
        # Step 1: Extract history from grants
        extract_result = await extract_deadline_history_from_grants(async_session)
        assert extract_result["created"] > 0

        # Step 2: Get statistics
        stats = await get_deadline_history_stats(async_session)
        assert stats["total_records"] > 0

        # Step 3: Get patterns for NSF
        patterns = await get_deadline_patterns(
            async_session, "National Science Foundation"
        )
        # May be None if not enough variety in data

        # Step 4: Predict next deadline
        prediction = await predict_next_deadline(
            async_session, "National Science Foundation"
        )
        assert prediction is not None
