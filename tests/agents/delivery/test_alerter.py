"""
Tests for Alert Delivery Agent.
Tests priority determination, channel selection, and alert routing.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from agents.delivery.alerter import AlertDeliveryAgent
from agents.delivery.models import (
    AlertPriority,
    DeliveryChannel,
    UserNotificationPreferences,
)


class TestPriorityDetermination:
    """Tests for alert priority determination."""

    def test_critical_priority_high_score_urgent_deadline(self):
        """Test CRITICAL priority for >95% match + <14 days deadline."""
        agent = AlertDeliveryAgent()
        deadline = datetime.utcnow() + timedelta(days=7)

        priority = agent.determine_priority(0.96, deadline)

        assert priority == AlertPriority.CRITICAL

    def test_high_priority_85_to_95_percent(self):
        """Test HIGH priority for 85-95% match."""
        agent = AlertDeliveryAgent()

        assert agent.determine_priority(0.85, None) == AlertPriority.HIGH
        assert agent.determine_priority(0.90, None) == AlertPriority.HIGH
        assert agent.determine_priority(0.95, None) == AlertPriority.HIGH

    def test_medium_priority_70_to_85_percent(self):
        """Test MEDIUM priority for 70-85% match."""
        agent = AlertDeliveryAgent()

        assert agent.determine_priority(0.70, None) == AlertPriority.MEDIUM
        assert agent.determine_priority(0.75, None) == AlertPriority.MEDIUM
        assert agent.determine_priority(0.84, None) == AlertPriority.MEDIUM

    def test_low_priority_below_70_percent(self):
        """Test LOW priority for <70% match."""
        agent = AlertDeliveryAgent()

        assert agent.determine_priority(0.69, None) == AlertPriority.LOW
        assert agent.determine_priority(0.50, None) == AlertPriority.LOW
        assert agent.determine_priority(0.30, None) == AlertPriority.LOW

    def test_high_score_long_deadline_not_critical(self):
        """Test that high score with long deadline is not CRITICAL."""
        agent = AlertDeliveryAgent()
        deadline = datetime.utcnow() + timedelta(days=30)

        # 90% match but deadline > 14 days (in HIGH range 85-95%)
        priority = agent.determine_priority(0.90, deadline)

        # Should be HIGH (not CRITICAL) because deadline is too far
        assert priority == AlertPriority.HIGH


class TestChannelDetermination:
    """Tests for delivery channel determination."""

    def test_critical_priority_all_channels(self):
        """Test CRITICAL priority enables SMS + Email + Slack."""
        agent = AlertDeliveryAgent()

        channels = agent.determine_channels(AlertPriority.CRITICAL)

        assert DeliveryChannel.SMS in channels
        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SLACK in channels

    def test_high_priority_email_slack(self):
        """Test HIGH priority enables Email + Slack."""
        agent = AlertDeliveryAgent()

        channels = agent.determine_channels(AlertPriority.HIGH)

        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SLACK in channels
        assert DeliveryChannel.SMS not in channels

    def test_medium_priority_email_only(self):
        """Test MEDIUM priority enables Email only."""
        agent = AlertDeliveryAgent()

        channels = agent.determine_channels(AlertPriority.MEDIUM)

        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SMS not in channels
        assert DeliveryChannel.SLACK not in channels

    def test_low_priority_no_channels(self):
        """Test LOW priority returns no channels."""
        agent = AlertDeliveryAgent()

        channels = agent.determine_channels(AlertPriority.LOW)

        assert len(channels) == 0

    def test_user_preferences_disable_channels(self):
        """Test that user preferences can disable channels."""
        agent = AlertDeliveryAgent()
        preferences = UserNotificationPreferences(
            email_notifications=True,
            sms_notifications=False,  # Disabled
            slack_notifications=False,  # Disabled
        )

        channels = agent.determine_channels(AlertPriority.CRITICAL, preferences)

        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SMS not in channels
        assert DeliveryChannel.SLACK not in channels

    def test_user_preferences_all_disabled(self):
        """Test that all channels disabled returns empty list."""
        agent = AlertDeliveryAgent()
        preferences = UserNotificationPreferences(
            email_notifications=False,
            sms_notifications=False,
            slack_notifications=False,
        )

        channels = agent.determine_channels(AlertPriority.HIGH, preferences)

        assert len(channels) == 0


class TestDigestBatching:
    """Tests for digest batching logic."""

    def test_should_batch_medium_priority_over_threshold(self, mock_redis_client):
        """Test batching when >3 medium alerts in a day."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client
        mock_redis_client.llen.return_value = 4  # >3 alerts

        user_id = uuid4()
        should_batch = agent.should_batch_for_digest(user_id, AlertPriority.MEDIUM)

        assert should_batch is True

    def test_should_not_batch_medium_below_threshold(self, mock_redis_client):
        """Test no batching when <3 medium alerts in a day."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client
        mock_redis_client.llen.return_value = 2  # <3 alerts

        user_id = uuid4()
        should_batch = agent.should_batch_for_digest(user_id, AlertPriority.MEDIUM)

        assert should_batch is False

    def test_should_not_batch_high_priority(self, mock_redis_client):
        """Test that HIGH priority is never batched."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        user_id = uuid4()
        should_batch = agent.should_batch_for_digest(user_id, AlertPriority.HIGH)

        assert should_batch is False

    def test_should_not_batch_critical_priority(self, mock_redis_client):
        """Test that CRITICAL priority is never batched."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        user_id = uuid4()
        should_batch = agent.should_batch_for_digest(user_id, AlertPriority.CRITICAL)

        assert should_batch is False

    def test_add_to_digest_batch(self, mock_redis_client, sample_alert_payload):
        """Test adding alert to digest batch."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        agent.add_to_digest_batch(sample_alert_payload)

        mock_redis_client.lpush.assert_called_once()
        mock_redis_client.expireat.assert_called_once()


