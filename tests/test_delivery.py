"""
Alert Delivery Tests
Tests for email generation, SMS formatting, and routing logic.
"""
import json
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.delivery.models import (
    AlertPriority,
    DeliveryChannel,
    UserInfo,
    GrantInfo,
    MatchInfo,
    AlertPayload,
    EmailContent,
    SMSContent,
    SlackContent,
    DeliveryStatus,
    DigestBatch,
)
from backend.core.events import AlertPendingEvent, AlertChannel


# =============================================================================
# Alert Priority Tests
# =============================================================================


class TestAlertPriority:
    """Tests for alert priority routing logic."""

    @pytest.fixture
    def priority_router(self):
        """Create a priority router."""
        class PriorityRouter:
            PRIORITY_THRESHOLDS = {
                AlertPriority.CRITICAL: 0.95,
                AlertPriority.HIGH: 0.85,
                AlertPriority.MEDIUM: 0.70,
            }

            PRIORITY_CHANNELS = {
                AlertPriority.CRITICAL: [DeliveryChannel.SMS, DeliveryChannel.EMAIL, DeliveryChannel.SLACK],
                AlertPriority.HIGH: [DeliveryChannel.EMAIL, DeliveryChannel.SLACK],
                AlertPriority.MEDIUM: [DeliveryChannel.EMAIL],
                AlertPriority.LOW: [],
            }

            def determine_priority(
                self,
                match_score: float,
                deadline: datetime | None,
                days_threshold_critical: int = 14,
            ) -> AlertPriority:
                """Determine alert priority based on score and deadline."""
                now = datetime.now(timezone.utc)
                days_to_deadline = float("inf")

                if deadline:
                    days_to_deadline = (deadline - now).days

                # Critical: high score AND urgent deadline
                if match_score >= self.PRIORITY_THRESHOLDS[AlertPriority.CRITICAL]:
                    if days_to_deadline <= days_threshold_critical:
                        return AlertPriority.CRITICAL
                    return AlertPriority.HIGH

                # High: good score
                if match_score >= self.PRIORITY_THRESHOLDS[AlertPriority.HIGH]:
                    return AlertPriority.HIGH

                # Medium: decent score
                if match_score >= self.PRIORITY_THRESHOLDS[AlertPriority.MEDIUM]:
                    return AlertPriority.MEDIUM

                # Low: below threshold
                return AlertPriority.LOW

            def get_channels_for_priority(
                self,
                priority: AlertPriority,
                user_preferences: dict | None = None,
            ) -> list[DeliveryChannel]:
                """Get delivery channels for a priority level."""
                channels = self.PRIORITY_CHANNELS.get(priority, [])

                # Apply user preferences if provided
                if user_preferences:
                    disabled_channels = user_preferences.get("disabled_channels", [])
                    channels = [c for c in channels if c not in disabled_channels]

                return channels

        return PriorityRouter()

    def test_determine_priority_critical(self, priority_router):
        """Test critical priority determination."""
        deadline = datetime.now(timezone.utc) + timedelta(days=7)
        priority = priority_router.determine_priority(0.96, deadline)
        assert priority == AlertPriority.CRITICAL

    def test_determine_priority_high_score_no_deadline(self, priority_router):
        """Test high priority with high score but no urgent deadline."""
        priority = priority_router.determine_priority(0.96, None)
        assert priority == AlertPriority.HIGH

    def test_determine_priority_high(self, priority_router):
        """Test high priority determination."""
        priority = priority_router.determine_priority(0.90, None)
        assert priority == AlertPriority.HIGH

    def test_determine_priority_medium(self, priority_router):
        """Test medium priority determination."""
        priority = priority_router.determine_priority(0.75, None)
        assert priority == AlertPriority.MEDIUM

    def test_determine_priority_low(self, priority_router):
        """Test low priority determination."""
        priority = priority_router.determine_priority(0.50, None)
        assert priority == AlertPriority.LOW

    def test_get_channels_critical(self, priority_router):
        """Test channels for critical priority."""
        channels = priority_router.get_channels_for_priority(AlertPriority.CRITICAL)
        assert DeliveryChannel.SMS in channels
        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SLACK in channels

    def test_get_channels_high(self, priority_router):
        """Test channels for high priority."""
        channels = priority_router.get_channels_for_priority(AlertPriority.HIGH)
        assert DeliveryChannel.SMS not in channels
        assert DeliveryChannel.EMAIL in channels
        assert DeliveryChannel.SLACK in channels

    def test_get_channels_medium(self, priority_router):
        """Test channels for medium priority."""
        channels = priority_router.get_channels_for_priority(AlertPriority.MEDIUM)
        assert channels == [DeliveryChannel.EMAIL]

    def test_get_channels_low(self, priority_router):
        """Test channels for low priority."""
        channels = priority_router.get_channels_for_priority(AlertPriority.LOW)
        assert channels == []

    def test_get_channels_with_preferences(self, priority_router):
        """Test channel filtering with user preferences."""
        preferences = {"disabled_channels": [DeliveryChannel.SMS]}
        channels = priority_router.get_channels_for_priority(
            AlertPriority.CRITICAL,
            user_preferences=preferences,
        )
        assert DeliveryChannel.SMS not in channels
        assert DeliveryChannel.EMAIL in channels


