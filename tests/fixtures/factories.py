"""
Test Data Factories
Factory functions for creating test data with sensible defaults and customization options.

These factories create dictionaries suitable for creating model instances,
allowing flexibility with different database backends (SQLite for tests, PostgreSQL for prod).
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from backend.models import (
    AlertSent,
    ApplicationStage,
    Grant,
    GrantApplication,
    LabProfile,
    Match,
    SavedSearch,
    User,
)


class UserFactory:
    """Factory for creating User instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        email: Optional[str] = None,
        password_hash: str = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4eqZzJMnE8mFJGSq",
        name: Optional[str] = None,
        institution: Optional[str] = None,
        phone: Optional[str] = None,
        email_notifications: bool = True,
        sms_notifications: bool = False,
        slack_notifications: bool = False,
        digest_frequency: str = "immediate",
        minimum_match_score: float = 0.7,
        **kwargs,
    ) -> User:
        """Create a User instance with defaults."""
        cls._counter += 1
        return User(
            id=id or uuid.uuid4(),
            email=email or f"researcher{cls._counter}@university.edu",
            password_hash=password_hash,
            name=name or f"Dr. Test User {cls._counter}",
            institution=institution or "Test University",
            phone=phone,
            email_notifications=email_notifications,
            sms_notifications=sms_notifications,
            slack_notifications=slack_notifications,
            digest_frequency=digest_frequency,
            minimum_match_score=minimum_match_score,
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[User]:
        """Create multiple User instances."""
        return [cls.create(**kwargs) for _ in range(count)]


class GrantFactory:
    """Factory for creating Grant instances."""

    _counter = 0

    SOURCES = ["grants_gov", "nsf", "nih"]
    AGENCIES = [
        "National Institutes of Health",
        "National Science Foundation",
        "Department of Energy",
        "National Cancer Institute",
        "DARPA",
    ]
    CATEGORIES = [
        ["machine_learning", "healthcare", "data_science"],
        ["climate", "environment", "sustainability"],
        ["cancer", "oncology", "treatment"],
        ["ai", "robotics", "automation"],
        ["neuroscience", "brain", "cognition"],
    ]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
        external_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        agency: Optional[str] = None,
        amount_min: Optional[int] = None,
        amount_max: Optional[int] = None,
        deadline: Optional[datetime] = None,
        posted_at: Optional[datetime] = None,
        url: Optional[str] = None,
        categories: Optional[list[str]] = None,
        eligibility: Optional[dict] = None,
        **kwargs,
    ) -> Grant:
        """Create a Grant instance with defaults."""
        cls._counter += 1
        now = datetime.now(timezone.utc)

        return Grant(
            id=id or uuid.uuid4(),
            source=source or cls.SOURCES[cls._counter % len(cls.SOURCES)],
            external_id=external_id or f"GRANT-2024-{cls._counter:04d}",
            title=title or f"Research Grant Opportunity {cls._counter}",
            description=description
            or f"This grant supports innovative research in various fields. Grant #{cls._counter}.",
            agency=agency or cls.AGENCIES[cls._counter % len(cls.AGENCIES)],
            amount_min=amount_min if amount_min is not None else 50000 + (cls._counter * 10000),
            amount_max=amount_max if amount_max is not None else 200000 + (cls._counter * 50000),
            deadline=deadline or (now + timedelta(days=30 + cls._counter * 7)),
            posted_at=posted_at or (now - timedelta(days=cls._counter)),
            url=url or f"https://grants.gov/view-opportunity.html?oppId={cls._counter}",
            categories=categories or cls.CATEGORIES[cls._counter % len(cls.CATEGORIES)],
            eligibility=eligibility
            or {
                "institution_types": ["universities", "research_institutions"],
                "career_stages": ["early_career", "established"],
            },
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, **kwargs) -> list[Grant]:
        """Create multiple Grant instances."""
        return [cls.create(**kwargs) for _ in range(count)]

    @classmethod
    def create_expired(cls, days_ago: int = 7, **kwargs) -> Grant:
        """Create an expired grant."""
        now = datetime.now(timezone.utc)
        return cls.create(
            deadline=now - timedelta(days=days_ago),
            **kwargs,
        )

    @classmethod
    def create_urgent(cls, days_until: int = 3, **kwargs) -> Grant:
        """Create a grant with urgent deadline."""
        now = datetime.now(timezone.utc)
        return cls.create(
            deadline=now + timedelta(days=days_until),
            **kwargs,
        )


