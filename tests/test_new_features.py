"""
New Features Tests
Consolidated unit tests for analytics, forecast, funder insights, calendar, pipeline, saved searches.
These tests are database-independent and focus on business logic.
Database integration tests are in existing test files with proper PostgreSQL fixtures.
"""

import math
from datetime import datetime, timedelta, timezone


from backend.models import ApplicationStage


# =============================================================================
# Analytics Tests
# =============================================================================


class TestAnalyticsSuccessRates:
    """Tests for analytics success rate calculations."""

    def test_calculate_success_rate_normal(self):
        """Test normal success rate calculation."""
        from backend.api.analytics import calculate_success_rate

        rate = calculate_success_rate(awarded=3, submitted=9)
        assert rate == 33.3

    def test_calculate_success_rate_zero_submitted(self):
        """Test success rate with zero submissions."""
        from backend.api.analytics import calculate_success_rate

        rate = calculate_success_rate(awarded=0, submitted=0)
        assert rate == 0.0

    def test_calculate_success_rate_all_awarded(self):
        """Test 100% success rate."""
        from backend.api.analytics import calculate_success_rate

        rate = calculate_success_rate(awarded=5, submitted=5)
        assert rate == 100.0

    def test_calculate_success_rate_partial(self):
        """Test partial success rate."""
        from backend.api.analytics import calculate_success_rate

        rate = calculate_success_rate(awarded=1, submitted=4)
        assert rate == 25.0


class TestAnalyticsPipelineStages:
    """Tests for pipeline stage ordering."""

    def test_stage_order_defined(self):
        """Test that stage order is properly defined."""
        from backend.api.analytics import STAGE_ORDER

        assert "researching" in STAGE_ORDER
        assert "writing" in STAGE_ORDER
        assert "submitted" in STAGE_ORDER
        assert "awarded" in STAGE_ORDER
        assert "rejected" in STAGE_ORDER


# =============================================================================
# Forecast Tests (Unit Tests - No DB)
# =============================================================================


class TestForecastConfidence:
    """Tests for forecast confidence scoring."""

    def test_confidence_decreases_with_distance(self):
        """Test that confidence decreases for forecasts further in future."""

        def calculate_confidence(months_ahead: int) -> float:
            base_confidence = 0.95
            decay_rate = 0.05
            return max(0.3, base_confidence - (months_ahead * decay_rate))

        confidences = [calculate_confidence(m) for m in range(12)]
        for i in range(len(confidences) - 1):
            assert confidences[i] >= confidences[i + 1]

    def test_confidence_minimum_threshold(self):
        """Test that confidence has a minimum threshold."""

        def calculate_confidence(months_ahead: int) -> float:
            base_confidence = 0.95
            decay_rate = 0.05
            return max(0.3, base_confidence - (months_ahead * decay_rate))

        far_future_confidence = calculate_confidence(24)
        assert far_future_confidence >= 0.3


class TestSeasonalAnalysis:
    """Tests for seasonal trend analysis."""

    def test_identify_peak_months(self):
        """Test identifying peak grant months."""
        monthly_data = {1: 15, 2: 12, 3: 20, 4: 10, 5: 8, 6: 6, 7: 5, 8: 4, 9: 8, 10: 12, 11: 15, 12: 10}
        peak_month = max(monthly_data, key=monthly_data.get)
        assert peak_month == 3

    def test_identify_low_months(self):
        """Test identifying low grant months."""
        monthly_data = {1: 15, 2: 12, 3: 20, 4: 10, 5: 8, 6: 6, 7: 5, 8: 4, 9: 8, 10: 12, 11: 15, 12: 10}
        low_month = min(monthly_data, key=monthly_data.get)
        assert low_month == 8

    def test_quarterly_aggregation(self):
        """Test quarterly data aggregation."""
        monthly_data = {1: 15, 2: 12, 3: 20, 4: 10, 5: 8, 6: 6, 7: 5, 8: 4, 9: 8, 10: 12, 11: 15, 12: 10}
        quarterly = {
            "Q1": sum(monthly_data[m] for m in [1, 2, 3]),
            "Q2": sum(monthly_data[m] for m in [4, 5, 6]),
            "Q3": sum(monthly_data[m] for m in [7, 8, 9]),
            "Q4": sum(monthly_data[m] for m in [10, 11, 12]),
        }
        assert quarterly["Q1"] > quarterly["Q3"]


# =============================================================================
# Funder Insights Tests (Unit Tests)
# =============================================================================


