"""
Tests for Funding Alerts API endpoints.
Tests preferences management, alert preview, and scheduled delivery.
"""
import pytest
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models import User, Grant, Match, Deadline, FundingAlertPreference, LabProfile
from backend.schemas.alerts import AlertFrequency
from backend.services.funding_alerts import FundingAlertsService


@pytest.fixture
def sample_alert_preferences():
    """Sample alert preferences data."""
    return {
        "enabled": True,
        "frequency": "weekly",
        "min_match_score": 75,
        "include_deadlines": True,
        "include_new_grants": True,
        "include_insights": True,
        "preferred_funders": ["NIH", "NSF"],
    }


@pytest.fixture
def mock_anthropic_insights():
    """Mock Anthropic response for insights generation."""
    return MagicMock(
        content=[MagicMock(text="""Based on your profile, here are key insights:
1. The NIH R01 deadline in 2 weeks should be your top priority
2. NSF has increased funding for computational biology
3. Consider the new K99/R00 mechanism for career development""")]
    )


class TestFundingAlertPreferences:
    """Tests for funding alert preferences management."""

    @pytest.mark.asyncio
    async def test_get_or_create_preferences_creates_new(self, async_session, db_user):
        """Test creating new preferences for user without existing ones."""
        service = FundingAlertsService()
        prefs = await service.get_or_create_preferences(async_session, db_user.id)

        assert prefs is not None
        assert prefs.user_id == db_user.id
        assert prefs.enabled == True  # Default
        assert prefs.frequency == "weekly"  # Default
        assert prefs.min_match_score == 70  # Default

    @pytest.mark.asyncio
    async def test_get_or_create_preferences_returns_existing(self, async_session, db_user):
        """Test returning existing preferences."""
        # Create preferences first
        existing = FundingAlertPreference(
            user_id=db_user.id,
            enabled=False,
            frequency="daily",
            min_match_score=80,
        )
        async_session.add(existing)
        await async_session.commit()

        service = FundingAlertsService()
        prefs = await service.get_or_create_preferences(async_session, db_user.id)

        assert prefs.enabled == False
        assert prefs.frequency == "daily"
        assert prefs.min_match_score == 80

    @pytest.mark.asyncio
    async def test_update_preferences(self, async_session, db_user):
        """Test updating alert preferences."""
        service = FundingAlertsService()

        # Create initial preferences
        await service.get_or_create_preferences(async_session, db_user.id)

        # Update preferences
        updated = await service.update_preferences(
            db=async_session,
            user_id=db_user.id,
            enabled=False,
            frequency=AlertFrequency.DAILY,
            min_match_score=90,
            include_insights=False,
            preferred_funders=["DOE", "DOD"],
        )

        assert updated.enabled == False
        assert updated.frequency == "daily"
        assert updated.min_match_score == 90
        assert updated.include_insights == False
        assert updated.preferred_funders == ["DOE", "DOD"]

    @pytest.mark.asyncio
    async def test_update_preferences_partial(self, async_session, db_user):
        """Test updating only some preferences."""
        service = FundingAlertsService()

        # Create initial preferences
        await service.get_or_create_preferences(async_session, db_user.id)

        # Update only frequency
        updated = await service.update_preferences(
            db=async_session,
            user_id=db_user.id,
            frequency=AlertFrequency.MONTHLY,
        )

        assert updated.frequency == "monthly"
        assert updated.enabled == True  # Unchanged
        assert updated.min_match_score == 70  # Unchanged


