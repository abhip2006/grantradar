"""
Tests for Delivery Channels.
Tests SendGrid, Twilio, and Slack channel implementations.
"""
import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from agents.delivery.channels import (
    SendGridChannel,
    TwilioChannel,
    SlackChannel,
    get_sendgrid_channel,
    get_twilio_channel,
    get_slack_channel,
)
from agents.delivery.models import (
    DeliveryChannel,
    EmailContent,
    SMSContent,
    SlackContent,
)


class TestSendGridChannel:
    """Tests for SendGrid email channel."""

    def test_is_configured_with_api_key(self):
        """Test is_configured returns True when API key is set."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.test_key"
            channel = SendGridChannel()
            assert channel.is_configured() is True

    def test_is_configured_without_api_key(self):
        """Test is_configured returns False when API key is missing."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.sendgrid_api_key = None
            channel = SendGridChannel()
            assert channel.is_configured() is False

    def test_build_message_includes_tracking(self, sample_email_content):
        """Test that built message includes tracking settings."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.test_key"
            channel = SendGridChannel()

            message = channel._build_message(sample_email_content)

            assert message.tracking_settings is not None

    def test_is_retryable_error_timeout(self):
        """Test that timeout errors are retryable."""
        channel = SendGridChannel()

        assert channel._is_retryable_error(Exception("Connection timeout")) is True
        assert channel._is_retryable_error(Exception("timeout error")) is True

    def test_is_retryable_error_rate_limit(self):
        """Test that rate limit errors are retryable."""
        channel = SendGridChannel()

        assert channel._is_retryable_error(Exception("429 Too Many Requests")) is True

    def test_is_retryable_error_server_error(self):
        """Test that server errors are retryable."""
        channel = SendGridChannel()

        assert channel._is_retryable_error(Exception("500 Internal Server Error")) is True
        assert channel._is_retryable_error(Exception("503 Service Unavailable")) is True

    def test_is_not_retryable_validation_error(self):
        """Test that validation errors are not retryable."""
        channel = SendGridChannel()

        assert channel._is_retryable_error(Exception("Invalid email address")) is False

    @pytest.mark.asyncio
    async def test_send_success(self, sample_email_content, mock_sendgrid_response):
        """Test successful email sending."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.test_key"
            channel = SendGridChannel()

            with patch.object(channel, "_send_sync", return_value=mock_sendgrid_response):
                status = await channel.send(sample_email_content)

        assert status.status == "sent"
        assert status.provider_message_id == "sg-msg-12345"
        assert status.channel == DeliveryChannel.EMAIL

    @pytest.mark.asyncio
    async def test_send_build_message_failure(self, sample_email_content):
        """Test handling of message build failure."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.sendgrid_api_key = "SG.test_key"
            channel = SendGridChannel()

            with patch.object(channel, "_build_message", side_effect=Exception("Build failed")):
                status = await channel.send(sample_email_content)

        assert status.status == "failed"
        assert "Build failed" in status.error_message


class TestTwilioChannel:
    """Tests for Twilio SMS channel."""

    def test_is_configured_with_credentials(self):
        """Test is_configured returns True when all credentials are set."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.twilio_account_sid = "AC123"
            mock_settings.twilio_auth_token = "token123"
            mock_settings.twilio_phone_number = "+15551234567"
            channel = TwilioChannel()
            assert channel.is_configured() is True

    def test_is_configured_missing_credentials(self):
        """Test is_configured returns False when credentials are missing."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.twilio_account_sid = None
            mock_settings.twilio_auth_token = None
            mock_settings.twilio_phone_number = None
            channel = TwilioChannel()
            assert channel.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_success(self, sample_sms_content, mock_twilio_message):
        """Test successful SMS sending."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.twilio_account_sid = "AC123"
            mock_settings.twilio_auth_token = "token123"
            mock_settings.twilio_phone_number = "+15551234567"
            mock_settings.backend_url = "https://api.grantradar.com"

            channel = TwilioChannel()
            mock_client = MagicMock()
            mock_client.messages.create.return_value = mock_twilio_message
            channel._client = mock_client

            status = await channel.send(sample_sms_content)

        assert status.status == "sent"
        assert status.provider_message_id == mock_twilio_message.sid
        assert status.channel == DeliveryChannel.SMS

    @pytest.mark.asyncio
    async def test_send_twilio_exception(self, sample_sms_content):
        """Test handling of Twilio API exception."""
        from twilio.base.exceptions import TwilioRestException

        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.twilio_account_sid = "AC123"
            mock_settings.twilio_auth_token = "token123"
            mock_settings.twilio_phone_number = "+15551234567"
            mock_settings.backend_url = "https://api.grantradar.com"

            channel = TwilioChannel()
            mock_client = MagicMock()
            mock_client.messages.create.side_effect = TwilioRestException(
                status=400, uri="/Messages", msg="Invalid phone number"
            )
            channel._client = mock_client

            status = await channel.send(sample_sms_content)

        assert status.status == "failed"
        assert status.error_message is not None