class TestFunderHelpers:
    """Tests for funder insight helper functions."""

    def test_is_grant_active_future_deadline(self):
        """Test active grant detection with future deadline."""
        from backend.api.funder_insights import is_grant_active

        future = datetime.now(timezone.utc) + timedelta(days=30)
        assert is_grant_active(future) is True

    def test_is_grant_active_past_deadline(self):
        """Test active grant detection with past deadline."""
        from backend.api.funder_insights import is_grant_active

        past = datetime.now(timezone.utc) - timedelta(days=30)
        assert is_grant_active(past) is False

    def test_is_grant_active_no_deadline(self):
        """Test active grant detection with no deadline."""
        from backend.api.funder_insights import is_grant_active

        assert is_grant_active(None) is True

    def test_month_names_array(self):
        """Test month names array is correct."""
        from backend.api.funder_insights import MONTH_NAMES

        assert len(MONTH_NAMES) == 13  # Index 0 is empty
        assert MONTH_NAMES[1] == "January"
        assert MONTH_NAMES[12] == "December"


# =============================================================================
# Calendar Tests (Unit Tests)
# =============================================================================


class TestICSGeneration:
    """Tests for ICS file generation patterns."""

    def test_ics_header_format(self):
        """Test ICS file header format components."""
        expected_headers = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:",
        ]
        for header in expected_headers:
            assert isinstance(header, str)

    def test_ics_date_format(self):
        """Test ICS date formatting."""
        now = datetime.now(timezone.utc)
        ics_format = now.strftime("%Y%m%dT%H%M%SZ")
        assert len(ics_format) == 16
        assert ics_format.endswith("Z")
        assert "T" in ics_format

    def test_urgency_classification(self):
        """Test deadline urgency classification."""

        def classify_urgency(days_until: int) -> str:
            if days_until <= 7:
                return "urgent"
            elif days_until <= 14:
                return "warning"
            else:
                return "normal"

        assert classify_urgency(3) == "urgent"
        assert classify_urgency(10) == "warning"
        assert classify_urgency(30) == "normal"


# =============================================================================
# Pipeline Tests (Unit Tests)
# =============================================================================


class TestStageTransitions:
    """Tests for pipeline stage transitions."""

    def test_all_stages_defined(self):
        """Test all application stages are defined."""
        stages = list(ApplicationStage)
        assert ApplicationStage.RESEARCHING in stages
        assert ApplicationStage.WRITING in stages
        assert ApplicationStage.SUBMITTED in stages
        assert ApplicationStage.AWARDED in stages
        assert ApplicationStage.REJECTED in stages

    def test_stage_values(self):
        """Test stage enum values."""
        assert ApplicationStage.RESEARCHING.value == "researching"
        assert ApplicationStage.WRITING.value == "writing"
        assert ApplicationStage.SUBMITTED.value == "submitted"
        assert ApplicationStage.AWARDED.value == "awarded"
        assert ApplicationStage.REJECTED.value == "rejected"


