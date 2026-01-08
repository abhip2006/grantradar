"""
Tests for Digest Email Generation.
Tests batching logic and digest email content generation.
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4

from agents.delivery.alerter import AlertDeliveryAgent, process_digest_batch
from agents.delivery.models import (
    AlertPayload,
    AlertPriority,
    DeliveryChannel,
    EmailContent,
    GrantInfo,
    MatchInfo,
    UserInfo,
)


class TestDigestEmailGeneration:
    """Tests for digest email generation."""

    @pytest.mark.asyncio
    async def test_generate_digest_email_single_alert(
        self, sample_alert_payload, mock_anthropic_client
    ):
        """Test digest email generation with single alert."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alert_payload.user,
                [sample_alert_payload],
            )

        assert content is not None
        assert "New grant match" in content.subject
        assert sample_alert_payload.grant.title in content.body_html
        assert "88%" in content.body_html

    @pytest.mark.asyncio
    async def test_generate_digest_email_multiple_alerts(
        self, sample_alerts_for_digest, mock_anthropic_client
    ):
        """Test digest email generation with multiple alerts."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alerts_for_digest[0].user,
                sample_alerts_for_digest,
            )

        assert content is not None
        assert f"{len(sample_alerts_for_digest)} new grant matches" in content.subject
        # Should contain all grants
        for alert in sample_alerts_for_digest:
            assert alert.grant.title in content.body_html

    @pytest.mark.asyncio
    async def test_generate_digest_email_sorts_by_score(
        self, sample_alerts_for_digest, mock_anthropic_client
    ):
        """Test that digest sorts alerts by match score descending."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alerts_for_digest[0].user,
                sample_alerts_for_digest,
            )

        # First grant in HTML should be the highest score (95%)
        first_grant_pos = content.body_html.find("Research Grant 1")
        second_grant_pos = content.body_html.find("Research Grant 2")
        assert first_grant_pos < second_grant_pos

    @pytest.mark.asyncio
    async def test_generate_digest_email_limits_to_10_grants(
        self, sample_user_info, mock_anthropic_client
    ):
        """Test that digest limits to 10 grants."""
        # Create 15 alerts
        alerts = []
        for i in range(15):
            grant = GrantInfo(
                grant_id=uuid4(),
                title=f"Grant {i+1}",
                description=f"Description {i+1}",
                funding_agency="NSF",
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                url=f"https://example.com/grant/{i+1}",
            )
            match = MatchInfo(
                match_id=uuid4(),
                match_score=0.90 - (i * 0.01),
            )
            alerts.append(
                AlertPayload(
                    match_id=match.match_id,
                    user=sample_user_info,
                    grant=grant,
                    match=match,
                    priority=AlertPriority.HIGH,
                    channels=[DeliveryChannel.EMAIL],
                )
            )

        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_user_info,
                alerts,
            )

        # Should contain notice about showing top 10
        assert "Showing top 10" in content.body_html
        # Should contain first 10 grants
        for i in range(10):
            assert f"Grant {i+1}" in content.body_html
        # Should not contain grants 11-15
        assert "Grant 11" not in content.body_html

    @pytest.mark.asyncio
    async def test_generate_digest_email_empty_alerts(self, sample_user_info):
        """Test that empty alerts returns None."""
        agent = AlertDeliveryAgent()

        content = await agent._generate_digest_email_content(
            sample_user_info,
            [],
        )

        assert content is None

    @pytest.mark.asyncio
    async def test_generate_digest_email_llm_failure_fallback(
        self, sample_alert_payload
    ):
        """Test fallback when LLM fails to generate intro."""
        agent = AlertDeliveryAgent()
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("LLM error")
        agent._anthropic_client = mock_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alert_payload.user,
                [sample_alert_payload],
            )

        # Should still generate email with fallback intro
        assert content is not None
        assert "we found" in content.body_text.lower()