class LabProfileFactory:
    """Factory for creating LabProfile instances."""

    _counter = 0

    RESEARCH_AREAS = [
        ["machine_learning", "natural_language_processing", "computer_vision"],
        ["genomics", "bioinformatics", "precision_medicine"],
        ["climate_modeling", "atmospheric_science", "sustainability"],
        ["neuroscience", "cognitive_science", "brain_imaging"],
        ["quantum_computing", "cryptography", "information_theory"],
    ]

    METHODS = [
        ["deep_learning", "transformer_models", "reinforcement_learning"],
        ["crispr", "single_cell_sequencing", "proteomics"],
        ["satellite_data_analysis", "climate_simulation", "remote_sensing"],
        ["fmri", "eeg", "computational_modeling"],
        ["quantum_algorithms", "error_correction", "quantum_simulation"],
    ]

    CAREER_STAGES = ["early_career", "mid_career", "established", "senior"]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        research_areas: Optional[list[str]] = None,
        methods: Optional[list[str]] = None,
        career_stage: Optional[str] = None,
        past_grants: Optional[dict] = None,
        publications: Optional[dict] = None,
        orcid: Optional[str] = None,
        **kwargs,
    ) -> LabProfile:
        """Create a LabProfile instance with defaults."""
        cls._counter += 1

        return LabProfile(
            id=id or uuid.uuid4(),
            user_id=user_id or uuid.uuid4(),
            research_areas=research_areas or cls.RESEARCH_AREAS[cls._counter % len(cls.RESEARCH_AREAS)],
            methods=methods or cls.METHODS[cls._counter % len(cls.METHODS)],
            career_stage=career_stage or cls.CAREER_STAGES[cls._counter % len(cls.CAREER_STAGES)],
            past_grants=past_grants
            or {
                "awards": [
                    {"agency": "NSF", "amount": 500000, "year": 2023},
                    {"agency": "NIH", "amount": 300000, "year": 2022},
                ]
            },
            publications=publications
            or {
                "total": 20 + cls._counter * 5,
                "h_index": 10 + cls._counter,
                "recent_topics": ["AI", "healthcare", "research"],
            },
            orcid=orcid or f"0000-0002-{cls._counter:04d}-5678",
            **kwargs,
        )


class MatchFactory:
    """Factory for creating Match instances."""

    _counter = 0

    USER_ACTIONS = [None, "saved", "dismissed", "applied", "interested"]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        grant_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        match_score: Optional[float] = None,
        reasoning: Optional[str] = None,
        predicted_success: Optional[float] = None,
        user_action: Optional[str] = None,
        **kwargs,
    ) -> Match:
        """Create a Match instance with defaults."""
        cls._counter += 1

        # Generate varied scores for testing
        base_score = 0.5 + (cls._counter % 5) * 0.1

        return Match(
            id=id or uuid.uuid4(),
            grant_id=grant_id or uuid.uuid4(),
            user_id=user_id or uuid.uuid4(),
            match_score=match_score if match_score is not None else base_score,
            reasoning=reasoning or f"Strong alignment based on research focus. Match #{cls._counter}.",
            predicted_success=predicted_success if predicted_success is not None else base_score * 0.8,
            user_action=user_action,
            **kwargs,
        )

    @classmethod
    def create_batch(cls, count: int, user_id: uuid.UUID, grant_ids: list[uuid.UUID], **kwargs) -> list[Match]:
        """Create multiple matches for a user with different grants."""
        return [cls.create(user_id=user_id, grant_id=grant_id, **kwargs) for grant_id in grant_ids[:count]]

    @classmethod
    def create_high_score(cls, **kwargs) -> Match:
        """Create a high-scoring match."""
        return cls.create(match_score=0.95, predicted_success=0.85, **kwargs)

    @classmethod
    def create_low_score(cls, **kwargs) -> Match:
        """Create a low-scoring match."""
        return cls.create(match_score=0.35, predicted_success=0.25, **kwargs)