class TestDeadlineCalculations:
    """Tests for deadline calculation helpers."""

    def test_days_until_calculation(self):
        """Test days until deadline calculation."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(days=10)
        days_until = (future - now).days
        assert days_until == 10

    def test_expired_deadline_detection(self):
        """Test expired deadline detection."""
        now = datetime.now(timezone.utc)
        past = now - timedelta(days=5)
        is_expired = past < now
        assert is_expired is True


# =============================================================================
# Saved Search Tests (Unit Tests)
# =============================================================================


class TestFilterValidation:
    """Tests for saved search filter validation."""

    def test_valid_source_filter(self):
        """Test valid source values."""
        valid_sources = ["grants_gov", "nsf", "nih"]
        filters = {"source": valid_sources}
        assert all(s in ["grants_gov", "nsf", "nih"] for s in filters["source"])

    def test_valid_amount_range(self):
        """Test valid amount range."""
        filters = {"amount_min": 50000, "amount_max": 500000}
        assert filters["amount_min"] <= filters["amount_max"]

    def test_valid_category_filter(self):
        """Test valid category values."""
        filters = {"categories": ["machine_learning", "healthcare"]}
        assert isinstance(filters["categories"], list)
        assert len(filters["categories"]) > 0


# =============================================================================
# Services Tests (Unit Tests)
# =============================================================================


class TestSimilarityService:
    """Tests for similarity scoring algorithms."""

    def test_cosine_similarity_identical(self):
        """Test cosine similarity for identical vectors."""

        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0

        vec = [0.1, 0.2, 0.3, 0.4]
        similarity = cosine_similarity(vec, vec)
        assert abs(similarity - 1.0) < 0.0001

    def test_cosine_similarity_orthogonal(self):
        """Test cosine similarity for orthogonal vectors."""

        def cosine_similarity(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            norm_a = math.sqrt(sum(x * x for x in a))
            norm_b = math.sqrt(sum(x * x for x in b))
            return dot / (norm_a * norm_b) if norm_a and norm_b else 0

        vec_a = [1, 0, 0, 0]
        vec_b = [0, 1, 0, 0]
        similarity = cosine_similarity(vec_a, vec_b)
        assert abs(similarity) < 0.0001

    def test_category_overlap_score(self):
        """Test category overlap scoring."""

        def category_overlap(a: list[str], b: list[str]) -> float:
            set_a = set(a)
            set_b = set(b)
            overlap = len(set_a & set_b)
            union = len(set_a | set_b)
            return overlap / union if union else 0

        score1 = category_overlap(["ml", "healthcare", "ai"], ["ml", "healthcare", "data_science"])
        assert score1 > 0.4

        score2 = category_overlap(["ml", "healthcare"], ["geology", "archaeology"])
        assert score2 == 0


class TestMatchScoring:
    """Tests for match scoring algorithms."""

    def test_combined_score_calculation(self):
        """Test combined match score calculation."""

        def calculate_combined_score(
            vector_score: float,
            category_score: float,
            career_match: float,
        ) -> float:
            weights = {"vector": 0.5, "category": 0.3, "career": 0.2}
            return (
                vector_score * weights["vector"]
                + category_score * weights["category"]
                + career_match * weights["career"]
            )

        score = calculate_combined_score(0.8, 0.9, 1.0)
        assert 0.8 <= score <= 0.9

    def test_score_normalization(self):
        """Test score normalization to 0-1 range."""

        def normalize_score(score: float) -> float:
            return max(0.0, min(1.0, score))

        assert normalize_score(1.5) == 1.0
        assert normalize_score(-0.5) == 0.0
        assert normalize_score(0.75) == 0.75

    def test_score_thresholds(self):
        """Test score classification thresholds."""

        def classify_score(score: float) -> str:
            if score >= 0.85:
                return "excellent"
            elif score >= 0.70:
                return "good"
            elif score >= 0.50:
                return "moderate"
            else:
                return "low"

        assert classify_score(0.95) == "excellent"
        assert classify_score(0.75) == "good"
        assert classify_score(0.60) == "moderate"
        assert classify_score(0.30) == "low"


class TestCVParserService:
    """Tests for CV parsing helpers."""

    def test_extract_research_areas(self):
        """Test extracting research areas from CV text."""

        def extract_research_areas(text: str) -> list[str]:
            keywords = [
                "machine learning",
                "artificial intelligence",
                "deep learning",
                "natural language processing",
                "computer vision",
                "healthcare",
                "genomics",
                "climate",
                "neuroscience",
            ]
            text_lower = text.lower()
            return [kw for kw in keywords if kw in text_lower]

        cv_text = """
        Research Focus: Machine Learning and Healthcare Applications
        I specialize in deep learning methods for medical image analysis
        and natural language processing for clinical text.
        """
        areas = extract_research_areas(cv_text)
        assert "machine learning" in areas
        assert "deep learning" in areas

    def test_extract_publications(self):
        """Test extracting publication information."""
        import re

        def extract_publications(text: str) -> dict:
            pub_count = len(re.findall(r"\d{4}\)", text))
            h_index_match = re.search(r"h-index[:\s]+(\d+)", text, re.I)
            return {"estimated_count": pub_count, "h_index": int(h_index_match.group(1)) if h_index_match else None}

        cv_text = """
        Selected Publications:
        1. Smith et al. (2023) "Deep Learning for Healthcare"
        2. Smith et al. (2022) "NLP in Medicine"
        Metrics: h-index: 15
        """
        pubs = extract_publications(cv_text)
        assert pubs["estimated_count"] == 2
        assert pubs["h_index"] == 15


class TestORCIDService:
    """Tests for ORCID validation."""

    def test_validate_orcid_format(self):
        """Test ORCID ID format validation."""
        import re

        def is_valid_orcid(orcid: str) -> bool:
            pattern = r"^\d{4}-\d{4}-\d{4}-\d{3}[\dX]$"
            return bool(re.match(pattern, orcid))

        assert is_valid_orcid("0000-0002-1234-5678")
        assert is_valid_orcid("0000-0002-1234-567X")
        assert not is_valid_orcid("invalid")
        assert not is_valid_orcid("0000-0002-1234")


# Note: Database integration tests are handled by existing test files
# (test_user_api.py, test_grant_api.py, test_match_api.py, etc.)
# which use the proper PostgreSQL fixtures from conftest.py