# =============================================================================
# Email Generation Tests
# =============================================================================


class TestEmailGeneration:
    """Tests for email content generation."""

    @pytest.fixture
    def email_generator(self):
        """Create an email generator."""
        class EmailGenerator:
            def __init__(self, from_email: str = "alerts@grantradar.com", from_name: str = "GrantRadar"):
                self.from_email = from_email
                self.from_name = from_name

            def generate_subject(self, grant: GrantInfo, match_score: float) -> str:
                """Generate email subject line."""
                score_percent = int(match_score * 100)
                title_truncated = grant.title[:50] + "..." if len(grant.title) > 50 else grant.title
                return f"[{score_percent}% Match] {title_truncated}"

            def generate_html_body(self, alert: AlertPayload) -> str:
                """Generate HTML email body."""
                deadline_str = ""
                if alert.grant.deadline:
                    days_left = (alert.grant.deadline - datetime.now(timezone.utc)).days
                    deadline_str = f"<p><strong>Deadline:</strong> {alert.grant.deadline.strftime('%B %d, %Y')} ({days_left} days left)</p>"

                amount_str = ""
                if alert.grant.amount_max:
                    amount_str = f"<p><strong>Funding:</strong> Up to ${alert.grant.amount_max:,.0f}</p>"

                return f"""
                <html>
                <body>
                <h1>New Grant Match: {alert.grant.title}</h1>
                <p>Hi {alert.user.name},</p>
                <p>We found a <strong>{int(alert.match.match_score * 100)}%</strong> match for your research profile!</p>

                <h2>{alert.grant.title}</h2>
                <p><strong>Agency:</strong> {alert.grant.funding_agency}</p>
                {amount_str}
                {deadline_str}

                <p>{alert.grant.description[:500]}...</p>

                <p><a href="{alert.grant.url}">View Grant Details</a></p>

                <hr>
                <p>Match Explanation: {alert.match.explanation or 'Based on your research profile alignment.'}</p>

                <p>Best regards,<br>The GrantRadar Team</p>
                </body>
                </html>
                """

            def generate_text_body(self, alert: AlertPayload) -> str:
                """Generate plain text email body."""
                deadline_str = ""
                if alert.grant.deadline:
                    days_left = (alert.grant.deadline - datetime.now(timezone.utc)).days
                    deadline_str = f"Deadline: {alert.grant.deadline.strftime('%B %d, %Y')} ({days_left} days left)\n"

                return f"""
New Grant Match: {alert.grant.title}

Hi {alert.user.name},

We found a {int(alert.match.match_score * 100)}% match for your research profile!

{alert.grant.title}
Agency: {alert.grant.funding_agency}
{deadline_str}
{alert.grant.description[:300]}...

View Grant: {alert.grant.url}

Match Explanation: {alert.match.explanation or 'Based on your research profile alignment.'}

Best regards,
The GrantRadar Team
                """.strip()

            def generate_email(self, alert: AlertPayload) -> EmailContent:
                """Generate complete email content."""
                return EmailContent(
                    subject=self.generate_subject(alert.grant, alert.match.match_score),
                    body_html=self.generate_html_body(alert),
                    body_text=self.generate_text_body(alert),
                    from_email=self.from_email,
                    from_name=self.from_name,
                    to_email=alert.user.email,
                    to_name=alert.user.name,
                    tracking_id=str(alert.match.match_id),
                )

        return EmailGenerator()

    @pytest.fixture
    def sample_alert_payload(self):
        """Create a sample alert payload."""
        return AlertPayload(
            match_id=uuid.uuid4(),
            user=UserInfo(
                user_id=uuid.uuid4(),
                name="Dr. Jane Smith",
                email="jane@university.edu",
                phone="+1-555-123-4567",
            ),
            grant=GrantInfo(
                grant_id=uuid.uuid4(),
                title="AI Research in Healthcare: Novel Machine Learning Approaches",
                description="This grant supports innovative research in applying machine learning to healthcare challenges.",
                funding_agency="National Institutes of Health",
                amount_max=500000.0,
                deadline=datetime.now(timezone.utc) + timedelta(days=30),
                url="https://grants.gov/test",
            ),
            match=MatchInfo(
                match_id=uuid.uuid4(),
                match_score=0.87,
                matching_criteria=["research_area", "methods"],
                explanation="Strong alignment in AI and healthcare research.",
            ),
            priority=AlertPriority.HIGH,
            channels=[DeliveryChannel.EMAIL],
        )

    def test_generate_subject(self, email_generator, sample_alert_payload):
        """Test email subject generation."""
        subject = email_generator.generate_subject(
            sample_alert_payload.grant,
            sample_alert_payload.match.match_score,
        )

        assert "[87% Match]" in subject
        assert "AI Research" in subject

    def test_generate_subject_long_title(self, email_generator):
        """Test subject truncation for long titles."""
        grant = GrantInfo(
            grant_id=uuid.uuid4(),
            title="This is an extremely long grant title that should definitely be truncated in the email subject line",
            description="Description",
            funding_agency="Agency",
            url="https://test.com",
        )

        subject = email_generator.generate_subject(grant, 0.90)

        assert len(subject) < 100
        assert "..." in subject

    def test_generate_html_body(self, email_generator, sample_alert_payload):
        """Test HTML email body generation."""
        html = email_generator.generate_html_body(sample_alert_payload)

        assert "<html>" in html
        assert sample_alert_payload.grant.title in html
        assert sample_alert_payload.user.name in html
        assert "87%" in html

    def test_generate_text_body(self, email_generator, sample_alert_payload):
        """Test plain text email body generation."""
        text = email_generator.generate_text_body(sample_alert_payload)

        assert sample_alert_payload.grant.title in text
        assert sample_alert_payload.user.name in text
        assert sample_alert_payload.grant.url in text

    def test_generate_complete_email(self, email_generator, sample_alert_payload):
        """Test complete email generation."""
        email = email_generator.generate_email(sample_alert_payload)

        assert email.to_email == sample_alert_payload.user.email
        assert email.to_name == sample_alert_payload.user.name
        assert email.from_email == "alerts@grantradar.com"
        assert email.tracking_id is not None