class TestContentGeneration:
    """Tests for content generation methods."""

    def test_generate_sms_content(self, sample_grant_info, sample_match_info):
        """Test SMS content generation."""
        agent = AlertDeliveryAgent()

        sms = agent.generate_sms_content(
            sample_grant_info,
            sample_match_info,
            "https://gr.ai/x123",
        )

        assert "GrantRadar Alert" in sms.message
        assert "88%" in sms.message
        assert len(sms.message) <= 160

    def test_generate_sms_content_truncates_long_title(self, sample_grant_info, sample_match_info):
        """Test that long grant titles are truncated in SMS."""
        agent = AlertDeliveryAgent()
        sample_grant_info.title = "A" * 100  # Very long title

        sms = agent.generate_sms_content(
            sample_grant_info,
            sample_match_info,
            "https://gr.ai/x123",
        )

        assert len(sms.message) <= 160
        assert "..." in sms.message

    def test_generate_slack_blocks(self, sample_user_info, sample_grant_info, sample_match_info):
        """Test Slack block generation."""
        agent = AlertDeliveryAgent()

        blocks = agent.generate_slack_blocks(
            sample_user_info,
            sample_grant_info,
            sample_match_info,
        )

        assert len(blocks) > 0
        assert blocks[0]["type"] == "header"
        assert "88%" in blocks[0]["text"]["text"]


class TestAlertSending:
    """Tests for alert sending."""

    @pytest.mark.asyncio
    @patch("agents.delivery.alerter.get_sendgrid_channel")
    async def test_send_alert_email_success(self, mock_get_sendgrid, sample_alert_payload, mock_redis_client):
        """Test successful email sending."""
        # Setup mocks
        mock_sendgrid = MagicMock()
        mock_status = MagicMock()
        mock_status.channel = DeliveryChannel.EMAIL
        mock_status.status = "sent"
        mock_status.sent_at = datetime.utcnow()
        mock_status.provider_message_id = "sg-123"
        mock_status.error_message = None
        mock_status.alert_id = uuid4()
        mock_sendgrid.send = AsyncMock(return_value=mock_status)
        mock_get_sendgrid.return_value = mock_sendgrid

        # Configure payload for email only
        sample_alert_payload.channels = [DeliveryChannel.EMAIL]

        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client
        agent._anthropic_client = MagicMock()
        agent._anthropic_client.messages.create.return_value = MagicMock(content=[MagicMock(text="Test subject")])

        statuses = await agent.send_alert(sample_alert_payload)

        assert len(statuses) == 1
        assert statuses[0].status == "sent"

    @pytest.mark.asyncio
    async def test_send_alert_channel_failure_logged(self, sample_alert_payload, mock_redis_client):
        """Test that channel failures are logged but don't stop other channels."""
        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        # Configure for email only and patch to raise exception
        sample_alert_payload.channels = [DeliveryChannel.EMAIL]

        with patch("agents.delivery.alerter.get_sendgrid_channel") as mock_get:
            mock_get.return_value.send = AsyncMock(side_effect=Exception("Send failed"))

            with patch.object(agent, "_anthropic_client") as mock_anthropic:
                mock_anthropic.messages.create.return_value = MagicMock(content=[MagicMock(text="Subject")])

                statuses = await agent.send_alert(sample_alert_payload)

        assert len(statuses) == 1
        assert statuses[0].status == "failed"


class TestAlertLogging:
    """Tests for alert logging to Redis."""

    def test_log_alert_sent_creates_redis_entry(self, mock_redis_client, sample_alert_payload):
        """Test that sent alerts are logged to Redis."""
        from tests.agents.delivery.conftest import create_delivery_status

        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        status = create_delivery_status(DeliveryChannel.EMAIL, "sent", sample_alert_payload.match_id)

        # Patch db persistence to avoid async issues
        with patch.object(agent, "_persist_alert_to_db", new_callable=AsyncMock):
            agent._log_alert_sent(sample_alert_payload, [status])

        mock_redis_client.hset.assert_called()
        mock_redis_client.expire.assert_called()

    def test_log_alert_calculates_latency(self, mock_redis_client, sample_alert_payload):
        """Test that latency is calculated when posted_at is available."""
        from tests.agents.delivery.conftest import create_delivery_status

        agent = AlertDeliveryAgent()
        agent._redis_client = mock_redis_client

        # Ensure grant has posted_at
        sample_alert_payload.grant.posted_at = datetime.utcnow() - timedelta(minutes=5)

        status = create_delivery_status(DeliveryChannel.EMAIL, "sent", sample_alert_payload.match_id)
        status.sent_at = datetime.utcnow()

        with patch.object(agent, "_persist_alert_to_db", new_callable=AsyncMock):
            with patch.object(agent, "logger") as mock_logger:
                agent._log_alert_sent(sample_alert_payload, [status])

        # Check that latency was logged
        mock_logger.info.assert_called()