class TestAlertPreview:
    """Tests for alert preview generation."""

    @pytest.mark.asyncio
    async def test_preview_with_disabled_alerts(self, async_session, db_user):
        """Test preview when alerts are disabled."""
        # Create disabled preferences
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=False,
        )
        async_session.add(prefs)
        await async_session.commit()

        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        assert preview.would_send == False
        assert "disabled" in preview.reason.lower()
        assert len(preview.new_grants) == 0
        assert len(preview.upcoming_deadlines) == 0

    @pytest.mark.asyncio
    async def test_preview_with_no_content(self, async_session, db_user):
        """Test preview when there's no content to send."""
        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        assert preview.would_send == False
        assert "no" in preview.reason.lower()

    @pytest.mark.asyncio
    async def test_preview_includes_new_grants(self, async_session, db_user, db_grant):
        """Test preview includes new matching grants."""
        # Create a match with high score (0.85 = 85% match)
        match = Match(
            user_id=db_user.id,
            grant_id=db_grant.id,
            match_score=0.85,  # 85% match score (0-1 scale)
            reasoning="Strong alignment with research areas",
            created_at=datetime.now(timezone.utc),  # Recent
        )
        async_session.add(match)
        await async_session.commit()

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = MagicMock(
                content=[MagicMock(text="Focus on the high-scoring NIH grant.")]
            )

            service = FundingAlertsService()
            service.client = mock_client.return_value
            preview = await service.preview_alert(async_session, db_user)

            assert preview.would_send == True
            assert len(preview.new_grants) >= 1
            assert preview.new_grants[0].match_score >= 70

    @pytest.mark.asyncio
    async def test_preview_includes_upcoming_deadlines(self, async_session, db_user):
        """Test preview includes upcoming deadlines."""
        # Create upcoming deadline
        deadline = Deadline(
            user_id=db_user.id,
            title="R01 Submission",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=14),
            status="active",
            priority="high",
            funder="NIH",
        )
        async_session.add(deadline)
        await async_session.commit()

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = MagicMock(
                content=[MagicMock(text="Don't miss the R01 deadline!")]
            )

            service = FundingAlertsService()
            service.client = mock_client.return_value
            preview = await service.preview_alert(async_session, db_user)

            assert preview.would_send == True
            assert len(preview.upcoming_deadlines) >= 1
            assert preview.upcoming_deadlines[0].days_until <= 30

    @pytest.mark.asyncio
    async def test_preview_respects_min_match_score(self, async_session, db_user, db_grant):
        """Test preview respects minimum match score filter."""
        # Create preferences with high threshold
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=True,
            min_match_score=90,  # 90% threshold
        )
        async_session.add(prefs)

        # Create match below threshold (0.75 = 75%, below 90%)
        match = Match(
            user_id=db_user.id,
            grant_id=db_grant.id,
            match_score=0.75,  # 75% - below 90% threshold
            created_at=datetime.now(timezone.utc),
        )
        async_session.add(match)
        await async_session.commit()

        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        # Grant should not be included due to low score
        assert len(preview.new_grants) == 0

    @pytest.mark.asyncio
    async def test_preview_respects_preferred_funders(self, async_session, db_user):
        """Test preview filters by preferred funders."""
        # Create preferences with funder filter
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=True,
            preferred_funders=["NIH"],
        )
        async_session.add(prefs)

        # Create grants from different funders (using 'agency' field as per model)
        nih_grant = Grant(
            title="NIH Research Grant",
            agency="NIH",  # Using 'agency' field, not 'funder'
            source="nih",
            external_id="NIH-001",
        )
        nsf_grant = Grant(
            title="NSF Research Grant",
            agency="NSF",
            source="nsf",
            external_id="NSF-001",
        )
        async_session.add_all([nih_grant, nsf_grant])
        await async_session.flush()

        # Create matches for both with recent timestamps
        for grant in [nih_grant, nsf_grant]:
            match = Match(
                user_id=db_user.id,
                grant_id=grant.id,
                match_score=0.85,  # 85% match (0-1 scale)
                created_at=datetime.now(timezone.utc),
            )
            async_session.add(match)
        await async_session.commit()

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = MagicMock(
                content=[MagicMock(text="Focus on NIH opportunities.")]
            )

            service = FundingAlertsService()
            service.client = mock_client.return_value
            preview = await service.preview_alert(async_session, db_user)

            # Should only include NIH grants
            for grant in preview.new_grants:
                assert grant.funder == "NIH"


