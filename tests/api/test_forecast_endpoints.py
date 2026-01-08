"""
Tests for forecast API endpoints.
Tests all forecast-related API endpoints including predictions and fiscal calendar.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, GrantDeadlineHistory, LabProfile, User


# Skip marker for tests that require PostgreSQL-specific functions (array_agg)
requires_postgres = pytest.mark.skip(
    reason="Test requires PostgreSQL-specific functions (array_agg) not available in SQLite"
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def sample_grants_for_api(async_session: AsyncSession):
    """Create sample grants for API testing."""
    grants = []
    base_date = datetime.now(timezone.utc)

    # NSF grants with March pattern
    for year in range(2021, 2026):
        grant = Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id=f"NSF-API-{year}",
            title=f"NSF Research Grant {year}",
            description="Test grant for API",
            agency="National Science Foundation",
            deadline=datetime(year, 3, 31, tzinfo=timezone.utc),
            amount_min=100000,
            amount_max=500000,
            categories=["research", "science"],
        )
        async_session.add(grant)
        grants.append(grant)

    # NIH grants
    for year in range(2022, 2026):
        grant = Grant(
            id=uuid.uuid4(),
            source="nih",
            external_id=f"NIH-API-{year}",
            title=f"NIH Health Grant {year}",
            description="Health research grant",
            agency="NIH - National Cancer Institute",
            deadline=datetime(year, 6, 15, tzinfo=timezone.utc),
            amount_min=200000,
            amount_max=1000000,
            categories=["health", "cancer"],
        )
        async_session.add(grant)
        grants.append(grant)

    await async_session.commit()
    return grants


@pytest_asyncio.fixture
async def sample_deadline_history_for_api(async_session: AsyncSession):
    """Create sample deadline history records for API testing."""
    records = []
    base_date = datetime.now(timezone.utc)

    # NSF records
    for i in range(5):
        record = GrantDeadlineHistory(
            id=uuid.uuid4(),
            funder_name="National Science Foundation",
            grant_title=f"NSF Grant {i}",
            deadline_date=base_date.replace(day=28) + timedelta(days=i * 30),
            fiscal_year=2026,
            source="nsf",
        )
        async_session.add(record)
        records.append(record)

    await async_session.commit()
    return records


@pytest_asyncio.fixture
async def api_user(async_session: AsyncSession):
    """Create a user for API authentication testing."""
    user = User(
        id=uuid.uuid4(),
        email="api-test@university.edu",
        password_hash="hashed_pw",
        name="API Test User",
    )
    async_session.add(user)
    await async_session.commit()
    return user


@pytest_asyncio.fixture
async def api_user_with_profile(async_session: AsyncSession, api_user):
    """Create a user with a lab profile for recommendations testing."""
    profile = LabProfile(
        id=uuid.uuid4(),
        user_id=api_user.id,
        lab_name="Test Lab",
        institution="Test University",
        research_areas=["machine learning", "research", "science"],
        methods=["deep learning"],
        career_stage="senior_researcher",
    )
    async_session.add(profile)
    await async_session.commit()
    return api_user


# =============================================================================
# Upcoming Forecasts Endpoint Tests
# =============================================================================


@requires_postgres
class TestUpcomingEndpoint:
    """Tests for /api/forecast/upcoming endpoint."""

    @pytest.mark.asyncio
    async def test_get_upcoming_returns_forecasts(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that upcoming endpoint returns forecast list."""
        from backend.api.forecast import get_upcoming
        from backend.api.deps import get_current_user_optional

        # Mock the dependencies
        mock_user = None

        # Call the endpoint handler directly
        response = await get_upcoming(
            db=async_session,
            user=mock_user,
            lookahead_months=6,
            limit=20,
        )

        assert response is not None
        assert hasattr(response, "forecasts")
        assert hasattr(response, "total")
        assert hasattr(response, "generated_at")
        assert response.lookahead_months == 6

    @pytest.mark.asyncio
    async def test_get_upcoming_respects_limit(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that upcoming endpoint respects limit parameter."""
        from backend.api.forecast import get_upcoming

        response = await get_upcoming(
            db=async_session,
            user=None,
            lookahead_months=12,
            limit=2,
        )

        assert len(response.forecasts) <= 2

    @pytest.mark.asyncio
    async def test_get_upcoming_includes_fiscal_info(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that forecasts include fiscal calendar information."""
        from backend.api.forecast import get_upcoming

        response = await get_upcoming(
            db=async_session,
            user=None,
            lookahead_months=12,
            limit=20,
        )

        if response.forecasts:
            for forecast in response.forecasts:
                assert hasattr(forecast, "fiscal_quarter")
                assert hasattr(forecast, "is_federal_funder")


# =============================================================================
# Seasonal Trends Endpoint Tests
# =============================================================================


@requires_postgres
class TestSeasonalEndpoint:
    """Tests for /api/forecast/seasonal endpoint."""

    @pytest.mark.asyncio
    async def test_get_seasonal_returns_trends(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that seasonal endpoint returns trend data."""
        from backend.api.forecast import get_seasonal

        response = await get_seasonal(
            db=async_session,
            user=None,
        )

        assert response is not None
        assert hasattr(response, "trends")
        assert len(response.trends) == 12  # All 12 months
        assert hasattr(response, "year_total")
        assert hasattr(response, "peak_months")

    @pytest.mark.asyncio
    async def test_seasonal_months_in_order(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that seasonal months are returned in order."""
        from backend.api.forecast import get_seasonal

        response = await get_seasonal(
            db=async_session,
            user=None,
        )

        months = [t.month for t in response.trends]
        assert months == list(range(1, 13))

    @pytest.mark.asyncio
    async def test_seasonal_includes_month_names(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that seasonal data includes month names."""
        from backend.api.forecast import get_seasonal

        response = await get_seasonal(
            db=async_session,
            user=None,
        )

        expected_names = [
            "January", "February", "March", "April", "May", "June",
            "July", "August", "September", "October", "November", "December"
        ]

        for i, trend in enumerate(response.trends):
            assert trend.month_name == expected_names[i]


# =============================================================================
# Deadline History Stats Endpoint Tests
# =============================================================================


class TestHistoryStatsEndpoint:
    """Tests for /api/forecast/history/stats endpoint."""

    @pytest.mark.asyncio
    async def test_get_history_stats(
        self, async_session: AsyncSession, sample_deadline_history_for_api
    ):
        """Test that history stats endpoint returns statistics."""
        from backend.api.forecast import get_history_stats

        response = await get_history_stats(db=async_session)

        assert response is not None
        assert hasattr(response, "total_records")
        assert hasattr(response, "unique_funders")
        assert hasattr(response, "generated_at")

    @pytest.mark.asyncio
    async def test_history_stats_with_empty_database(
        self, async_session: AsyncSession
    ):
        """Test stats endpoint with no history records."""
        from backend.api.forecast import get_history_stats

        response = await get_history_stats(db=async_session)

        assert response.total_records == 0
        assert response.unique_funders == 0


# =============================================================================
# Funder History Endpoint Tests
# =============================================================================


class TestFunderHistoryEndpoint:
    """Tests for /api/forecast/history/{funder_name} endpoint."""

    @pytest.mark.asyncio
    async def test_get_funder_history_returns_records(
        self, async_session: AsyncSession, sample_deadline_history_for_api
    ):
        """Test that funder history endpoint returns records."""
        from backend.api.forecast import get_funder_history

        response = await get_funder_history(
            db=async_session,
            funder_name="National Science Foundation",
        )

        assert response is not None
        assert hasattr(response, "records")
        assert hasattr(response, "total")
        assert response.funder_name == "National Science Foundation"
        assert len(response.records) == 5

    @pytest.mark.asyncio
    async def test_get_funder_history_unknown_funder(
        self, async_session: AsyncSession
    ):
        """Test funder history with unknown funder returns empty."""
        from backend.api.forecast import get_funder_history

        response = await get_funder_history(
            db=async_session,
            funder_name="Unknown Foundation",
        )

        assert response.total == 0
        assert len(response.records) == 0


# =============================================================================
# Funder Prediction Endpoint Tests
# =============================================================================


class TestFunderPredictionEndpoint:
    """Tests for /api/forecast/predict/{funder_name} endpoint."""

    @pytest.mark.asyncio
    async def test_get_funder_prediction_returns_prediction(
        self, async_session: AsyncSession, sample_deadline_history_for_api
    ):
        """Test that prediction endpoint returns a prediction."""
        from backend.api.forecast import get_funder_prediction

        response = await get_funder_prediction(
            db=async_session,
            funder_name="National Science Foundation",
        )

        assert response is not None
        assert hasattr(response, "prediction")
        assert response.prediction.funder_name == "National Science Foundation"
        assert hasattr(response.prediction, "predicted_deadline")
        assert hasattr(response.prediction, "confidence")

    @pytest.mark.asyncio
    async def test_get_funder_prediction_unknown_funder_raises(
        self, async_session: AsyncSession
    ):
        """Test that prediction for unknown funder raises 404."""
        from fastapi import HTTPException
        from backend.api.forecast import get_funder_prediction

        with pytest.raises(HTTPException) as exc_info:
            await get_funder_prediction(
                db=async_session,
                funder_name="Unknown Foundation XYZ",
            )

        assert exc_info.value.status_code == 404


# =============================================================================
# ML Prediction Endpoint Tests
# =============================================================================


class TestMLPredictionEndpoint:
    """Tests for /api/forecast/ml/{funder_name} endpoint."""

    @pytest.mark.asyncio
    async def test_get_ml_prediction_returns_result(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that ML prediction endpoint returns a result."""
        from backend.api.forecast import get_ml_prediction

        response = await get_ml_prediction(
            db=async_session,
            funder_name="National Science Foundation",
        )

        assert response is not None
        assert hasattr(response, "prediction")
        assert hasattr(response, "model_trained")
        assert response.prediction.funder_name == "National Science Foundation"
        assert hasattr(response.prediction, "method")
        assert response.prediction.method in ["ml", "rule_based"]

    @pytest.mark.asyncio
    async def test_ml_prediction_includes_uncertainty(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that ML prediction includes uncertainty information."""
        from backend.api.forecast import get_ml_prediction

        response = await get_ml_prediction(
            db=async_session,
            funder_name="National Science Foundation",
        )

        assert hasattr(response.prediction, "uncertainty_days")
        assert response.prediction.uncertainty_days >= 0


# =============================================================================
# Fiscal Calendar Endpoint Tests
# =============================================================================


class TestFiscalCalendarEndpoint:
    """Tests for /api/forecast/fiscal-calendar endpoint."""

    @pytest.mark.asyncio
    async def test_get_fiscal_calendar_default_date(self):
        """Test fiscal calendar with default date (today)."""
        from backend.api.forecast import get_fiscal_calendar

        response = await get_fiscal_calendar(for_date=None)

        assert response is not None
        assert hasattr(response, "fiscal_info")
        assert response.for_date == date.today()
        assert 1 <= response.fiscal_info.current_fiscal_quarter <= 4
        assert response.fiscal_info.current_fiscal_year >= 2024

    @pytest.mark.asyncio
    async def test_get_fiscal_calendar_specific_date(self):
        """Test fiscal calendar with specific date."""
        from backend.api.forecast import get_fiscal_calendar

        # October 15, 2025 is FY2026 Q1
        test_date = date(2025, 10, 15)
        response = await get_fiscal_calendar(for_date=test_date)

        assert response.for_date == test_date
        assert response.fiscal_info.current_fiscal_year == 2026
        assert response.fiscal_info.current_fiscal_quarter == 1

    @pytest.mark.asyncio
    async def test_fiscal_calendar_includes_quarter_end(self):
        """Test that fiscal calendar includes quarter end information."""
        from backend.api.forecast import get_fiscal_calendar

        response = await get_fiscal_calendar(for_date=None)

        assert hasattr(response.fiscal_info, "quarter_end_date")
        assert hasattr(response.fiscal_info, "days_until_quarter_end")
        assert response.fiscal_info.days_until_quarter_end >= 0

    @pytest.mark.asyncio
    async def test_fiscal_calendar_year_end_detection(self):
        """Test fiscal year end period detection."""
        from backend.api.forecast import get_fiscal_calendar

        # September is fiscal year end period
        test_date = date(2026, 9, 15)
        response = await get_fiscal_calendar(for_date=test_date)

        assert response.fiscal_info.is_year_end_period is True
        assert response.fiscal_info.is_year_start_period is False

    @pytest.mark.asyncio
    async def test_fiscal_calendar_year_start_detection(self):
        """Test fiscal year start period detection."""
        from backend.api.forecast import get_fiscal_calendar

        # October is fiscal year start period
        test_date = date(2025, 10, 15)
        response = await get_fiscal_calendar(for_date=test_date)

        assert response.fiscal_info.is_year_start_period is True
        assert response.fiscal_info.is_year_end_period is False


# =============================================================================
# Federal Funder Check Endpoint Tests
# =============================================================================


class TestFederalFunderEndpoint:
    """Tests for /api/forecast/is-federal/{funder_name} endpoint."""

    @pytest.mark.asyncio
    async def test_check_federal_funder_nsf(self):
        """Test federal funder check for NSF."""
        from backend.api.forecast import check_federal_funder

        response = await check_federal_funder(funder_name="NSF")

        assert response["funder_name"] == "NSF"
        assert response["is_federal"] is True
        assert "fiscal year" in response["note"].lower()

    @pytest.mark.asyncio
    async def test_check_federal_funder_nih(self):
        """Test federal funder check for NIH."""
        from backend.api.forecast import check_federal_funder

        response = await check_federal_funder(funder_name="NIH")

        assert response["is_federal"] is True

    @pytest.mark.asyncio
    async def test_check_federal_funder_full_name(self):
        """Test federal funder check with full agency name."""
        from backend.api.forecast import check_federal_funder

        response = await check_federal_funder(
            funder_name="National Science Foundation"
        )

        assert response["is_federal"] is True

    @pytest.mark.asyncio
    async def test_check_non_federal_funder(self):
        """Test federal funder check for non-federal funder."""
        from backend.api.forecast import check_federal_funder

        response = await check_federal_funder(funder_name="Ford Foundation")

        assert response["is_federal"] is False
        assert response["note"] is None

    @pytest.mark.asyncio
    async def test_check_federal_funder_case_insensitive(self):
        """Test that federal funder check is case insensitive."""
        from backend.api.forecast import check_federal_funder

        response1 = await check_federal_funder(funder_name="nsf")
        response2 = await check_federal_funder(funder_name="NSF")
        response3 = await check_federal_funder(funder_name="Nsf")

        assert response1["is_federal"] == response2["is_federal"] == response3["is_federal"]


# =============================================================================
# Recommendations Endpoint Tests
# =============================================================================


@requires_postgres
class TestRecommendationsEndpoint:
    """Tests for /api/forecast/recommendations endpoint."""

    @pytest.mark.asyncio
    async def test_get_recommendations_returns_list(
        self, async_session: AsyncSession, sample_grants_for_api, api_user_with_profile
    ):
        """Test that recommendations endpoint returns a list."""
        from backend.api.forecast import get_recommendation_list

        response = await get_recommendation_list(
            db=async_session,
            user=api_user_with_profile,
            limit=10,
        )

        assert response is not None
        assert hasattr(response, "recommendations")
        assert hasattr(response, "total")
        assert hasattr(response, "profile_complete")

    @pytest.mark.asyncio
    async def test_recommendations_include_match_info(
        self, async_session: AsyncSession, sample_grants_for_api, api_user_with_profile
    ):
        """Test that recommendations include match information."""
        from backend.api.forecast import get_recommendation_list

        response = await get_recommendation_list(
            db=async_session,
            user=api_user_with_profile,
            limit=10,
        )

        if response.recommendations:
            for rec in response.recommendations:
                assert hasattr(rec, "match_score")
                assert hasattr(rec, "match_reasons")
                assert hasattr(rec, "profile_overlap")

    @pytest.mark.asyncio
    async def test_recommendations_respects_limit(
        self, async_session: AsyncSession, sample_grants_for_api, api_user_with_profile
    ):
        """Test that recommendations respect limit parameter."""
        from backend.api.forecast import get_recommendation_list

        response = await get_recommendation_list(
            db=async_session,
            user=api_user_with_profile,
            limit=2,
        )

        assert len(response.recommendations) <= 2


# =============================================================================
# Integration Tests
# =============================================================================


@requires_postgres
class TestForecastAPIIntegration:
    """Integration tests for forecast API endpoints."""

    @pytest.mark.asyncio
    async def test_forecast_api_workflow(
        self, async_session: AsyncSession, sample_grants_for_api, sample_deadline_history_for_api
    ):
        """Test complete forecast API workflow."""
        from backend.api.forecast import (
            get_upcoming,
            get_seasonal,
            get_history_stats,
            get_fiscal_calendar,
        )

        # Step 1: Get upcoming forecasts
        upcoming = await get_upcoming(
            db=async_session,
            user=None,
            lookahead_months=12,
            limit=20,
        )
        assert upcoming.total >= 0

        # Step 2: Get seasonal trends
        seasonal = await get_seasonal(
            db=async_session,
            user=None,
        )
        assert len(seasonal.trends) == 12

        # Step 3: Get history stats
        stats = await get_history_stats(db=async_session)
        assert stats.total_records >= 0

        # Step 4: Get fiscal calendar
        fiscal = await get_fiscal_calendar(for_date=None)
        assert fiscal.fiscal_info.current_fiscal_year >= 2024

    @pytest.mark.asyncio
    async def test_forecast_data_consistency(
        self, async_session: AsyncSession, sample_grants_for_api
    ):
        """Test that forecast data is internally consistent."""
        from backend.api.forecast import get_upcoming

        response = await get_upcoming(
            db=async_session,
            user=None,
            lookahead_months=12,
            limit=50,
        )

        # Verify forecasts are sorted by date
        if len(response.forecasts) > 1:
            dates = [f.predicted_open_date for f in response.forecasts]
            assert dates == sorted(dates)

        # Verify confidence values are valid
        for forecast in response.forecasts:
            assert 0 <= forecast.confidence <= 1

        # Verify fiscal quarters are valid
        for forecast in response.forecasts:
            if forecast.fiscal_quarter is not None:
                assert 1 <= forecast.fiscal_quarter <= 4