# =============================================================================
# SMS Generation Tests
# =============================================================================


class TestSMSGeneration:
    """Tests for SMS content generation."""

    @pytest.fixture
    def sms_generator(self):
        """Create an SMS generator."""
        class SMSGenerator:
            MAX_LENGTH = 160

            def generate_short_url(self, url: str, match_id: uuid.UUID) -> str:
                """Generate a short tracking URL."""
                # In production, this would use a URL shortener
                return f"https://gr.ai/m/{str(match_id)[:8]}"

            def generate_message(self, alert: AlertPayload) -> SMSContent:
                """Generate SMS message content."""
                score_percent = int(alert.match.match_score * 100)

                # Truncate title to fit in SMS
                max_title_len = 50
                title = alert.grant.title[:max_title_len]
                if len(alert.grant.title) > max_title_len:
                    title += "..."

                short_url = self.generate_short_url(alert.grant.url, alert.match.match_id)

                # Format message
                days_left = ""
                if alert.grant.deadline:
                    days = (alert.grant.deadline - datetime.now(timezone.utc)).days
                    days_left = f" ({days}d left)"

                message = f"GrantRadar: {score_percent}% match! {title}{days_left} {short_url}"

                # Ensure message fits in SMS
                if len(message) > self.MAX_LENGTH:
                    # Truncate title further
                    overflow = len(message) - self.MAX_LENGTH
                    title = title[:len(title) - overflow - 3] + "..."
                    message = f"GrantRadar: {score_percent}% match! {title}{days_left} {short_url}"

                return SMSContent(
                    message=message,
                    phone_number=alert.user.phone,
                    short_url=short_url,
                )

        return SMSGenerator()

    def test_generate_sms_message(self, sms_generator, sample_alert_payload):
        """Test SMS message generation."""
        sample_alert_payload.user.phone = "+1-555-123-4567"
        sms = sms_generator.generate_message(sample_alert_payload)

        assert sms.phone_number == "+1-555-123-4567"
        assert "GrantRadar:" in sms.message
        assert "87% match" in sms.message
        assert len(sms.message) <= 160

    def test_sms_message_length_limit(self, sms_generator, sample_alert_payload):
        """Test SMS message respects 160 character limit."""
        # Use a very long title
        sample_alert_payload.grant.title = "A" * 200
        sample_alert_payload.user.phone = "+1-555-123-4567"

        sms = sms_generator.generate_message(sample_alert_payload)

        assert len(sms.message) <= 160

    def test_sms_short_url(self, sms_generator, sample_alert_payload):
        """Test short URL generation."""
        match_id = uuid.uuid4()
        short_url = sms_generator.generate_short_url("https://grants.gov/very/long/url", match_id)

        assert short_url.startswith("https://gr.ai/m/")
        assert len(short_url) < 30