class TestAlertEmailGeneration:
    """Tests for email HTML generation."""

    def test_generate_email_html_with_grants(self):
        """Test email generation includes grant summaries."""
        from backend.schemas.alerts import AlertGrantSummary, AlertDeadlineSummary, FundingAlertPreview

        user = MagicMock(spec=User)
        user.name = "Dr. Smith"

        preview = FundingAlertPreview(
            new_grants=[
                AlertGrantSummary(
                    id=uuid4(),
                    title="Cancer Research Grant",
                    funder="NIH",
                    mechanism="R01",
                    amount_max=500000,
                    deadline=datetime.now(timezone.utc) + timedelta(days=30),
                    match_score=92,
                    match_reason="Strong alignment",
                )
            ],
            upcoming_deadlines=[],
            personalized_insights="Focus on the R01 opportunity.",
            would_send=True,
            reason=None,
        )

        service = FundingAlertsService()
        html = service.generate_email_html(user, preview)

        assert "Dr. Smith" in html
        assert "Cancer Research Grant" in html
        assert "NIH" in html
        assert "R01" in html
        assert "92%" in html

    def test_generate_email_html_with_deadlines(self):
        """Test email generation includes deadline summaries."""
        from backend.schemas.alerts import AlertGrantSummary, AlertDeadlineSummary, FundingAlertPreview

        user = MagicMock(spec=User)
        user.name = "Researcher"

        preview = FundingAlertPreview(
            new_grants=[],
            upcoming_deadlines=[
                AlertDeadlineSummary(
                    id=uuid4(),
                    title="R01 Deadline",
                    funder="NIH",
                    sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=7),
                    days_until=7,
                    priority="high",
                )
            ],
            personalized_insights=None,
            would_send=True,
            reason=None,
        )

        service = FundingAlertsService()
        html = service.generate_email_html(user, preview)

        assert "R01 Deadline" in html
        assert "7 days" in html

    def test_generate_email_html_with_insights(self):
        """Test email generation includes AI insights."""
        from backend.schemas.alerts import FundingAlertPreview

        user = MagicMock(spec=User)
        user.name = "Researcher"

        preview = FundingAlertPreview(
            new_grants=[],
            upcoming_deadlines=[],
            personalized_insights="Consider applying for the K99 mechanism for career development.",
            would_send=True,
            reason=None,
        )

        service = FundingAlertsService()
        html = service.generate_email_html(user, preview)

        assert "K99 mechanism" in html
        assert "Insights" in html


class TestInsightsGeneration:
    """Tests for AI insights generation."""

    @pytest.mark.asyncio
    async def test_generate_insights_with_content(
        self, async_session, db_user, mock_anthropic_insights
    ):
        """Test insights generation with grants and deadlines."""
        from backend.schemas.alerts import AlertGrantSummary, AlertDeadlineSummary

        grants = [
            AlertGrantSummary(
                id=uuid4(),
                title="Test Grant",
                funder="NIH",
                mechanism="R01",
                amount_max=500000,
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                match_score=85,
                match_reason="Good match",
            )
        ]
        deadlines = [
            AlertDeadlineSummary(
                id=uuid4(),
                title="Important Deadline",
                funder="NIH",
                sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=14),
                days_until=14,
                priority="high",
            )
        ]

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.return_value = mock_anthropic_insights

            service = FundingAlertsService()
            service.client = mock_client.return_value

            insights = await service._generate_insights(
                async_session, db_user, grants, deadlines
            )

            assert insights is not None
            assert len(insights) > 0

    @pytest.mark.asyncio
    async def test_generate_insights_handles_api_error(self, async_session, db_user):
        """Test insights generation handles API errors gracefully."""
        from backend.schemas.alerts import AlertGrantSummary

        grants = [
            AlertGrantSummary(
                id=uuid4(),
                title="Test Grant",
                funder="NIH",
                mechanism="R01",
                amount_max=500000,
                deadline=None,
                match_score=85,
                match_reason="Good match",
            )
        ]

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            mock_client.return_value.messages.create.side_effect = Exception("API Error")

            service = FundingAlertsService()
            service.client = mock_client.return_value

            insights = await service._generate_insights(
                async_session, db_user, grants, []
            )

            # Should return None on error, not raise
            assert insights is None

    @pytest.mark.asyncio
    async def test_generate_insights_without_client(self, async_session, db_user):
        """Test insights generation returns None when client is not configured."""
        from backend.schemas.alerts import AlertGrantSummary

        grants = [
            AlertGrantSummary(
                id=uuid4(),
                title="Test Grant",
                funder="NIH",
                mechanism="R01",
                amount_max=500000,
                deadline=None,
                match_score=85,
                match_reason="Good match",
            )
        ]

        service = FundingAlertsService()
        service.client = None  # No client configured

        insights = await service._generate_insights(
            async_session, db_user, grants, []
        )

        # Should return None when no client configured
        assert insights is None


