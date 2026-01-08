"""
Tests for ML forecast service.
Tests Prophet-based time-series forecasting for grant deadlines.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Grant
from backend.services.ml_forecast import (
    GrantDeadlinePredictor,
    MLPredictionResult,
    get_predictor,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def predictor():
    """Create a fresh predictor instance for testing."""
    return GrantDeadlinePredictor(min_data_points=3)


@pytest.fixture
def sample_deadlines():
    """Create sample deadline dates for testing."""
    today = date.today()
    # Create deadlines that show an annual pattern (same month each year)
    return [
        date(2023, 3, 31),
        date(2024, 3, 31),
        date(2025, 3, 30),
        date(2022, 3, 31),
        date(2021, 3, 31),
    ]


@pytest_asyncio.fixture
async def sample_grants_for_ml(async_session: AsyncSession):
    """Create sample grants with varied deadlines for ML testing."""
    grants = []
    base_date = datetime.now(timezone.utc)

    # NSF grants with annual pattern (March deadlines)
    for year in range(2021, 2026):
        grant = Grant(
            id=uuid.uuid4(),
            source="nsf",
            external_id=f"NSF-{year}-001",
            title=f"NSF Research Grant {year}",
            description="Test grant for ML prediction",
            agency="National Science Foundation",
            deadline=datetime(year, 3, 31, tzinfo=timezone.utc),
            amount_min=100000,
            amount_max=500000,
            categories=["research"],
        )
        async_session.add(grant)
        grants.append(grant)

    # NIH grants with bi-annual pattern (Feb and Oct)
    for year in range(2022, 2026):
        for month in [2, 10]:
            grant = Grant(
                id=uuid.uuid4(),
                source="nih",
                external_id=f"NIH-{year}-{month:02d}",
                title=f"NIH Health Grant {year}-{month}",
                description="Health research grant",
                agency="NIH - National Cancer Institute",
                deadline=datetime(year, month, 15, tzinfo=timezone.utc),
                amount_min=200000,
                amount_max=1000000,
                categories=["health"],
            )
            async_session.add(grant)
            grants.append(grant)

    # Small funder with insufficient data (only 1 grant)
    grant = Grant(
        id=uuid.uuid4(),
        source="small",
        external_id="SMALL-001",
        title="Small Foundation Grant",
        description="Single grant",
        agency="Small Foundation",
        deadline=base_date,
        amount_min=10000,
        amount_max=50000,
        categories=["general"],
    )
    async_session.add(grant)
    grants.append(grant)

    await async_session.commit()
    return grants


# =============================================================================
# Predictor Initialization Tests
# =============================================================================


class TestPredictorInitialization:
    """Tests for GrantDeadlinePredictor initialization."""

    def test_init_default_min_data_points(self):
        """Test default minimum data points."""
        predictor = GrantDeadlinePredictor()
        assert predictor.min_data_points == 4

    def test_init_custom_min_data_points(self):
        """Test custom minimum data points."""
        predictor = GrantDeadlinePredictor(min_data_points=10)
        assert predictor.min_data_points == 10

    def test_init_empty_cache(self):
        """Test that cache is empty on initialization."""
        predictor = GrantDeadlinePredictor()
        assert len(predictor._model_cache) == 0

    def test_cache_expiry_default(self):
        """Test default cache expiry time."""
        predictor = GrantDeadlinePredictor()
        assert predictor._cache_expiry_hours == 24


# =============================================================================
# Model Cache Tests
# =============================================================================


class TestModelCache:
    """Tests for model caching functionality."""

    def test_is_model_stale_no_cache(self, predictor):
        """Test stale check with no cached model."""
        assert predictor._is_model_stale("Test Funder") is True

    def test_is_model_stale_fresh_cache(self, predictor):
        """Test stale check with fresh cache."""
        # Manually add a cached model
        mock_model = MagicMock()
        predictor._model_cache["Test Funder"] = (mock_model, datetime.utcnow())

        assert predictor._is_model_stale("Test Funder") is False

    def test_is_model_stale_expired_cache(self, predictor):
        """Test stale check with expired cache."""
        mock_model = MagicMock()
        expired_time = datetime.utcnow() - timedelta(hours=25)
        predictor._model_cache["Test Funder"] = (mock_model, expired_time)

        assert predictor._is_model_stale("Test Funder") is True

    def test_clear_cache_specific_funder(self, predictor):
        """Test clearing cache for specific funder."""
        mock_model = MagicMock()
        predictor._model_cache["Funder A"] = (mock_model, datetime.utcnow())
        predictor._model_cache["Funder B"] = (mock_model, datetime.utcnow())

        predictor.clear_cache("Funder A")

        assert "Funder A" not in predictor._model_cache
        assert "Funder B" in predictor._model_cache

    def test_clear_cache_all(self, predictor):
        """Test clearing entire cache."""
        mock_model = MagicMock()
        predictor._model_cache["Funder A"] = (mock_model, datetime.utcnow())
        predictor._model_cache["Funder B"] = (mock_model, datetime.utcnow())

        predictor.clear_cache()

        assert len(predictor._model_cache) == 0

    def test_get_cache_stats(self, predictor):
        """Test getting cache statistics."""
        mock_model = MagicMock()
        predictor._model_cache["Funder A"] = (mock_model, datetime.utcnow())
        predictor._model_cache["Funder B"] = (mock_model, datetime.utcnow())

        stats = predictor.get_cache_stats()

        assert stats["cached_models"] == 2
        assert "Funder A" in stats["funder_names"]
        assert "Funder B" in stats["funder_names"]
        assert stats["cache_expiry_hours"] == 24


# =============================================================================
# Data Preparation Tests
# =============================================================================


class TestDataPreparation:
    """Tests for Prophet data preparation."""

    def test_prepare_prophet_data_structure(self, predictor, sample_deadlines):
        """Test that prepared data has correct structure."""
        df = predictor._prepare_prophet_data(sample_deadlines)

        assert isinstance(df, pd.DataFrame)
        assert "ds" in df.columns
        assert "y" in df.columns
        assert len(df) == len(sample_deadlines)

    def test_prepare_prophet_data_day_of_year(self, predictor):
        """Test that y values are day-of-year."""
        deadlines = [date(2024, 1, 1), date(2024, 6, 15), date(2024, 12, 31)]
        df = predictor._prepare_prophet_data(deadlines)

        # Day 1 of year
        assert df.iloc[0]["y"] == 1
        # Day 167 (June 15 in leap year 2024)
        assert df.iloc[1]["y"] == 167
        # Day 366 (Dec 31 in leap year 2024)
        assert df.iloc[2]["y"] == 366

    def test_prepare_prophet_data_timestamps(self, predictor, sample_deadlines):
        """Test that ds values are proper timestamps."""
        df = predictor._prepare_prophet_data(sample_deadlines)

        for idx, row in df.iterrows():
            assert isinstance(row["ds"], pd.Timestamp)


# =============================================================================
# Prophet Model Creation Tests
# =============================================================================


class TestProphetModelCreation:
    """Tests for Prophet model configuration."""

    def test_create_prophet_model_returns_prophet(self, predictor):
        """Test that _create_prophet_model returns a Prophet instance."""
        model = predictor._create_prophet_model()

        from prophet import Prophet
        assert isinstance(model, Prophet)

    def test_create_prophet_model_yearly_seasonality(self, predictor):
        """Test that model has yearly seasonality enabled."""
        model = predictor._create_prophet_model()
        assert model.yearly_seasonality is True

    def test_create_prophet_model_no_weekly_seasonality(self, predictor):
        """Test that model has weekly seasonality disabled."""
        model = predictor._create_prophet_model()
        assert model.weekly_seasonality is False

    def test_create_prophet_model_no_daily_seasonality(self, predictor):
        """Test that model has daily seasonality disabled."""
        model = predictor._create_prophet_model()
        assert model.daily_seasonality is False


# =============================================================================
# Train Model Tests
# =============================================================================


class TestTrainFunderModel:
    """Tests for training funder models."""

    @pytest.mark.asyncio
    async def test_train_with_sufficient_data(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test training with sufficient historical data."""
        result = await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        assert result is True
        assert "National Science Foundation" in predictor._model_cache

    @pytest.mark.asyncio
    async def test_train_with_insufficient_data(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test training with insufficient historical data."""
        result = await predictor.train_funder_model(
            async_session, "Small Foundation"
        )

        assert result is False
        assert "Small Foundation" not in predictor._model_cache

    @pytest.mark.asyncio
    async def test_train_uses_cached_model(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test that training uses cached model when available."""
        # First training
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        # Record cache state
        cache_time_1 = predictor._model_cache["National Science Foundation"][1]

        # Second training (should use cache)
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        cache_time_2 = predictor._model_cache["National Science Foundation"][1]

        # Cache time should be unchanged (same cached model)
        assert cache_time_1 == cache_time_2

    @pytest.mark.asyncio
    async def test_train_force_retrain(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test force retraining bypasses cache."""
        # First training
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        cache_time_1 = predictor._model_cache["National Science Foundation"][1]

        # Force retrain
        await predictor.train_funder_model(
            async_session, "National Science Foundation", force_retrain=True
        )

        cache_time_2 = predictor._model_cache["National Science Foundation"][1]

        # Cache time should be updated
        assert cache_time_2 >= cache_time_1


# =============================================================================
# Prediction Tests
# =============================================================================


class TestPredictNextDeadline:
    """Tests for deadline prediction."""

    @pytest.mark.asyncio
    async def test_predict_requires_trained_model(self, predictor):
        """Test that prediction fails without trained model."""
        with pytest.raises(ValueError, match="No trained model"):
            predictor.predict_next_deadline("Unknown Funder")

    @pytest.mark.asyncio
    async def test_predict_returns_tuple(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test that prediction returns correct structure."""
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        result = predictor.predict_next_deadline("National Science Foundation")

        assert isinstance(result, tuple)
        assert len(result) == 3

        predicted_date, confidence, bounds = result
        assert isinstance(predicted_date, date)
        assert isinstance(confidence, float)
        assert isinstance(bounds, tuple)
        assert len(bounds) == 2

    @pytest.mark.asyncio
    async def test_predict_date_is_future(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test that predicted date is in the future."""
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        predicted_date, _, _ = predictor.predict_next_deadline(
            "National Science Foundation"
        )

        assert predicted_date >= date.today()

    @pytest.mark.asyncio
    async def test_predict_confidence_in_range(
        self, async_session: AsyncSession, sample_grants_for_ml, predictor
    ):
        """Test that confidence is within valid range."""
        await predictor.train_funder_model(
            async_session, "National Science Foundation"
        )

        _, confidence, _ = predictor.predict_next_deadline(
            "National Science Foundation"
        )

        assert 0.5 <= confidence <= 0.95


# =============================================================================
# Prediction with Fallback Tests
# =============================================================================


class TestGetPredictionWithFallback:
    """Tests for prediction with rule-based fallback."""

    @pytest.mark.asyncio
    async def test_returns_ml_prediction_with_sufficient_data(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test ML prediction is used with sufficient data."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        result = await predictor.get_prediction_with_fallback(
            async_session, "National Science Foundation"
        )

        assert result["method"] == "ml"
        assert "predicted_date" in result
        assert "confidence" in result
        assert "lower_bound" in result
        assert "upper_bound" in result

    @pytest.mark.asyncio
    async def test_returns_rule_based_with_insufficient_data(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test rule-based fallback with insufficient data."""
        predictor = GrantDeadlinePredictor(min_data_points=10)

        result = await predictor.get_prediction_with_fallback(
            async_session, "Small Foundation"
        )

        assert result["method"] == "rule_based"

    @pytest.mark.asyncio
    async def test_returns_uncertainty_days(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test that uncertainty days is included."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        result = await predictor.get_prediction_with_fallback(
            async_session, "National Science Foundation"
        )

        assert "uncertainty_days" in result
        assert isinstance(result["uncertainty_days"], int)
        assert result["uncertainty_days"] >= 0


# =============================================================================
# Rule-Based Prediction Tests
# =============================================================================


class TestRuleBasedPrediction:
    """Tests for rule-based prediction fallback."""

    @pytest.mark.asyncio
    async def test_rule_based_with_no_data(self, async_session: AsyncSession):
        """Test rule-based prediction with no historical data."""
        predictor = GrantDeadlinePredictor()

        result = await predictor._get_rule_based_prediction(
            async_session, "Unknown Funder"
        )

        assert result["method"] == "rule_based"
        assert result["confidence"] == 0.3
        assert result["uncertainty_days"] == 60
        assert result["predicted_date"] > date.today()

    @pytest.mark.asyncio
    async def test_rule_based_with_some_data(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test rule-based prediction with some historical data."""
        predictor = GrantDeadlinePredictor(min_data_points=100)  # Force rule-based

        result = await predictor._get_rule_based_prediction(
            async_session, "National Science Foundation"
        )

        assert result["method"] == "rule_based"
        assert result["predicted_date"] is not None


# =============================================================================
# Batch Prediction Tests
# =============================================================================


class TestBatchPredict:
    """Tests for batch prediction functionality."""

    @pytest.mark.asyncio
    async def test_batch_predict_multiple_funders(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test batch prediction for multiple funders."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        funders = [
            "National Science Foundation",
            "NIH - National Cancer Institute",
            "Small Foundation",
        ]
        results = await predictor.batch_predict(async_session, funders)

        assert len(results) == 3
        for funder in funders:
            assert funder in results
            assert "predicted_date" in results[funder]
            assert "method" in results[funder]

    @pytest.mark.asyncio
    async def test_batch_predict_empty_list(self, async_session: AsyncSession):
        """Test batch prediction with empty funder list."""
        predictor = GrantDeadlinePredictor()

        results = await predictor.batch_predict(async_session, [])

        assert results == {}


# =============================================================================
# Get All Funder Predictions Tests
# =============================================================================


class TestGetAllFunderPredictions:
    """Tests for getting predictions for all funders."""

    @pytest.mark.asyncio
    async def test_returns_predictions_list(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test that predictions are returned as a list."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        results = await predictor.get_all_funder_predictions(
            async_session, min_grants=2
        )

        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_includes_funder_info(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test that results include funder information."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        results = await predictor.get_all_funder_predictions(
            async_session, min_grants=2
        )

        for result in results:
            assert "funder_name" in result
            assert "grant_count" in result
            assert "last_deadline" in result

    @pytest.mark.asyncio
    async def test_filters_by_min_grants(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test filtering by minimum grants."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        # With min_grants=5, should only get NSF (has 5 grants)
        results = await predictor.get_all_funder_predictions(
            async_session, min_grants=5
        )

        funder_names = [r["funder_name"] for r in results]
        # Small Foundation only has 1 grant, should be excluded
        assert "Small Foundation" not in funder_names

    @pytest.mark.asyncio
    async def test_sorted_by_predicted_date(
        self, async_session: AsyncSession, sample_grants_for_ml
    ):
        """Test that results are sorted by predicted date."""
        predictor = GrantDeadlinePredictor(min_data_points=3)

        results = await predictor.get_all_funder_predictions(
            async_session, min_grants=2
        )

        if len(results) > 1:
            dates = [r["predicted_date"] for r in results]
            assert dates == sorted(dates)


# =============================================================================
# Global Predictor Instance Tests
# =============================================================================


class TestGetPredictor:
    """Tests for global predictor instance."""

    def test_get_predictor_returns_instance(self):
        """Test that get_predictor returns an instance."""
        predictor = get_predictor()
        assert isinstance(predictor, GrantDeadlinePredictor)

    def test_get_predictor_singleton(self):
        """Test that get_predictor returns same instance."""
        predictor1 = get_predictor()
        predictor2 = get_predictor()

        assert predictor1 is predictor2

    def test_get_predictor_custom_min_data_points(self):
        """Test get_predictor with custom min_data_points."""
        # Note: This only affects initial creation
        predictor = get_predictor(min_data_points=10)
        assert isinstance(predictor, GrantDeadlinePredictor)


# =============================================================================
# MLPredictionResult Dataclass Tests
# =============================================================================


class TestMLPredictionResult:
    """Tests for MLPredictionResult dataclass."""

    def test_create_with_required_fields(self):
        """Test creating result with required fields."""
        result = MLPredictionResult(
            predicted_date=date.today(),
            confidence=0.8,
            method="ml",
            uncertainty_days=10,
        )

        assert result.predicted_date == date.today()
        assert result.confidence == 0.8
        assert result.method == "ml"
        assert result.uncertainty_days == 10
        assert result.lower_bound is None
        assert result.upper_bound is None

    def test_create_with_all_fields(self):
        """Test creating result with all fields."""
        today = date.today()
        result = MLPredictionResult(
            predicted_date=today,
            confidence=0.85,
            method="ml",
            uncertainty_days=15,
            lower_bound=today - timedelta(days=15),
            upper_bound=today + timedelta(days=15),
        )

        assert result.lower_bound == today - timedelta(days=15)
        assert result.upper_bound == today + timedelta(days=15)