class GrantApplicationFactory:
    """Factory for creating GrantApplication instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        grant_id: Optional[uuid.UUID] = None,
        match_id: Optional[uuid.UUID] = None,
        stage: ApplicationStage = ApplicationStage.RESEARCHING,
        notes: Optional[str] = None,
        target_date: Optional[datetime] = None,
        **kwargs,
    ) -> GrantApplication:
        """Create a GrantApplication instance with defaults."""
        cls._counter += 1
        now = datetime.now(timezone.utc)

        return GrantApplication(
            id=id or uuid.uuid4(),
            user_id=user_id or uuid.uuid4(),
            grant_id=grant_id or uuid.uuid4(),
            match_id=match_id,
            stage=stage,
            notes=notes or f"Application notes for #{cls._counter}",
            target_date=target_date or (now + timedelta(days=14)),
            **kwargs,
        )

    @classmethod
    def create_pipeline(
        cls,
        user_id: uuid.UUID,
        grant_ids: list[uuid.UUID],
        stages: Optional[list[ApplicationStage]] = None,
    ) -> list[GrantApplication]:
        """Create a full pipeline with applications at different stages."""
        if stages is None:
            stages = list(ApplicationStage)

        applications = []
        for i, grant_id in enumerate(grant_ids):
            stage = stages[i % len(stages)]
            applications.append(
                cls.create(
                    user_id=user_id,
                    grant_id=grant_id,
                    stage=stage,
                )
            )
        return applications


class SavedSearchFactory:
    """Factory for creating SavedSearch instances."""

    _counter = 0

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        name: Optional[str] = None,
        filters: Optional[dict] = None,
        alert_enabled: bool = False,
        **kwargs,
    ) -> SavedSearch:
        """Create a SavedSearch instance with defaults."""
        cls._counter += 1

        return SavedSearch(
            id=id or uuid.uuid4(),
            user_id=user_id or uuid.uuid4(),
            name=name or f"Saved Search {cls._counter}",
            filters=filters
            or {
                "source": ["grants_gov", "nsf"],
                "categories": ["machine_learning"],
                "amount_min": 50000,
                "amount_max": 500000,
            },
            alert_enabled=alert_enabled,
            **kwargs,
        )


class AlertSentFactory:
    """Factory for creating AlertSent instances."""

    _counter = 0

    CHANNELS = ["email", "sms", "push", "slack"]

    @classmethod
    def create(
        cls,
        id: Optional[uuid.UUID] = None,
        match_id: Optional[uuid.UUID] = None,
        channel: Optional[str] = None,
        sent_at: Optional[datetime] = None,
        opened_at: Optional[datetime] = None,
        clicked_at: Optional[datetime] = None,
        **kwargs,
    ) -> AlertSent:
        """Create an AlertSent instance with defaults."""
        cls._counter += 1
        now = datetime.now(timezone.utc)

        return AlertSent(
            id=id or uuid.uuid4(),
            match_id=match_id or uuid.uuid4(),
            channel=channel or cls.CHANNELS[cls._counter % len(cls.CHANNELS)],
            sent_at=sent_at or now,
            opened_at=opened_at,
            clicked_at=clicked_at,
            **kwargs,
        )