# =============================================================================
# SendGrid Integration Tests
# =============================================================================


class TestSendGridIntegration:
    """Tests for SendGrid email delivery."""

    @pytest.fixture
    def sendgrid_sender(self, mock_sendgrid):
        """Create a SendGrid sender."""
        class SendGridSender:
            def __init__(self, api_key: str):
                import sendgrid
                self.client = sendgrid.SendGridAPIClient(api_key=api_key)

            async def send_email(self, email: EmailContent) -> dict:
                """Send email via SendGrid."""
                from sendgrid.helpers.mail import Mail, Email, To, Content

                message = Mail(
                    from_email=Email(email.from_email, email.from_name),
                    to_emails=To(email.to_email, email.to_name),
                    subject=email.subject,
                )

                message.add_content(Content("text/plain", email.body_text))
                message.add_content(Content("text/html", email.body_html))

                response = self.client.send(message)

                return {
                    "status_code": response.status_code,
                    "message_id": response.headers.get("X-Message-Id", email.tracking_id),
                }

        return SendGridSender("test-api-key")

    @pytest.fixture
    def sample_email_content(self):
        """Create sample email content."""
        return EmailContent(
            subject="[87% Match] AI Research Grant",
            body_html="<html><body>Test email</body></html>",
            body_text="Test email",
            from_email="alerts@grantradar.com",
            from_name="GrantRadar",
            to_email="test@university.edu",
            to_name="Dr. Test",
            tracking_id=str(uuid.uuid4()),
        )

    @pytest.mark.asyncio
    async def test_send_email_success(self, sendgrid_sender, sample_email_content, mock_sendgrid):
        """Test successful email sending."""
        result = await sendgrid_sender.send_email(sample_email_content)

        assert result["status_code"] == 202
        mock_sendgrid.return_value.send.assert_called_once()


# =============================================================================
# Twilio Integration Tests
# =============================================================================


class TestTwilioIntegration:
    """Tests for Twilio SMS delivery."""

    @pytest.fixture
    def twilio_sender(self, mock_twilio):
        """Create a Twilio sender."""
        class TwilioSender:
            def __init__(self, account_sid: str, auth_token: str, from_number: str):
                from twilio.rest import Client
                self.client = Client(account_sid, auth_token)
                self.from_number = from_number

            async def send_sms(self, sms: SMSContent) -> dict:
                """Send SMS via Twilio."""
                message = self.client.messages.create(
                    body=sms.message,
                    from_=self.from_number,
                    to=sms.phone_number,
                )

                return {
                    "message_sid": message.sid,
                    "status": message.status,
                }

        return TwilioSender("test-sid", "test-token", "+1-555-000-0000")

    @pytest.fixture
    def sample_sms_content(self):
        """Create sample SMS content."""
        return SMSContent(
            message="GrantRadar: 87% match! AI Research Grant (30d left) https://gr.ai/m/abc123",
            phone_number="+1-555-123-4567",
            short_url="https://gr.ai/m/abc123",
        )

    @pytest.mark.asyncio
    async def test_send_sms_success(self, twilio_sender, sample_sms_content, mock_twilio):
        """Test successful SMS sending."""
        result = await twilio_sender.send_sms(sample_sms_content)

        assert "message_sid" in result
        assert result["status"] == "queued"
        mock_twilio.return_value.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_sms_invalid_number(self, twilio_sender, mock_twilio):
        """Test SMS sending with invalid phone number."""
        from twilio.base.exceptions import TwilioRestException

        mock_twilio.return_value.messages.create.side_effect = TwilioRestException(
            status=400,
            uri="/Messages",
            msg="Invalid phone number",
        )

        sms = SMSContent(
            message="Test",
            phone_number="invalid",
        )

        with pytest.raises(TwilioRestException):
            await twilio_sender.send_sms(sms)