class TestPreferencesWithLabProfile:
    """Tests for alert generation with lab profile context."""

    @pytest.mark.asyncio
    async def test_insights_include_profile_context(self, async_session, db_user):
        """Test that insights generation includes user profile context."""
        from backend.schemas.alerts import AlertGrantSummary

        # Create a lab profile for the user
        profile = LabProfile(
            user_id=db_user.id,
            research_areas=["Machine Learning", "Healthcare AI"],
            career_stage="early_career",
        )
        async_session.add(profile)
        await async_session.commit()

        grants = [
            AlertGrantSummary(
                id=uuid4(),
                title="AI Healthcare Grant",
                funder="NIH",
                mechanism="K99",
                amount_max=300000,
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                match_score=90,
                match_reason="Strong alignment with ML and healthcare focus",
            )
        ]

        with patch('backend.services.funding_alerts.anthropic.Anthropic') as mock_client:
            # Check that the prompt includes profile information
            captured_prompt = None

            def capture_create(**kwargs):
                nonlocal captured_prompt
                captured_prompt = kwargs.get('messages', [{}])[0].get('content', '')
                return MagicMock(
                    content=[MagicMock(text="Based on your ML background, consider the K99.")]
                )

            mock_client.return_value.messages.create.side_effect = capture_create

            service = FundingAlertsService()
            service.client = mock_client.return_value

            insights = await service._generate_insights(
                async_session, db_user, grants, []
            )

            # Verify profile context was included in the prompt
            assert "Machine Learning" in captured_prompt or "early_career" in captured_prompt


class TestAlertDeliveryFilters:
    """Tests for alert content filtering logic."""

    @pytest.mark.asyncio
    async def test_exclude_deadlines_when_disabled(self, async_session, db_user):
        """Test that deadlines are excluded when include_deadlines is False."""
        # Create preferences with deadlines disabled
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=True,
            include_deadlines=False,
            include_new_grants=True,
        )
        async_session.add(prefs)

        # Create an upcoming deadline
        deadline = Deadline(
            user_id=db_user.id,
            title="Should Not Appear",
            sponsor_deadline=datetime.now(timezone.utc) + timedelta(days=10),
            status="active",
            priority="high",
        )
        async_session.add(deadline)
        await async_session.commit()

        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        # Deadlines should be empty since include_deadlines is False
        assert len(preview.upcoming_deadlines) == 0

    @pytest.mark.asyncio
    async def test_exclude_grants_when_disabled(self, async_session, db_user, db_grant):
        """Test that grants are excluded when include_new_grants is False."""
        # Create preferences with grants disabled
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=True,
            include_deadlines=True,
            include_new_grants=False,
        )
        async_session.add(prefs)

        # Create a matching grant
        match = Match(
            user_id=db_user.id,
            grant_id=db_grant.id,
            match_score=0.90,
            created_at=datetime.now(timezone.utc),
        )
        async_session.add(match)
        await async_session.commit()

        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        # Grants should be empty since include_new_grants is False
        assert len(preview.new_grants) == 0

    @pytest.mark.asyncio
    async def test_filter_old_matches(self, async_session, db_user, db_grant):
        """Test that old matches are not included in alerts."""
        # Create preferences
        prefs = FundingAlertPreference(
            user_id=db_user.id,
            enabled=True,
            last_sent_at=datetime.now(timezone.utc) - timedelta(days=1),  # Sent yesterday
        )
        async_session.add(prefs)

        # Create an old match (before last_sent_at)
        old_match = Match(
            user_id=db_user.id,
            grant_id=db_grant.id,
            match_score=0.90,
            created_at=datetime.now(timezone.utc) - timedelta(days=3),  # 3 days ago
        )
        async_session.add(old_match)
        await async_session.commit()

        service = FundingAlertsService()
        preview = await service.preview_alert(async_session, db_user)

        # Old match should not be included
        assert len(preview.new_grants) == 0


class TestFrequencySettings:
    """Tests for alert frequency settings."""

    @pytest.mark.asyncio
    async def test_daily_frequency_setting(self, async_session, db_user):
        """Test setting daily alert frequency."""
        service = FundingAlertsService()

        updated = await service.update_preferences(
            db=async_session,
            user_id=db_user.id,
            frequency=AlertFrequency.DAILY,
        )

        assert updated.frequency == "daily"

    @pytest.mark.asyncio
    async def test_weekly_frequency_setting(self, async_session, db_user):
        """Test setting weekly alert frequency."""
        service = FundingAlertsService()

        updated = await service.update_preferences(
            db=async_session,
            user_id=db_user.id,
            frequency=AlertFrequency.WEEKLY,
        )

        assert updated.frequency == "weekly"

    @pytest.mark.asyncio
    async def test_monthly_frequency_setting(self, async_session, db_user):
        """Test setting monthly alert frequency."""
        service = FundingAlertsService()

        updated = await service.update_preferences(
            db=async_session,
            user_id=db_user.id,
            frequency=AlertFrequency.MONTHLY,
        )

        assert updated.frequency == "monthly"
