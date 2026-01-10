"""
Tests for core event models.
Tests all event types used in the Redis Streams event system.
"""

import uuid
from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from backend.core.events import (
    PriorityLevel,
    AlertChannel,
    BaseEvent,
    GrantDiscoveredEvent,
    GrantValidatedEvent,
    MatchComputedEvent,
    AlertPendingEvent,
    DeadLetterEvent,
    WebSocketEvent,
    NewMatchEvent,
    DeadlineReminderEvent,
    GrantUpdateEvent,
    StatsUpdateEvent,
)


class TestPriorityLevel:
    """Tests for PriorityLevel enum."""

    def test_priority_values(self):
        """Test priority level values."""
        assert PriorityLevel.CRITICAL == "critical"
        assert PriorityLevel.HIGH == "high"
        assert PriorityLevel.MEDIUM == "medium"
        assert PriorityLevel.LOW == "low"

    def test_all_priorities_exist(self):
        """Test all priority levels are defined."""
        assert len(PriorityLevel) == 4


class TestAlertChannel:
    """Tests for AlertChannel enum."""

    def test_channel_values(self):
        """Test alert channel values."""
        assert AlertChannel.EMAIL == "email"
        assert AlertChannel.SMS == "sms"
        assert AlertChannel.PUSH == "push"
        assert AlertChannel.WEBSOCKET == "websocket"

    def test_all_channels_exist(self):
        """Test all channels are defined."""
        assert len(AlertChannel) == 4


class TestBaseEvent:
    """Tests for BaseEvent model."""

    def test_create_base_event(self):
        """Test creating a base event with required fields."""
        event_id = uuid.uuid4()
        event = BaseEvent(event_id=event_id)

        assert event.event_id == event_id
        assert event.version == "1.0"
        assert event.timestamp is not None

    def test_base_event_default_timestamp(self):
        """Test that timestamp is auto-generated."""
        event_id = uuid.uuid4()
        before = datetime.utcnow()
        event = BaseEvent(event_id=event_id)
        after = datetime.utcnow()

        assert before <= event.timestamp <= after

    def test_base_event_custom_timestamp(self):
        """Test setting custom timestamp."""
        event_id = uuid.uuid4()
        custom_time = datetime(2025, 1, 1, 12, 0, 0)
        event = BaseEvent(event_id=event_id, timestamp=custom_time)

        assert event.timestamp == custom_time

    def test_base_event_custom_version(self):
        """Test setting custom version."""
        event_id = uuid.uuid4()
        event = BaseEvent(event_id=event_id, version="2.0")

        assert event.version == "2.0"

    def test_base_event_json_serialization(self):
        """Test JSON serialization of base event."""
        event_id = uuid.uuid4()
        event = BaseEvent(event_id=event_id)
        json_data = event.model_dump_json()

        assert str(event_id) in json_data
        assert "1.0" in json_data


class TestGrantDiscoveredEvent:
    """Tests for GrantDiscoveredEvent model."""

    def test_create_minimal_event(self):
        """Test creating event with required fields only."""
        event = GrantDiscoveredEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            source="grants.gov",
            title="Test Grant",
            url="https://grants.gov/test",
        )

        assert event.source == "grants.gov"
        assert event.title == "Test Grant"
        assert event.url == "https://grants.gov/test"
        assert event.funding_agency is None
        assert event.estimated_amount is None

    def test_create_full_event(self):
        """Test creating event with all fields."""
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        event = GrantDiscoveredEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            source="nih_reporter",
            title="NIH Research Grant",
            url="https://nih.gov/grants/test",
            funding_agency="NIH",
            estimated_amount=500000.0,
            deadline=deadline,
            raw_data={"key": "value"},
        )

        assert event.funding_agency == "NIH"
        assert event.estimated_amount == 500000.0
        assert event.deadline == deadline
        assert event.raw_data == {"key": "value"}

    def test_discovered_at_default(self):
        """Test discovered_at defaults to now."""
        event = GrantDiscoveredEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            source="test",
            title="Test",
            url="https://test.com",
        )

        assert event.discovered_at is not None

    def test_missing_required_fields(self):
        """Test validation error for missing required fields."""
        with pytest.raises(ValidationError):
            GrantDiscoveredEvent(event_id=uuid.uuid4())