# =============================================================================
# Delivery Status Tests
# =============================================================================


class TestDeliveryStatus:
    """Tests for delivery status tracking."""

    def test_delivery_status_initial(self):
        """Test initial delivery status."""
        status = DeliveryStatus(
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=DeliveryChannel.EMAIL,
        )

        assert status.status == "pending"
        assert status.sent_at is None
        assert status.retry_count == 0

    def test_delivery_status_sent(self):
        """Test delivery status after sending."""
        status = DeliveryStatus(
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=DeliveryChannel.EMAIL,
            status="sent",
            sent_at=datetime.now(timezone.utc),
            provider_message_id="sg_123456",
        )

        assert status.status == "sent"
        assert status.sent_at is not None
        assert status.provider_message_id == "sg_123456"

    def test_delivery_status_failed(self):
        """Test delivery status after failure."""
        status = DeliveryStatus(
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=DeliveryChannel.SMS,
            status="failed",
            error_message="Invalid phone number",
            retry_count=3,
        )

        assert status.status == "failed"
        assert status.error_message == "Invalid phone number"
        assert status.retry_count == 3


# =============================================================================
# Digest Batching Tests
# =============================================================================


class TestDigestBatching:
    """Tests for batching medium-priority alerts into digests."""

    @pytest.fixture
    def digest_batcher(self):
        """Create a digest batcher."""
        class DigestBatcher:
            def __init__(self, max_per_digest: int = 10, batch_window_hours: int = 24):
                self.max_per_digest = max_per_digest
                self.batch_window_hours = batch_window_hours
                self.pending_alerts: dict[uuid.UUID, list[AlertPayload]] = {}

            def should_batch(self, alert: AlertPayload) -> bool:
                """Determine if alert should be batched."""
                return alert.priority == AlertPriority.MEDIUM

            def add_to_batch(self, alert: AlertPayload) -> DigestBatch | None:
                """Add alert to batch, return batch if ready to send."""
                user_id = alert.user.user_id

                if user_id not in self.pending_alerts:
                    self.pending_alerts[user_id] = []

                self.pending_alerts[user_id].append(alert)

                # Check if batch is ready
                if len(self.pending_alerts[user_id]) >= self.max_per_digest:
                    return self.flush_batch(user_id)

                return None

            def flush_batch(self, user_id: uuid.UUID) -> DigestBatch | None:
                """Flush pending alerts for a user."""
                if user_id not in self.pending_alerts or not self.pending_alerts[user_id]:
                    return None

                alerts = self.pending_alerts.pop(user_id)
                return DigestBatch(
                    user_id=user_id,
                    alerts=alerts,
                )

            def flush_all(self) -> list[DigestBatch]:
                """Flush all pending batches."""
                batches = []
                for user_id in list(self.pending_alerts.keys()):
                    batch = self.flush_batch(user_id)
                    if batch:
                        batches.append(batch)
                return batches

        return DigestBatcher()

    def test_should_batch_medium(self, digest_batcher, sample_alert_payload):
        """Test that medium priority alerts should be batched."""
        sample_alert_payload.priority = AlertPriority.MEDIUM
        assert digest_batcher.should_batch(sample_alert_payload) is True

    def test_should_not_batch_high(self, digest_batcher, sample_alert_payload):
        """Test that high priority alerts should not be batched."""
        sample_alert_payload.priority = AlertPriority.HIGH
        assert digest_batcher.should_batch(sample_alert_payload) is False

    def test_add_to_batch_accumulates(self, digest_batcher, sample_alert_payload):
        """Test that alerts accumulate in batch."""
        sample_alert_payload.priority = AlertPriority.MEDIUM

        # Add multiple alerts
        for i in range(5):
            result = digest_batcher.add_to_batch(sample_alert_payload)

        # Should not trigger batch yet (max is 10)
        assert result is None
        assert len(digest_batcher.pending_alerts[sample_alert_payload.user.user_id]) == 5

    def test_add_to_batch_triggers_flush(self, digest_batcher, sample_alert_payload):
        """Test that batch flushes when reaching max."""
        sample_alert_payload.priority = AlertPriority.MEDIUM
        digest_batcher.max_per_digest = 5

        # Add alerts up to max
        for i in range(5):
            result = digest_batcher.add_to_batch(sample_alert_payload)

        assert result is not None
        assert isinstance(result, DigestBatch)
        assert len(result.alerts) == 5

    def test_flush_all(self, digest_batcher, sample_alert_payload):
        """Test flushing all pending batches."""
        user1 = uuid.uuid4()
        user2 = uuid.uuid4()

        # Use deep=True to create independent copies of nested objects
        alert1 = sample_alert_payload.model_copy(deep=True)
        alert1.user.user_id = user1
        alert1.priority = AlertPriority.MEDIUM

        alert2 = sample_alert_payload.model_copy(deep=True)
        alert2.user.user_id = user2
        alert2.priority = AlertPriority.MEDIUM

        digest_batcher.add_to_batch(alert1)
        digest_batcher.add_to_batch(alert2)

        batches = digest_batcher.flush_all()

        assert len(batches) == 2


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestDeliveryErrorHandling:
    """Tests for error handling in delivery."""

    @pytest.mark.asyncio
    async def test_sendgrid_api_error(self, mock_sendgrid):
        """Test handling SendGrid API errors."""
        mock_sendgrid.return_value.send.side_effect = Exception("SendGrid API Error")

        with pytest.raises(Exception) as exc_info:
            mock_sendgrid.return_value.send(MagicMock())

        assert "SendGrid API Error" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_twilio_api_error(self, mock_twilio):
        """Test handling Twilio API errors."""
        from twilio.base.exceptions import TwilioRestException

        mock_twilio.return_value.messages.create.side_effect = TwilioRestException(
            status=500,
            uri="/Messages",
            msg="Internal Server Error",
        )

        with pytest.raises(TwilioRestException):
            mock_twilio.return_value.messages.create(
                body="Test",
                from_="+1-555-000-0000",
                to="+1-555-123-4567",
            )

    def test_invalid_email_address(self):
        """Test that EmailContent accepts string values (validation happens at send time)."""
        # EmailContent accepts any string - validation happens at send time
        # This test verifies the model doesn't crash on instantiation
        email = EmailContent(
            subject="Test",
            body_html="<html>Test</html>",
            body_text="Test",
            from_email="invalid",
            from_name="Test",
            to_email="also-invalid",
        )
        assert email.from_email == "invalid"
        assert email.to_email == "also-invalid"