class TestSendDigestEmail:
    """Tests for sending digest emails."""

    @pytest.mark.asyncio
    async def test_send_digest_email_success(
        self, sample_alerts_for_digest, mock_anthropic_client
    ):
        """Test successful digest email sending."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        mock_status = MagicMock()
        mock_status.status = "sent"

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            with patch("agents.delivery.alerter.get_sendgrid_channel") as mock_sendgrid:
                mock_sendgrid.return_value.send = AsyncMock(return_value=mock_status)

                status = await agent._send_digest_email(sample_alerts_for_digest)

        assert status is not None
        assert status.status == "sent"

    @pytest.mark.asyncio
    async def test_send_digest_email_empty_alerts(self):
        """Test that empty alerts returns None."""
        agent = AlertDeliveryAgent()

        status = await agent._send_digest_email([])

        assert status is None

    @pytest.mark.asyncio
    async def test_send_digest_email_generation_failure(
        self, sample_alerts_for_digest
    ):
        """Test handling when digest generation fails."""
        agent = AlertDeliveryAgent()

        with patch.object(
            agent, "_generate_digest_email_content", new_callable=AsyncMock
        ) as mock_gen:
            mock_gen.return_value = None

            status = await agent._send_digest_email(sample_alerts_for_digest)

        assert status is None


class TestProcessDigestBatch:
    """Tests for the process_digest_batch Celery task."""

    def test_process_digest_batch_no_alerts(self, mock_redis_client):
        """Test processing when no alerts are batched."""
        with patch("agents.delivery.alerter.AlertDeliveryAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.redis_client = mock_redis_client
            mock_agent.DIGEST_KEY_PREFIX = "digest:pending:"
            mock_redis_client.lrange.return_value = []
            mock_agent_class.return_value = mock_agent

            result = process_digest_batch("user-123", "2025-01-08")

        assert result["alerts_processed"] == 0

    def test_process_digest_batch_with_alerts(
        self, mock_redis_client, sample_alert_payload
    ):
        """Test processing with batched alerts."""
        with patch("agents.delivery.alerter.AlertDeliveryAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.redis_client = mock_redis_client
            mock_agent.DIGEST_KEY_PREFIX = "digest:pending:"

            # Mock Redis returning alert data
            mock_redis_client.lrange.return_value = [
                sample_alert_payload.model_dump_json()
            ]

            # Mock the send method
            mock_status = MagicMock()
            mock_status.status = "sent"
            mock_agent._send_digest_email = AsyncMock(return_value=mock_status)

            mock_agent_class.return_value = mock_agent

            result = process_digest_batch(
                str(sample_alert_payload.user.user_id),
                "2025-01-08",
            )

        assert result["alerts_processed"] == 1
        mock_redis_client.delete.assert_called_once()


class TestDigestPlainText:
    """Tests for plain text digest generation."""

    @pytest.mark.asyncio
    async def test_plain_text_includes_all_grants(
        self, sample_alerts_for_digest, mock_anthropic_client
    ):
        """Test that plain text includes all grant info."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alerts_for_digest[0].user,
                sample_alerts_for_digest,
            )

        # Check plain text contains grant titles
        for alert in sample_alerts_for_digest:
            assert alert.grant.title in content.body_text

        # Check plain text contains URLs
        for alert in sample_alerts_for_digest:
            assert alert.grant.url in content.body_text

    @pytest.mark.asyncio
    async def test_plain_text_includes_scores(
        self, sample_alerts_for_digest, mock_anthropic_client
    ):
        """Test that plain text includes match scores."""
        agent = AlertDeliveryAgent()
        agent._anthropic_client = mock_anthropic_client

        with patch("agents.delivery.alerter.settings") as mock_settings:
            mock_settings.llm_model = "claude-3-haiku-20240307"
            mock_settings.from_email = "alerts@grantradar.com"
            mock_settings.from_name = "GrantRadar"
            mock_settings.frontend_url = "https://grantradar.com"

            content = await agent._generate_digest_email_content(
                sample_alerts_for_digest[0].user,
                sample_alerts_for_digest,
            )

        # Check plain text contains match percentages
        assert "95% match" in content.body_text
        assert "90% match" in content.body_text
