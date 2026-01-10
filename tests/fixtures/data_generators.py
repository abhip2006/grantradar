"""
Test Data Generators
Utilities for generating realistic test data for various scenarios.
"""

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


class RandomDataGenerator:
    """Generate random but realistic test data."""

    RESEARCH_AREAS = [
        "machine_learning",
        "natural_language_processing",
        "computer_vision",
        "deep_learning",
        "reinforcement_learning",
        "genomics",
        "bioinformatics",
        "precision_medicine",
        "drug_discovery",
        "clinical_trials",
        "climate_modeling",
        "atmospheric_science",
        "sustainability",
        "renewable_energy",
        "neuroscience",
        "cognitive_science",
        "brain_imaging",
        "quantum_computing",
        "cybersecurity",
        "robotics",
    ]

    AGENCIES = [
        "National Institutes of Health",
        "National Science Foundation",
        "Department of Energy",
        "National Cancer Institute",
        "DARPA",
        "NASA",
        "Department of Defense",
        "National Institute of Standards and Technology",
        "Environmental Protection Agency",
        "Centers for Disease Control",
    ]

    INSTITUTIONS = [
        "Stanford University",
        "MIT",
        "Harvard University",
        "UC Berkeley",
        "Caltech",
        "Princeton University",
        "Yale University",
        "Columbia University",
        "University of Chicago",
        "Johns Hopkins University",
    ]

    FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry", "Iris", "James"]
    LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Davis", "Miller", "Wilson", "Moore", "Taylor"]

    @classmethod
    def random_research_areas(cls, count: int = 3) -> list[str]:
        """Generate random research areas."""
        return random.sample(cls.RESEARCH_AREAS, min(count, len(cls.RESEARCH_AREAS)))

    @classmethod
    def random_agency(cls) -> str:
        """Generate a random agency name."""
        return random.choice(cls.AGENCIES)

    @classmethod
    def random_institution(cls) -> str:
        """Generate a random institution name."""
        return random.choice(cls.INSTITUTIONS)

    @classmethod
    def random_name(cls) -> str:
        """Generate a random researcher name."""
        return f"Dr. {random.choice(cls.FIRST_NAMES)} {random.choice(cls.LAST_NAMES)}"

    @classmethod
    def random_email(cls, domain: str = "university.edu") -> str:
        """Generate a random email address."""
        first = random.choice(cls.FIRST_NAMES).lower()
        last = random.choice(cls.LAST_NAMES).lower()
        return f"{first}.{last}@{domain}"

    @classmethod
    def random_amount_range(cls, min_val: int = 10000, max_val: int = 5000000) -> tuple[int, int]:
        """Generate a random funding amount range."""
        amount_min = random.randint(min_val, max_val // 2)
        amount_max = random.randint(amount_min, max_val)
        return amount_min, amount_max

    @classmethod
    def random_deadline(
        cls,
        min_days: int = 7,
        max_days: int = 365,
    ) -> datetime:
        """Generate a random deadline."""
        days = random.randint(min_days, max_days)
        return datetime.now(timezone.utc) + timedelta(days=days)

    @classmethod
    def random_match_score(cls, bias: str = "neutral") -> float:
        """Generate a random match score with optional bias."""
        if bias == "high":
            return round(random.uniform(0.75, 0.99), 2)
        elif bias == "low":
            return round(random.uniform(0.1, 0.45), 2)
        else:
            return round(random.uniform(0.3, 0.95), 2)


class ScenarioDataGenerator:
    """Generate data for specific test scenarios."""

    @classmethod
    def pipeline_scenario(cls, num_grants: int = 20) -> dict[str, Any]:
        """Generate data for pipeline testing scenario."""
        from backend.models import ApplicationStage

        # Distribution of applications across stages
        stage_distribution = {
            ApplicationStage.RESEARCHING: 0.30,
            ApplicationStage.WRITING: 0.25,
            ApplicationStage.SUBMITTED: 0.25,
            ApplicationStage.AWARDED: 0.10,
            ApplicationStage.REJECTED: 0.10,
        }

        stages = []
        for stage, ratio in stage_distribution.items():
            count = int(num_grants * ratio)
            stages.extend([stage] * count)

        # Fill remaining with RESEARCHING
        while len(stages) < num_grants:
            stages.append(ApplicationStage.RESEARCHING)

        random.shuffle(stages)

        return {
            "stages": stages[:num_grants],
            "num_grants": num_grants,
        }

    @classmethod
    def analytics_scenario(cls, num_months: int = 12) -> dict[str, Any]:
        """Generate data for analytics testing scenario."""
        # Create monthly data points
        now = datetime.now(timezone.utc)
        months = []

        for i in range(num_months):
            month_start = now - timedelta(days=30 * i)
            months.append(
                {
                    "date": month_start,
                    "applications": random.randint(2, 10),
                    "awarded": random.randint(0, 3),
                    "rejected": random.randint(0, 2),
                    "funding_applied": random.randint(100000, 1000000),
                    "funding_awarded": random.randint(0, 500000),
                }
            )

        return {
            "months": list(reversed(months)),
            "total_months": num_months,
        }

    @classmethod
    def funder_scenario(cls, num_funders: int = 5, grants_per_funder: int = 10) -> dict[str, Any]:
        """Generate data for funder insights testing."""
        funders = random.sample(RandomDataGenerator.AGENCIES, num_funders)

        funder_data = {}
        for funder in funders:
            categories = random.sample(RandomDataGenerator.RESEARCH_AREAS, 3)
            funder_data[funder] = {
                "categories": categories,
                "grants_count": grants_per_funder,
                "avg_amount": random.randint(100000, 1000000),
                "success_rate": round(random.uniform(0.1, 0.4), 2),
            }

        return {
            "funders": funder_data,
            "total_funders": num_funders,
        }

    @classmethod
    def calendar_scenario(cls) -> dict[str, Any]:
        """Generate data for calendar testing."""
        now = datetime.now(timezone.utc)

        deadlines = []

        # Urgent (within 7 days)
        for i in range(3):
            deadlines.append(
                {
                    "days_until": random.randint(1, 7),
                    "urgency": "urgent",
                }
            )

        # Soon (8-30 days)
        for i in range(5):
            deadlines.append(
                {
                    "days_until": random.randint(8, 30),
                    "urgency": "soon",
                }
            )

        # Later (31-90 days)
        for i in range(7):
            deadlines.append(
                {
                    "days_until": random.randint(31, 90),
                    "urgency": "later",
                }
            )

        return {
            "deadlines": deadlines,
            "reference_date": now,
        }

    @classmethod
    def forecast_scenario(cls, months_ahead: int = 6) -> dict[str, Any]:
        """Generate data for forecast testing."""
        now = datetime.now(timezone.utc)

        seasonal_patterns = {
            1: 0.8,  # January - lower
            2: 0.9,  # February
            3: 1.2,  # March - higher (end of fiscal year)
            4: 1.1,  # April
            5: 1.0,  # May
            6: 0.9,  # June
            7: 0.7,  # July - lower (summer)
            8: 0.7,  # August
            9: 1.3,  # September - higher (new fiscal year)
            10: 1.2,  # October
            11: 1.0,  # November
            12: 0.8,  # December - lower (holidays)
        }

        forecasts = []
        for i in range(months_ahead):
            future_date = now + timedelta(days=30 * i)
            month = future_date.month
            base_count = 50

            forecasts.append(
                {
                    "month": month,
                    "expected_grants": int(base_count * seasonal_patterns[month]),
                    "confidence": round(0.9 - (i * 0.05), 2),  # Confidence decreases further out
                }
            )

        return {
            "forecasts": forecasts,
            "months_ahead": months_ahead,
        }


class AssertionHelpers:
    """Helper methods for test assertions."""

    @staticmethod
    def assert_pagination(response: dict, expected_total: int, page: int = 1, page_size: int = 20):
        """Assert pagination fields in response."""
        assert "total" in response
        assert response["total"] == expected_total
        if "page" in response:
            assert response["page"] == page
        if "page_size" in response:
            assert response["page_size"] == page_size

    @staticmethod
    def assert_grant_response(grant: dict):
        """Assert a grant response has required fields."""
        required_fields = ["id", "title", "source"]
        for field in required_fields:
            assert field in grant, f"Missing required field: {field}"

    @staticmethod
    def assert_match_response(match: dict):
        """Assert a match response has required fields."""
        required_fields = ["id", "match_score", "grant_id", "user_id"]
        for field in required_fields:
            assert field in match, f"Missing required field: {field}"

    @staticmethod
    def assert_application_response(application: dict):
        """Assert an application response has required fields."""
        required_fields = ["id", "stage", "grant_id", "user_id"]
        for field in required_fields:
            assert field in application, f"Missing required field: {field}"

    @staticmethod
    def assert_date_format(date_str: str):
        """Assert a date string is in ISO format."""
        try:
            datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except ValueError:
            raise AssertionError(f"Invalid date format: {date_str}")

    @staticmethod
    def assert_score_range(score: float, min_val: float = 0.0, max_val: float = 1.0):
        """Assert a score is within expected range."""
        assert min_val <= score <= max_val, f"Score {score} out of range [{min_val}, {max_val}]"

    @staticmethod
    def assert_amount_range(amount_min: Optional[int], amount_max: Optional[int]):
        """Assert amount range is valid."""
        if amount_min is not None and amount_max is not None:
            assert amount_min <= amount_max, f"Invalid amount range: {amount_min} > {amount_max}"