class TestSlackChannel:
    """Tests for Slack webhook channel."""

    def test_is_configured_with_webhook_url(self):
        """Test is_configured returns True when webhook URL is set."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.slack_webhook_url = "https://hooks.slack.com/services/..."
            channel = SlackChannel()
            assert channel.is_configured() is True

    def test_is_configured_without_webhook_url(self):
        """Test is_configured returns False when webhook URL is missing."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.slack_webhook_url = None
            channel = SlackChannel()
            assert channel.is_configured() is False

    @pytest.mark.asyncio
    async def test_send_success(self, sample_slack_content, mock_slack_response):
        """Test successful Slack message sending."""
        channel = SlackChannel()

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_slack_response
        channel._http_client = mock_client

        status = await channel.send(sample_slack_content)

        assert status.status == "delivered"
        assert status.delivered_at is not None
        assert status.channel == DeliveryChannel.SLACK

    @pytest.mark.asyncio
    async def test_send_no_webhook_url(self):
        """Test handling when no webhook URL is provided."""
        with patch("agents.delivery.channels.settings") as mock_settings:
            mock_settings.slack_webhook_url = None

            channel = SlackChannel()
            content = SlackContent(
                webhook_url="",  # Empty URL
                text="Test message",
            )

            status = await channel.send(content)

        assert status.status == "failed"
        assert "No Slack webhook URL" in status.error_message

    @pytest.mark.asyncio
    async def test_send_rate_limited(self, sample_slack_content):
        """Test handling of Slack rate limiting."""
        channel = SlackChannel()

        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "1"}
        mock_response.text = "rate_limited"

        mock_client = AsyncMock()
        # Return rate limited response twice, then fail
        mock_client.post.return_value = mock_response
        channel._http_client = mock_client

        status = await channel.send(sample_slack_content)

        assert status.status == "failed"
        assert status.retry_count > 0

    @pytest.mark.asyncio
    async def test_send_timeout_retry(self, sample_slack_content, mock_slack_response):
        """Test retry on timeout."""
        import httpx

        channel = SlackChannel()

        mock_client = AsyncMock()
        # First call times out, second succeeds
        mock_client.post.side_effect = [
            httpx.TimeoutException("Timeout"),
            mock_slack_response,
        ]
        channel._http_client = mock_client

        status = await channel.send(sample_slack_content)

        assert status.status == "delivered"
        assert status.retry_count == 1

    @pytest.mark.asyncio
    async def test_close_releases_client(self):
        """Test that close() releases the HTTP client."""
        channel = SlackChannel()
        # Initialize the client
        _ = channel.http_client

        mock_client = channel._http_client
        mock_client.aclose = AsyncMock()

        await channel.close()

        mock_client.aclose.assert_called_once()
        assert channel._http_client is None


class TestChannelSingletons:
    """Tests for channel singleton getters."""

    def test_get_sendgrid_channel_returns_same_instance(self):
        """Test that get_sendgrid_channel returns singleton."""
        # Reset singleton
        import agents.delivery.channels as channels_module
        channels_module._sendgrid_channel = None

        channel1 = get_sendgrid_channel()
        channel2 = get_sendgrid_channel()

        assert channel1 is channel2

    def test_get_twilio_channel_returns_same_instance(self):
        """Test that get_twilio_channel returns singleton."""
        import agents.delivery.channels as channels_module
        channels_module._twilio_channel = None

        channel1 = get_twilio_channel()
        channel2 = get_twilio_channel()

        assert channel1 is channel2

    def test_get_slack_channel_returns_same_instance(self):
        """Test that get_slack_channel returns singleton."""
        import agents.delivery.channels as channels_module
        channels_module._slack_channel = None

        channel1 = get_slack_channel()
        channel2 = get_slack_channel()

        assert channel1 is channel2
