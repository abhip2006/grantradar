"""
Tests for forecast service.
Tests grant forecasting based on historical patterns.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant, LabProfile, User
from backend.services.forecast import (
    MONTH_NAMES,
    ForecastResult,
    FunderPattern,
    RecommendationResult,
    SeasonalTrendResult,
    analyze_funder_patterns,
    calculate_confidence,
    calculate_recurrence_pattern,
    calculate_typical_day,
    get_recommendations,
    get_seasonal_trends,
    get_upcoming_forecasts,
    predict_next_opening,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def sample_user(async_session: AsyncSession):
    """Create a sample user for testing."""
    user = User(
        id=uuid.uuid4(),
        email="researcher@university.edu",
        hashed_password="hashed_pw",
    )
    async_session.add(user)
    await async_session.commit()
    return user


@pytest_asyncio.fixture
async def sample_profile(async_session: AsyncSession, sample_user):
    """Create a sample lab profile for testing."""
    profile = LabProfile(
        id=uuid.uuid4(),
        user_id=sample_user.id,
        lab_name="AI Research Lab",
        institution="Test University",
        research_areas=["machine learning", "computer vision", "NLP"],
        methods=["deep learning", "neural networks"],
        career_stage="senior_researcher",
    )
    async_session.add(profile)
    await async_session.commit()
    return profile


@pytest_asyncio.fixture
async def sample_grants_for_forecast(async_session: AsyncSession):
    """Create sample grants with various deadline patterns."""
    grants = []

    # NSF grants with March deadline pattern (5 years)
    for year in range(2021, 2026):
        grant = Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id=f"NSF-MARCH-{year}",
            title=f"NSF Research Grant {year}",
            description="Test grant",
            agency="National Science Foundation",
            deadline=datetime(year, 3, 31, tzinfo=timezone.utc),
            amount_min=100000,
            amount_max=500000,
            categories=["machine learning", "research"],
        )
        async_session.add(grant)
        grants.append(grant)

    # NIH grants with bi-annual pattern (Feb and Oct)
    for year in range(2022, 2026):
        for month, day in [(2, 15), (10, 5)]:
            grant = Grant(
                id=uuid.uuid4(),
                source="nih",
                external_id=f"NIH-{year}-{month}",
                title=f"NIH Health Grant {year}-{month}",
                description="Health research",
                agency="NIH - National Cancer Institute",
                deadline=datetime(year, month, day, tzinfo=timezone.utc),
                amount_min=200000,
                amount_max=1000000,
                categories=["health", "cancer research"],
            )
            async_session.add(grant)
            grants.append(grant)

    # DOE grants with quarterly pattern
    for year in range(2023, 2026):
        for month in [3, 6, 9, 12]:
            grant = Grant(
                id=uuid.uuid4(),
                source="doe",
                external_id=f"DOE-{year}-Q{month//3}",
                title=f"DOE Energy Grant Q{month//3} {year}",
                description="Energy research",
                agency="Department of Energy",
                deadline=datetime(year, month, 15, tzinfo=timezone.utc),
                amount_min=150000,
                amount_max=750000,
                categories=["energy", "sustainability"],
            )
            async_session.add(grant)
            grants.append(grant)

    # Small foundation with single grant (should be filtered out with min_grants=2)
    grant = Grant(
        id=uuid.uuid4(),
        source="private",
        external_id="SMALL-001",
        title="Small Foundation Grant",
        description="Single grant",
        agency="Small Foundation",
        deadline=datetime.now(timezone.utc),
        amount_min=10000,
        amount_max=50000,
        categories=["general"],
    )
    async_session.add(grant)
    grants.append(grant)

    await async_session.commit()
    return grants


# =============================================================================
# Calculate Recurrence Pattern Tests
# =============================================================================


class TestCalculateRecurrencePattern:
    """Tests for recurrence pattern calculation."""

    def test_empty_months_returns_unknown(self):
        """Test that empty months returns unknown."""
        assert calculate_recurrence_pattern([]) == "unknown"

    def test_annual_pattern(self):
        """Test annual pattern detection (1 unique month)."""
        months = [3, 3, 3, 3]  # All March
        assert calculate_recurrence_pattern(months) == "annual"

    def test_biannual_pattern(self):
        """Test biannual pattern detection (2-3 unique months)."""
        months = [3, 9, 3, 9]  # March and September
        assert calculate_recurrence_pattern(months) == "biannual"

    def test_quarterly_pattern(self):
        """Test quarterly pattern detection (4-9 unique months)."""
        months = [3, 6, 9, 12, 3, 6, 9, 12]  # All quarters
        assert calculate_recurrence_pattern(months) == "quarterly"

    def test_monthly_pattern(self):
        """Test monthly pattern detection (10+ unique months)."""
        months = list(range(1, 12))  # 11 unique months
        assert calculate_recurrence_pattern(months) == "monthly"


# =============================================================================
# Calculate Confidence Tests
# =============================================================================


class TestCalculateConfidence:
    """Tests for confidence score calculation."""

    def test_low_confidence_with_minimal_data(self):
        """Test low confidence with minimal data."""
        confidence = calculate_confidence(
            grant_count=1,
            years_span=1,
            consistency=0.0,
        )
        assert confidence < 0.5

    def test_high_confidence_with_good_data(self):
        """Test high confidence with good historical data."""
        confidence = calculate_confidence(
            grant_count=10,
            years_span=3,
            consistency=0.9,
        )
        assert confidence > 0.7

    def test_confidence_capped_at_one(self):
        """Test that confidence is capped at 1.0."""
        confidence = calculate_confidence(
            grant_count=100,
            years_span=10,
            consistency=1.0,
        )
        assert confidence <= 1.0

    def test_confidence_rounded(self):
        """Test that confidence is rounded to 2 decimal places."""
        confidence = calculate_confidence(
            grant_count=5,
            years_span=2,
            consistency=0.5,
        )
        assert confidence == round(confidence, 2)


# =============================================================================
# Calculate Typical Day Tests
# =============================================================================


class TestCalculateTypicalDay:
    """Tests for typical day of month calculation."""

    def test_empty_dates_returns_defaults(self):
        """Test that empty dates returns day 1 with 0 confidence."""
        day, confidence = calculate_typical_day([], 3)
        assert day == 1
        assert confidence == 0.0

    def test_single_date_medium_confidence(self):
        """Test that single date returns medium confidence."""
        dates = [date(2024, 3, 15)]
        day, confidence = calculate_typical_day(dates, 3)
        assert day == 15
        assert confidence == 0.5

    def test_consistent_dates_high_confidence(self):
        """Test that consistent dates return high confidence."""
        dates = [
            date(2024, 3, 15),
            date(2023, 3, 15),
            date(2022, 3, 15),
        ]
        day, confidence = calculate_typical_day(dates, 3)
        assert day == 15
        assert confidence > 0.9  # Perfect consistency

    def test_variable_dates_lower_confidence(self):
        """Test that variable dates return lower confidence."""
        dates = [
            date(2024, 3, 1),
            date(2023, 3, 15),
            date(2022, 3, 28),
        ]
        day, confidence = calculate_typical_day(dates, 3)
        assert confidence < 0.7

    def test_filters_by_target_month(self):
        """Test that calculation filters by target month when available."""
        dates = [
            date(2024, 3, 28),  # March
            date(2024, 6, 15),  # June
            date(2023, 3, 28),  # March
        ]
        day, confidence = calculate_typical_day(dates, 3)
        # Should focus on March dates (28 and 28) - clamped to 28 max
        assert day == 28

    def test_day_clamped_to_valid_range(self):
        """Test that predicted day is clamped to valid range."""
        # Day 31 should be clamped to 28 (safe max)
        dates = [date(2024, 3, 31), date(2023, 3, 31)]
        day, _ = calculate_typical_day(dates, 3)
        assert 1 <= day <= 28  # Safe max is 28


# =============================================================================
# Predict Next Opening Tests
# =============================================================================


class TestPredictNextOpening:
    """Tests for next opening prediction."""

    def test_no_pattern_uses_last_deadline(self):
        """Test prediction with no pattern uses last deadline."""
        last = date(2024, 6, 15)
        predicted, month, confidence = predict_next_opening(
            typical_months=[],
            historical_dates=[last],
            last_deadline=last,
        )

        # Should predict same month next occurrence
        assert predicted >= date.today()
        assert month == 6

    def test_no_pattern_no_deadline_defaults(self):
        """Test prediction with no pattern or deadline defaults to 90 days."""
        predicted, month, confidence = predict_next_opening(
            typical_months=[],
            historical_dates=[],
            last_deadline=None,
        )

        today = date.today()
        expected_future = today + timedelta(days=90)
        assert predicted.year == expected_future.year
        assert predicted.month == expected_future.month
        assert confidence == 0.0

    def test_finds_next_month_in_pattern(self):
        """Test that prediction finds next month in pattern."""
        today = date.today()
        # Pattern of March and September
        typical = [3, 9]
        historical = [
            date(2024, 3, 31),
            date(2023, 9, 30),
        ]

        predicted, month, confidence = predict_next_opening(
            typical_months=typical,
            historical_dates=historical,
            last_deadline=historical[0],
        )

        assert predicted > today
        assert month in typical

    def test_skips_past_months(self):
        """Test that prediction skips past months in current year."""
        predicted, month, _ = predict_next_opening(
            typical_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            historical_dates=[date(2024, 1, 15)],
            last_deadline=date(2024, 1, 15),
        )

        assert predicted > date.today()


# =============================================================================
# FunderPattern Dataclass Tests
# =============================================================================


class TestFunderPattern:
    """Tests for FunderPattern dataclass."""

    def test_create_with_required_fields(self):
        """Test creating pattern with required fields."""
        pattern = FunderPattern(
            funder_name="Test Foundation",
            typical_months=[3, 9],
            avg_amount_min=100000,
            avg_amount_max=500000,
            categories=["research"],
            grant_count=5,
            last_deadline=date.today(),
            source="test",
            sample_title="Test Grant",
        )

        assert pattern.funder_name == "Test Foundation"
        assert pattern.typical_months == [3, 9]
        assert pattern.historical_dates == []  # Default empty list

    def test_create_with_historical_dates(self):
        """Test creating pattern with historical dates."""
        historical = [date(2024, 3, 31), date(2023, 3, 31)]
        pattern = FunderPattern(
            funder_name="Test Foundation",
            typical_months=[3],
            avg_amount_min=None,
            avg_amount_max=None,
            categories=[],
            grant_count=2,
            last_deadline=date(2024, 3, 31),
            source="test",
            sample_title=None,
            historical_dates=historical,
        )

        assert pattern.historical_dates == historical


# =============================================================================
# ForecastResult Dataclass Tests
# =============================================================================


class TestForecastResult:
    """Tests for ForecastResult dataclass."""

    def test_create_with_all_fields(self):
        """Test creating forecast result with all fields."""
        result = ForecastResult(
            funder_name="NSF",
            predicted_open_date=date.today() + timedelta(days=90),
            confidence=0.85,
            historical_amount_min=100000,
            historical_amount_max=500000,
            focus_areas=["AI", "ML"],
            title="AI Research Grant",
            historical_deadline_month=3,
            recurrence_pattern="annual",
            last_seen_date=date.today() - timedelta(days=30),
            source="nsf",
            fiscal_quarter=2,
            is_federal_funder=True,
        )

        assert result.funder_name == "NSF"
        assert result.is_federal_funder is True
        assert result.fiscal_quarter == 2

    def test_default_values(self):
        """Test default values in forecast result."""
        result = ForecastResult(
            funder_name="Test",
            predicted_open_date=date.today(),
            confidence=0.5,
            historical_amount_min=None,
            historical_amount_max=None,
            focus_areas=[],
            title=None,
            historical_deadline_month=None,
            recurrence_pattern="unknown",
            last_seen_date=None,
            source=None,
        )

        assert result.grant_id is None
        assert result.fiscal_quarter is None
        assert result.is_federal_funder is False


# =============================================================================
# Analyze Funder Patterns Tests
# =============================================================================


class TestAnalyzeFunderPatterns:
    """Tests for analyzing funder patterns."""

    @pytest.mark.asyncio
    async def test_returns_list_of_patterns(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that analysis returns list of patterns."""
        patterns = await analyze_funder_patterns(async_session)

        assert isinstance(patterns, list)
        assert len(patterns) > 0
        assert all(isinstance(p, FunderPattern) for p in patterns)

    @pytest.mark.asyncio
    async def test_filters_by_min_grants(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that patterns are filtered by minimum grants."""
        patterns = await analyze_funder_patterns(async_session, min_grants=5)

        for pattern in patterns:
            assert pattern.grant_count >= 5

    @pytest.mark.asyncio
    async def test_extracts_typical_months(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that typical months are extracted."""
        patterns = await analyze_funder_patterns(async_session)

        for pattern in patterns:
            assert isinstance(pattern.typical_months, list)
            for month in pattern.typical_months:
                assert 1 <= month <= 12

    @pytest.mark.asyncio
    async def test_extracts_historical_dates(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that historical dates are extracted."""
        patterns = await analyze_funder_patterns(async_session)

        for pattern in patterns:
            assert isinstance(pattern.historical_dates, list)
            for d in pattern.historical_dates:
                assert isinstance(d, date)


# =============================================================================
# Get Upcoming Forecasts Tests
# =============================================================================


class TestGetUpcomingForecasts:
    """Tests for getting upcoming forecasts."""

    @pytest.mark.asyncio
    async def test_returns_forecast_list(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that forecasts are returned as a list."""
        forecasts = await get_upcoming_forecasts(async_session)

        assert isinstance(forecasts, list)
        assert all(isinstance(f, ForecastResult) for f in forecasts)

    @pytest.mark.asyncio
    async def test_forecasts_sorted_by_date(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that forecasts are sorted by predicted date."""
        forecasts = await get_upcoming_forecasts(async_session)

        if len(forecasts) > 1:
            dates = [f.predicted_open_date for f in forecasts]
            assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_respects_limit(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that forecasts respect limit parameter."""
        forecasts = await get_upcoming_forecasts(async_session, limit=2)

        assert len(forecasts) <= 2

    @pytest.mark.asyncio
    async def test_includes_fiscal_quarter(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that forecasts include fiscal quarter."""
        forecasts = await get_upcoming_forecasts(async_session)

        for forecast in forecasts:
            if forecast.fiscal_quarter is not None:
                assert 1 <= forecast.fiscal_quarter <= 4

    @pytest.mark.asyncio
    async def test_identifies_federal_funders(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that federal funders are identified."""
        forecasts = await get_upcoming_forecasts(async_session)

        nsf_forecasts = [f for f in forecasts if "NSF" in f.funder_name or "National Science" in f.funder_name]
        for f in nsf_forecasts:
            assert f.is_federal_funder is True


# =============================================================================
# Get Seasonal Trends Tests
# =============================================================================


class TestGetSeasonalTrends:
    """Tests for seasonal trend analysis."""

    @pytest.mark.asyncio
    async def test_returns_twelve_months(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that all 12 months are returned."""
        trends = await get_seasonal_trends(async_session)

        assert len(trends) == 12

    @pytest.mark.asyncio
    async def test_months_in_order(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that months are returned in order."""
        trends = await get_seasonal_trends(async_session)

        months = [t.month for t in trends]
        assert months == list(range(1, 13))

    @pytest.mark.asyncio
    async def test_includes_month_names(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that month names are included."""
        trends = await get_seasonal_trends(async_session)

        for trend in trends:
            assert trend.month_name == MONTH_NAMES[trend.month]

    @pytest.mark.asyncio
    async def test_result_structure(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that results have correct structure."""
        trends = await get_seasonal_trends(async_session)

        for trend in trends:
            assert isinstance(trend, SeasonalTrendResult)
            assert isinstance(trend.grant_count, int)
            assert isinstance(trend.top_categories, list)
            assert isinstance(trend.top_funders, list)


# =============================================================================
# Get Recommendations Tests
# =============================================================================


class TestGetRecommendations:
    """Tests for grant recommendations."""

    @pytest.mark.asyncio
    async def test_returns_recommendations_without_profile(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user
    ):
        """Test recommendations without user profile."""
        recommendations = await get_recommendations(
            async_session, sample_user.id
        )

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, RecommendationResult)
            assert "Complete your profile" in rec.match_reasons[0]

    @pytest.mark.asyncio
    async def test_returns_recommendations_with_profile(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user, sample_profile
    ):
        """Test recommendations with user profile."""
        recommendations = await get_recommendations(
            async_session, sample_user.id
        )

        assert isinstance(recommendations, list)
        for rec in recommendations:
            assert isinstance(rec, RecommendationResult)
            assert rec.match_score >= 0
            assert rec.match_score <= 1

    @pytest.mark.asyncio
    async def test_recommendations_sorted_by_score(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user, sample_profile
    ):
        """Test that recommendations are sorted by match score."""
        recommendations = await get_recommendations(
            async_session, sample_user.id
        )

        if len(recommendations) > 1:
            scores = [r.match_score for r in recommendations]
            assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_respects_limit(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user, sample_profile
    ):
        """Test that recommendations respect limit."""
        recommendations = await get_recommendations(
            async_session, sample_user.id, limit=3
        )

        assert len(recommendations) <= 3

    @pytest.mark.asyncio
    async def test_includes_profile_overlap(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user, sample_profile
    ):
        """Test that profile overlap is included."""
        recommendations = await get_recommendations(
            async_session, sample_user.id
        )

        for rec in recommendations:
            assert isinstance(rec.profile_overlap, list)


# =============================================================================
# Integration Tests
# =============================================================================


class TestForecastIntegration:
    """Integration tests for forecast workflow."""

    @pytest.mark.asyncio
    async def test_full_forecast_workflow(
        self, async_session: AsyncSession, sample_grants_for_forecast, sample_user, sample_profile
    ):
        """Test complete forecast workflow."""
        # Step 1: Analyze patterns
        patterns = await analyze_funder_patterns(async_session)
        assert len(patterns) > 0

        # Step 2: Get forecasts
        forecasts = await get_upcoming_forecasts(async_session)
        assert len(forecasts) > 0

        # Step 3: Get seasonal trends
        trends = await get_seasonal_trends(async_session)
        assert len(trends) == 12

        # Step 4: Get recommendations
        recommendations = await get_recommendations(
            async_session, sample_user.id
        )
        assert len(recommendations) > 0

        # Verify data consistency
        for forecast in forecasts:
            assert forecast.predicted_open_date >= date.today()
            assert 0 <= forecast.confidence <= 1

    @pytest.mark.asyncio
    async def test_forecasts_match_patterns(
        self, async_session: AsyncSession, sample_grants_for_forecast
    ):
        """Test that forecasts are based on analyzed patterns."""
        patterns = await analyze_funder_patterns(async_session)
        forecasts = await get_upcoming_forecasts(async_session)

        pattern_funders = {p.funder_name for p in patterns}

        for forecast in forecasts:
            # All forecasts should come from known patterns
            assert forecast.funder_name in pattern_funders
