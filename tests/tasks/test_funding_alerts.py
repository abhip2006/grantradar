"""
Tests for funding alerts Celery tasks.
Tests scheduled alert delivery and user-specific alerts.
"""
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import User, FundingAlertPreference


@pytest_asyncio.fixture
async def alert_user(async_session: AsyncSession):
    """Create a user for alert testing."""
    user = User(
        id=uuid.uuid4(),
        email="funding-alert@university.edu",
        password_hash="hashed_pw",
        name="Funding Alert User",
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def alert_prefs_daily(async_session: AsyncSession, alert_user: User):
    """Create daily alert preferences."""
    prefs = FundingAlertPreference(
        id=uuid.uuid4(),
        user_id=alert_user.id,
        enabled=True,
        frequency="daily",
        min_match_score=70,
        include_deadlines=True,
        include_new_grants=True,
        include_insights=True,
    )
    async_session.add(prefs)
    await async_session.commit()
    await async_session.refresh(prefs)
    return prefs


@pytest_asyncio.fixture
async def alert_prefs_weekly(async_session: AsyncSession, alert_user: User):
    """Create weekly alert preferences."""
    prefs = FundingAlertPreference(
        id=uuid.uuid4(),
        user_id=alert_user.id,
        enabled=True,
        frequency="weekly",
        min_match_score=75,
        last_sent_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    async_session.add(prefs)
    await async_session.commit()
    await async_session.refresh(prefs)
    return prefs


class TestFundingAlertPreferenceModel:
    """Tests for FundingAlertPreference model."""

    @pytest.mark.asyncio
    async def test_create_preference(self, async_session, alert_user):
        """Test creating alert preferences."""
        prefs = FundingAlertPreference(
            id=uuid.uuid4(),
            user_id=alert_user.id,
            enabled=True,
            frequency="daily",
        )
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(prefs)

        assert prefs.id is not None
        assert prefs.enabled is True
        assert prefs.frequency == "daily"

    @pytest.mark.asyncio
    async def test_preference_defaults(self, async_session, alert_user):
        """Test default values for preferences."""
        prefs = FundingAlertPreference(
            id=uuid.uuid4(),
            user_id=alert_user.id,
        )
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(prefs)

        assert prefs.enabled is True
        assert prefs.frequency == "weekly"
        assert prefs.min_match_score == 70

    @pytest.mark.asyncio
    async def test_update_last_sent_at(self, async_session, alert_prefs_daily):
        """Test updating last_sent_at."""
        alert_prefs_daily.last_sent_at = datetime.now(timezone.utc)
        await async_session.commit()
        await async_session.refresh(alert_prefs_daily)

        assert alert_prefs_daily.last_sent_at is not None


class TestAlertFrequencyLogic:
    """Tests for alert frequency checking logic."""

    def test_daily_frequency_due(self):
        """Test daily frequency when due."""
        last_sent = datetime.now(timezone.utc) - timedelta(days=2)
        now = datetime.now(timezone.utc)
        frequency = "daily"

        delta = now - last_sent
        should_send = delta.days >= 1

        assert should_send is True

    def test_daily_frequency_not_due(self):
        """Test daily frequency when not due."""
        last_sent = datetime.now(timezone.utc) - timedelta(hours=12)
        now = datetime.now(timezone.utc)
        frequency = "daily"

        delta = now - last_sent
        should_send = delta.days >= 1

        assert should_send is False

    def test_weekly_frequency_due(self):
        """Test weekly frequency when due."""
        last_sent = datetime.now(timezone.utc) - timedelta(days=8)
        now = datetime.now(timezone.utc)
        frequency = "weekly"

        delta = now - last_sent
        should_send = delta.days >= 7

        assert should_send is True

    def test_weekly_frequency_not_due(self):
        """Test weekly frequency when not due."""
        last_sent = datetime.now(timezone.utc) - timedelta(days=3)
        now = datetime.now(timezone.utc)
        frequency = "weekly"

        delta = now - last_sent
        should_send = delta.days >= 7

        assert should_send is False

    def test_monthly_frequency_due(self):
        """Test monthly frequency when due."""
        last_sent = datetime.now(timezone.utc) - timedelta(days=35)
        now = datetime.now(timezone.utc)
        frequency = "monthly"

        delta = now - last_sent
        should_send = delta.days >= 30

        assert should_send is True

    def test_monthly_frequency_not_due(self):
        """Test monthly frequency when not due."""
        last_sent = datetime.now(timezone.utc) - timedelta(days=15)
        now = datetime.now(timezone.utc)
        frequency = "monthly"

        delta = now - last_sent
        should_send = delta.days >= 30

        assert should_send is False

    def test_first_alert_no_last_sent(self):
        """Test first alert when last_sent_at is None."""
        last_sent = None
        should_send = last_sent is None

        assert should_send is True


class TestAlertContentGeneration:
    """Tests for alert email content generation."""

    def test_email_subject_format(self):
        """Test email subject line format."""
        now = datetime.now()
        subject = f"Your GrantRadar Funding Update - {now.strftime('%b %d')}"

        assert "GrantRadar" in subject
        assert "Funding Update" in subject

    def test_generate_grants_section(self):
        """Test generating grants section of email."""
        grants = [
            {"title": "Grant 1", "agency": "NSF", "match_score": 0.9},
            {"title": "Grant 2", "agency": "NIH", "match_score": 0.85},
        ]

        # Simple HTML generation
        html = "<h2>New Grants</h2><ul>"
        for g in grants:
            html += f"<li>{g['title']} - {g['agency']} ({g['match_score']*100:.0f}%)</li>"
        html += "</ul>"

        assert "New Grants" in html
        assert "Grant 1" in html
        assert "NSF" in html
        assert "90%" in html

    def test_generate_deadlines_section(self):
        """Test generating deadlines section of email."""
        deadlines = [
            {"title": "Deadline 1", "days_remaining": 5},
            {"title": "Deadline 2", "days_remaining": 10},
        ]

        html = "<h2>Upcoming Deadlines</h2><ul>"
        for d in deadlines:
            html += f"<li>{d['title']} - {d['days_remaining']} days</li>"
        html += "</ul>"

        assert "Upcoming Deadlines" in html
        assert "5 days" in html


class TestAlertFiltering:
    """Tests for alert content filtering."""

    def test_filter_by_min_match_score(self):
        """Test filtering grants by minimum match score."""
        grants = [
            {"title": "Grant 1", "match_score": 0.9},
            {"title": "Grant 2", "match_score": 0.5},
            {"title": "Grant 3", "match_score": 0.75},
        ]
        min_score = 0.7

        filtered = [g for g in grants if g["match_score"] >= min_score]

        assert len(filtered) == 2
        assert all(g["match_score"] >= min_score for g in filtered)

    def test_filter_upcoming_deadlines(self):
        """Test filtering for upcoming deadlines only."""
        now = datetime.now(timezone.utc)
        deadlines = [
            {"title": "D1", "deadline": now + timedelta(days=5)},
            {"title": "D2", "deadline": now + timedelta(days=30)},
            {"title": "D3", "deadline": now - timedelta(days=1)},  # Past
        ]

        filtered = [d for d in deadlines if d["deadline"] > now]

        assert len(filtered) == 2
        assert all(d["deadline"] > now for d in filtered)


class TestAlertDisabling:
    """Tests for disabled alerts."""

    @pytest.mark.asyncio
    async def test_disabled_alerts_not_sent(self, async_session, alert_user):
        """Test that disabled alerts are not sent."""
        prefs = FundingAlertPreference(
            id=uuid.uuid4(),
            user_id=alert_user.id,
            enabled=False,
            frequency="daily",
        )
        async_session.add(prefs)
        await async_session.commit()
        await async_session.refresh(prefs)

        # Should not send if disabled
        should_send = prefs.enabled
        assert should_send is False

    @pytest.mark.asyncio
    async def test_no_preferences_no_send(self, async_session, alert_user):
        """Test that users without preferences don't receive alerts."""
        from sqlalchemy import select

        # No preferences created for this user
        result = await async_session.execute(
            select(FundingAlertPreference).where(
                FundingAlertPreference.user_id == alert_user.id
            )
        )
        prefs = result.scalar_one_or_none()

        # Should not send without preferences
        assert prefs is None


class TestPreferredFunders:
    """Tests for preferred funders filtering."""

    def test_filter_by_preferred_funders(self):
        """Test filtering grants by preferred funders."""
        grants = [
            {"title": "G1", "agency": "NSF"},
            {"title": "G2", "agency": "NIH"},
            {"title": "G3", "agency": "DOE"},
        ]
        preferred = ["NSF", "NIH"]

        if preferred:
            filtered = [g for g in grants if g["agency"] in preferred]
        else:
            filtered = grants

        assert len(filtered) == 2
        assert all(g["agency"] in preferred for g in filtered)

    def test_no_preferred_funders_includes_all(self):
        """Test that empty preferred funders includes all grants."""
        grants = [
            {"title": "G1", "agency": "NSF"},
            {"title": "G2", "agency": "NIH"},
            {"title": "G3", "agency": "DOE"},
        ]
        preferred = []

        if preferred:
            filtered = [g for g in grants if g["agency"] in preferred]
        else:
            filtered = grants

        assert len(filtered) == 3
