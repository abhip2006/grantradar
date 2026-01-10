"""
Delivery agent test fixtures.
Provides mock data and utilities for testing delivery components.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from uuid import UUID, uuid4

from agents.delivery.models import (
    AlertPayload,
    AlertPriority,
    DeliveryChannel,
    DeliveryStatus,
    EmailContent,
    GrantInfo,
    MatchInfo,
    SMSContent,
    SlackContent,
    UserInfo,
    UserNotificationPreferences,
)


@pytest.fixture
def sample_user_info():
    """Sample user info for delivery tests."""
    return UserInfo(
        user_id=uuid4(),
        name="Dr. Jane Smith",
        email="jane.smith@stanford.edu",
        phone="+14155551234",
        slack_webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
        alert_preferences={},
    )


@pytest.fixture
def sample_grant_info():
    """Sample grant info for delivery tests."""
    return GrantInfo(
        grant_id=uuid4(),
        title="Machine Learning for Climate Science Research",
        description="Developing novel ML approaches for climate prediction and modeling.",
        funding_agency="National Science Foundation",
        amount_min=500000,
        amount_max=750000,
        deadline=datetime.now(timezone.utc) + timedelta(days=30),
        url="https://www.nsf.gov/funding/grants/12345",
        categories=["ai_ml", "climate"],
        eligibility_criteria=["Universities", "Research Institutions"],
        posted_at=datetime.now(timezone.utc) - timedelta(hours=2),
    )


@pytest.fixture
def sample_match_info():
    """Sample match info for delivery tests."""
    return MatchInfo(
        match_id=uuid4(),
        match_score=0.88,
        matching_criteria=["ML expertise", "Climate research background"],
        explanation="Strong alignment with your machine learning and climate research expertise.",
    )


@pytest.fixture
def sample_alert_payload(sample_user_info, sample_grant_info, sample_match_info):
    """Complete alert payload for testing."""
    return AlertPayload(
        match_id=sample_match_info.match_id,
        user=sample_user_info,
        grant=sample_grant_info,
        match=sample_match_info,
        priority=AlertPriority.HIGH,
        channels=[DeliveryChannel.EMAIL, DeliveryChannel.SLACK],
    )


@pytest.fixture
def sample_notification_preferences():
    """Sample user notification preferences."""
    return UserNotificationPreferences(
        email_notifications=True,
        sms_notifications=True,
        slack_notifications=True,
        digest_frequency="immediate",
        minimum_match_score=0.7,
    )


@pytest.fixture
def sample_email_content():
    """Sample email content for testing."""
    return EmailContent(
        subject="New Grant Match: 88%",
        body_html="<html><body>Grant match content</body></html>",
        body_text="Grant match content",
        from_email="alerts@grantradar.com",
        from_name="GrantRadar",
        to_email="jane.smith@stanford.edu",
        to_name="Dr. Jane Smith",
        tracking_id=str(uuid4()),
    )


@pytest.fixture
def sample_sms_content():
    """Sample SMS content for testing."""
    return SMSContent(
        message="GrantRadar Alert: ML for Climate matches 88%. Deadline: 02/07. View: https://gr.ai/x123",
        phone_number="+14155551234",
        short_url="https://gr.ai/x123",
    )


@pytest.fixture
def sample_slack_content():
    """Sample Slack content for testing."""
    return SlackContent(
        webhook_url="https://hooks.slack.com/services/T00/B00/XXX",
        text="New 88% grant match: ML for Climate Science",
        blocks=[
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "New Grant Match: 88%"},
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "*ML for Climate Science*\nNSF"},
            },
        ],
    )


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for delivery tests."""
    redis = MagicMock()
    redis.lpush = MagicMock(return_value=1)
    redis.lrange = MagicMock(return_value=[])
    redis.llen = MagicMock(return_value=0)
    redis.hset = MagicMock(return_value=True)
    redis.expire = MagicMock(return_value=True)
    redis.expireat = MagicMock(return_value=True)
    redis.delete = MagicMock(return_value=1)
    redis.keys = MagicMock(return_value=[])
    redis.xgroup_create = MagicMock()
    redis.xreadgroup = MagicMock(return_value=[])
    redis.xack = MagicMock(return_value=1)
    return redis


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic client for content generation."""
    client = MagicMock()
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Generated email content")]
    client.messages.create = MagicMock(return_value=mock_response)
    return client


@pytest.fixture
def mock_sendgrid_response():
    """Mock SendGrid API response."""
    response = MagicMock()
    response.status_code = 202
    response.headers = {"X-Message-Id": "sg-msg-12345"}
    return response


@pytest.fixture
def mock_twilio_message():
    """Mock Twilio message response."""
    message = MagicMock()
    message.sid = "SM12345678901234567890123456789012"
    message.status = "queued"
    return message


@pytest.fixture
def mock_slack_response():
    """Mock Slack webhook response."""
    response = MagicMock()
    response.status_code = 200
    response.text = "ok"
    return response


# =============================================================================
# Multiple alerts for digest testing
# =============================================================================


@pytest.fixture
def sample_alerts_for_digest(sample_user_info):
    """Multiple alert payloads for digest testing."""
    alerts = []
    # Use explicit scores to avoid floating point issues
    scores = [0.95, 0.90, 0.85, 0.80, 0.75]
    for i in range(5):
        grant = GrantInfo(
            grant_id=uuid4(),
            title=f"Research Grant {i + 1}",
            description=f"Description for grant {i + 1}",
            funding_agency=["NSF", "NIH", "DOE", "DARPA", "NASA"][i],
            amount_min=100000 * (i + 1),
            amount_max=200000 * (i + 1),
            deadline=datetime.now(timezone.utc) + timedelta(days=30 + i * 10),
            url=f"https://example.com/grant/{i + 1}",
            categories=["research"],
            posted_at=datetime.now(timezone.utc) - timedelta(hours=i + 1),
        )
        match = MatchInfo(
            match_id=uuid4(),
            match_score=scores[i],  # 95%, 90%, 85%, 80%, 75%
            matching_criteria=["Expertise match"],
            explanation=f"Good fit for grant {i + 1}",
        )
        alerts.append(
            AlertPayload(
                match_id=match.match_id,
                user=sample_user_info,
                grant=grant,
                match=match,
                priority=AlertPriority.HIGH if match.match_score >= 0.85 else AlertPriority.MEDIUM,
                channels=[DeliveryChannel.EMAIL],
            )
        )
    return alerts


# =============================================================================
# Helper functions
# =============================================================================


def create_delivery_status(
    channel: DeliveryChannel,
    status: str = "sent",
    match_id: UUID = None,
) -> DeliveryStatus:
    """Create a delivery status for testing."""
    return DeliveryStatus(
        alert_id=uuid4(),
        match_id=match_id or uuid4(),
        channel=channel,
        status=status,
        sent_at=datetime.utcnow() if status == "sent" else None,
    )