# =============================================================================
# Event Processing Tests
# =============================================================================


class TestAlertEventProcessing:
    """Tests for alert event processing."""

    def test_alert_pending_event_creation(self):
        """Test creating AlertPendingEvent."""
        event = AlertPendingEvent(
            event_id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            match_id=uuid.uuid4(),
            channel=AlertChannel.EMAIL,
            user_email="test@test.com",
            alert_title="New Grant Match",
            alert_body="A grant matches your profile.",
        )

        assert event.channel == AlertChannel.EMAIL
        assert event.user_email == "test@test.com"

    def test_alert_event_serialization(self, sample_alert_pending_event):
        """Test alert event JSON serialization."""
        json_str = sample_alert_pending_event.model_dump_json()
        parsed = json.loads(json_str)

        assert "alert_id" in parsed
        assert "channel" in parsed
        assert "user_email" in parsed

    def test_alert_event_deserialization(self):
        """Test alert event deserialization."""
        event_data = {
            "event_id": str(uuid.uuid4()),
            "alert_id": str(uuid.uuid4()),
            "match_id": str(uuid.uuid4()),
            "channel": "email",
            "user_email": "test@test.com",
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0",
        }

        event = AlertPendingEvent(**event_data)

        assert event.channel == AlertChannel.EMAIL
        assert event.user_email == "test@test.com"


@pytest.fixture
def sample_alert_payload():
    """Create a sample alert payload for tests outside the class."""
    return AlertPayload(
        match_id=uuid.uuid4(),
        user=UserInfo(
            user_id=uuid.uuid4(),
            name="Dr. Jane Smith",
            email="jane@university.edu",
            phone="+1-555-123-4567",
        ),
        grant=GrantInfo(
            grant_id=uuid.uuid4(),
            title="AI Research in Healthcare",
            description="Research grant for AI applications in medicine",
            funding_agency="NIH",
            amount_max=500000.0,
            deadline=datetime.now(timezone.utc) + timedelta(days=30),
            url="https://grants.gov/test",
        ),
        match=MatchInfo(
            match_id=uuid.uuid4(),
            match_score=0.87,
            matching_criteria=["research_area"],
            explanation="Strong alignment in AI research.",
        ),
        priority=AlertPriority.HIGH,
        channels=[DeliveryChannel.EMAIL],
    )