class TestGrantValidatedEvent:
    """Tests for GrantValidatedEvent model."""

    def test_create_validated_event(self):
        """Test creating a validated event."""
        event = GrantValidatedEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            quality_score=0.85,
            categories=["research", "science"],
            embedding_generated=True,
        )

        assert event.quality_score == 0.85
        assert event.categories == ["research", "science"]
        assert event.embedding_generated is True

    def test_quality_score_bounds(self):
        """Test quality score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            GrantValidatedEvent(
                event_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                quality_score=1.5,
            )

        with pytest.raises(ValidationError):
            GrantValidatedEvent(
                event_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                quality_score=-0.1,
            )

    def test_optional_fields(self):
        """Test optional fields have correct defaults."""
        event = GrantValidatedEvent(
            event_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            quality_score=0.5,
        )

        assert event.categories == []
        assert event.embedding_generated is False
        assert event.validation_details is None
        assert event.eligibility_criteria is None
        assert event.keywords is None


class TestMatchComputedEvent:
    """Tests for MatchComputedEvent model."""

    def test_create_match_event(self):
        """Test creating a match computed event."""
        event = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            match_score=0.87,
            priority_level=PriorityLevel.HIGH,
        )

        assert event.match_score == 0.87
        assert event.priority_level == PriorityLevel.HIGH

    def test_match_score_bounds(self):
        """Test match score must be between 0 and 1."""
        with pytest.raises(ValidationError):
            MatchComputedEvent(
                event_id=uuid.uuid4(),
                match_id=uuid.uuid4(),
                grant_id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                match_score=1.1,
                priority_level=PriorityLevel.HIGH,
            )

    def test_full_match_event(self):
        """Test match event with all optional fields."""
        deadline = datetime.now(timezone.utc) + timedelta(days=14)
        event = MatchComputedEvent(
            event_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            grant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            match_score=0.92,
            priority_level=PriorityLevel.CRITICAL,
            matching_criteria=["research_area", "career_stage"],
            explanation="Strong match based on profile",
            grant_deadline=deadline,
        )

        assert event.matching_criteria == ["research_area", "career_stage"]
        assert event.explanation == "Strong match based on profile"
        assert event.grant_deadline == deadline


class TestAlertPendingEvent:
    """Tests for AlertPendingEvent model."""

    def test_create_email_alert(self):
        """Test creating an email alert event."""
        event = AlertPendingEvent(
            event_id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=AlertChannel.EMAIL,
            user_email="test@university.edu",
            alert_title="New Grant Match",
            alert_body="A new grant matches your profile.",
        )

        assert event.channel == AlertChannel.EMAIL
        assert event.user_email == "test@university.edu"
        assert event.retry_count == 0
        assert event.max_retries == 3

    def test_create_sms_alert(self):
        """Test creating an SMS alert event."""
        event = AlertPendingEvent(
            event_id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=AlertChannel.SMS,
            user_phone="+15551234567",
        )

        assert event.channel == AlertChannel.SMS
        assert event.user_phone == "+15551234567"

    def test_create_push_alert(self):
        """Test creating a push notification alert."""
        user_id = uuid.uuid4()
        event = AlertPendingEvent(
            event_id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=AlertChannel.PUSH,
            user_id=user_id,
        )

        assert event.channel == AlertChannel.PUSH
        assert event.user_id == user_id


class TestDeadLetterEvent:
    """Tests for DeadLetterEvent model."""

    def test_create_dlq_event(self):
        """Test creating a dead letter event."""
        first_failure = datetime.now(timezone.utc) - timedelta(minutes=30)
        event = DeadLetterEvent(
            event_id=uuid.uuid4(),
            original_stream="grants:discovered",
            original_message_id="1234567890-0",
            original_payload={"grant_id": "test"},
            error_message="Connection timeout",
            error_type="ConnectionError",
            failure_count=3,
            first_failure_at=first_failure,
        )

        assert event.original_stream == "grants:discovered"
        assert event.original_message_id == "1234567890-0"
        assert event.failure_count == 3
        assert event.error_type == "ConnectionError"


class TestWebSocketEvent:
    """Tests for WebSocketEvent base model."""

    def test_create_websocket_event(self):
        """Test creating a websocket event."""
        event = WebSocketEvent()

        assert event.timestamp is not None


class TestNewMatchEvent:
    """Tests for NewMatchEvent model."""

    def test_create_new_match_event(self):
        """Test creating a new match websocket event."""
        deadline = datetime.now(timezone.utc) + timedelta(days=30)
        event = NewMatchEvent(
            grant_id=uuid.uuid4(),
            title="AI Research Grant",
            match_score=0.89,
            deadline=deadline,
            agency="NSF",
            amount_range="$100,000 - $500,000",
        )

        assert event.title == "AI Research Grant"
        assert event.match_score == 0.89
        assert event.agency == "NSF"
        assert event.amount_range == "$100,000 - $500,000"

    def test_match_score_bounds(self):
        """Test match score validation."""
        with pytest.raises(ValidationError):
            NewMatchEvent(
                grant_id=uuid.uuid4(),
                title="Test",
                match_score=1.5,
            )


class TestDeadlineReminderEvent:
    """Tests for DeadlineReminderEvent model."""

    def test_create_deadline_reminder(self):
        """Test creating a deadline reminder event."""
        deadline = datetime.now(timezone.utc) + timedelta(days=3)
        event = DeadlineReminderEvent(
            grant_id=uuid.uuid4(),
            title="NIH R01 Grant",
            days_remaining=3,
            deadline=deadline,
            url="https://grants.nih.gov/test",
        )

        assert event.title == "NIH R01 Grant"
        assert event.days_remaining == 3
        assert event.deadline == deadline
        assert event.url == "https://grants.nih.gov/test"

    def test_days_remaining_non_negative(self):
        """Test days_remaining must be non-negative."""
        with pytest.raises(ValidationError):
            DeadlineReminderEvent(
                grant_id=uuid.uuid4(),
                title="Test",
                days_remaining=-1,
                deadline=datetime.now(timezone.utc),
            )


class TestGrantUpdateEvent:
    """Tests for GrantUpdateEvent model."""

    def test_create_grant_update_event(self):
        """Test creating a grant update event."""
        event = GrantUpdateEvent(
            grant_id=uuid.uuid4(),
            title="Updated Grant",
            update_type="deadline_changed",
            changes={
                "deadline": {
                    "old": "2025-03-01",
                    "new": "2025-04-01",
                }
            },
            message="Deadline extended by one month",
        )

        assert event.update_type == "deadline_changed"
        assert event.changes["deadline"]["new"] == "2025-04-01"
        assert event.message == "Deadline extended by one month"


class TestStatsUpdateEvent:
    """Tests for StatsUpdateEvent model."""

    def test_create_stats_update_event(self):
        """Test creating a stats update event."""
        event = StatsUpdateEvent(
            new_grants_count=5,
            high_matches_count=3,
            pending_deadlines_count=2,
            total_saved_count=25,
        )

        assert event.new_grants_count == 5
        assert event.high_matches_count == 3
        assert event.pending_deadlines_count == 2
        assert event.total_saved_count == 25

    def test_stats_default_values(self):
        """Test default values for stats."""
        event = StatsUpdateEvent()

        assert event.new_grants_count == 0
        assert event.high_matches_count == 0
        assert event.pending_deadlines_count == 0
        assert event.total_saved_count is None

    def test_stats_non_negative(self):
        """Test stats values must be non-negative."""
        with pytest.raises(ValidationError):
            StatsUpdateEvent(new_grants_count=-1)

        with pytest.raises(ValidationError):
            StatsUpdateEvent(high_matches_count=-1)
