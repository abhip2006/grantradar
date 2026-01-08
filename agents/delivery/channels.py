"""
GrantRadar Alert Delivery Channels
Channel implementations for SendGrid, Twilio, and Slack.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

import structlog
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Mail,
    Email,
    To,
    Content,
    Attachment,
    TrackingSettings,
    ClickTracking,
    OpenTracking,
    Category,
    CustomArg,
)
from twilio.rest import Client as TwilioClient
from twilio.base.exceptions import TwilioRestException
import httpx

from backend.core.config import settings
from agents.delivery.models import (
    EmailContent,
    SMSContent,
    SlackContent,
    DeliveryStatus,
    DeliveryChannel,
)


logger = structlog.get_logger(__name__)


class BaseChannel(ABC):
    """Abstract base class for delivery channels."""

    @abstractmethod
    async def send(self, content: Any) -> DeliveryStatus:
        """Send content through this channel."""
        pass

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this channel is properly configured."""
        pass


class SendGridChannel(BaseChannel):
    """
    SendGrid email delivery channel.

    Features:
    - Personalized email sending
    - Open and click tracking
    - Webhook event handling
    - Automatic retry with exponential backoff
    - Proper async execution
    """

    # Retry configuration
    MAX_RETRIES: int = 3
    RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)  # Exponential backoff in seconds

    def __init__(self):
        self._client: Optional[SendGridAPIClient] = None
        self.logger = structlog.get_logger().bind(channel="sendgrid")

    @property
    def client(self) -> SendGridAPIClient:
        """Lazy-loaded SendGrid client."""
        if self._client is None:
            if not settings.sendgrid_api_key:
                raise ValueError("SendGrid API key not configured")
            self._client = SendGridAPIClient(api_key=settings.sendgrid_api_key)
        return self._client

    def is_configured(self) -> bool:
        """Check if SendGrid is configured."""
        return bool(settings.sendgrid_api_key)

    def _build_message(self, content: EmailContent) -> Mail:
        """
        Build a SendGrid Mail object from EmailContent.

        Args:
            content: Email content to build message from

        Returns:
            Configured Mail object ready to send
        """
        # Build the message - use separate assignment for better compatibility
        # across SendGrid library versions
        message = Mail()
        message.from_email = Email(content.from_email, content.from_name)
        message.subject = content.subject
        message.add_to(To(content.to_email, content.to_name))

        # Add HTML and plain text content
        # Plain text should come first for proper fallback
        message.add_content(Content("text/plain", content.body_text))
        message.add_content(Content("text/html", content.body_html))

        # Enable tracking
        tracking_settings = TrackingSettings()
        tracking_settings.click_tracking = ClickTracking(
            enable=True, enable_text=True
        )
        tracking_settings.open_tracking = OpenTracking(enable=True)
        message.tracking_settings = tracking_settings

        # Add category for filtering
        message.category = Category("grant_alert")

        # Add reply-to if specified
        if content.reply_to:
            message.reply_to = Email(content.reply_to)

        # Add custom tracking ID for webhook correlation
        if content.tracking_id:
            message.add_custom_arg(CustomArg(key="match_id", value=content.tracking_id))

        return message

    def _send_sync(self, message: Mail) -> Any:
        """
        Synchronous send operation for use with asyncio.to_thread.

        Args:
            message: SendGrid Mail object to send

        Returns:
            SendGrid API response
        """
        return self.client.send(message)

    def _is_retryable_error(self, exception: Exception) -> bool:
        """
        Determine if an error is retryable.

        Args:
            exception: The exception that occurred

        Returns:
            True if the error is transient and worth retrying
        """
        error_str = str(exception).lower()

        # Retryable conditions
        retryable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "429",  # Too Many Requests
            "500",  # Internal Server Error
            "502",  # Bad Gateway
            "503",  # Service Unavailable
            "504",  # Gateway Timeout
        ]

        return any(pattern in error_str for pattern in retryable_patterns)

    async def send(self, content: EmailContent) -> DeliveryStatus:
        """
        Send email via SendGrid with retry logic.

        Args:
            content: Email content to send

        Returns:
            DeliveryStatus with tracking information
        """
        import asyncio

        alert_id = uuid4()
        status = DeliveryStatus(
            alert_id=alert_id,
            match_id=UUID(content.tracking_id) if content.tracking_id else uuid4(),
            channel=DeliveryChannel.EMAIL,
            status="pending",
        )

        # Build the message once
        try:
            message = self._build_message(content)
        except Exception as e:
            status.status = "failed"
            status.error_message = f"Failed to build message: {str(e)}"
            self.logger.error(
                "email_build_failed",
                to=content.to_email,
                error=str(e),
            )
            return status

        # Attempt to send with retries
        last_exception: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                # Run the synchronous SendGrid API call in a thread pool
                # to avoid blocking the event loop
                response = await asyncio.to_thread(self._send_sync, message)

                # Extract message ID from response headers
                message_id = response.headers.get("X-Message-Id", str(alert_id))

                status.status = "sent"
                status.sent_at = datetime.utcnow()
                status.provider_message_id = message_id
                status.retry_count = attempt

                self.logger.info(
                    "email_sent",
                    to=content.to_email,
                    subject=content.subject[:50],
                    message_id=message_id,
                    status_code=response.status_code,
                    attempt=attempt + 1,
                )

                return status

            except Exception as e:
                last_exception = e
                status.retry_count = attempt + 1

                self.logger.warning(
                    "email_send_attempt_failed",
                    to=content.to_email,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.MAX_RETRIES,
                )

                # Check if we should retry
                if attempt < self.MAX_RETRIES - 1 and self._is_retryable_error(e):
                    delay = self.RETRY_DELAYS[attempt]
                    self.logger.info(
                        "email_send_retrying",
                        to=content.to_email,
                        delay_seconds=delay,
                        next_attempt=attempt + 2,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error or max retries reached
                    break

        # All retries exhausted
        status.status = "failed"
        status.error_message = str(last_exception) if last_exception else "Unknown error"
        self.logger.error(
            "email_send_failed",
            to=content.to_email,
            error=status.error_message,
            total_attempts=status.retry_count,
        )

        return status

    def send_email(
        self,
        to_email: str,
        to_name: Optional[str],
        subject: str,
        body_html: str,
        body_text: str,
        tracking_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Synchronous helper to send email.

        This method provides a synchronous interface for sending emails,
        handling both sync and async execution contexts properly.

        Args:
            to_email: Recipient email address
            to_name: Recipient name (can be None)
            subject: Email subject line
            body_html: HTML body content
            body_text: Plain text body content (fallback for non-HTML clients)
            tracking_id: Optional tracking ID for webhook correlation
            reply_to: Optional reply-to email address

        Returns:
            DeliveryStatus with tracking information including:
            - alert_id: Unique identifier for this send attempt
            - status: "sent", "failed", or "pending"
            - provider_message_id: SendGrid message ID for tracking
            - error_message: Error details if failed
            - retry_count: Number of retry attempts made
        """
        import asyncio
        import concurrent.futures

        content = EmailContent(
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=settings.from_email,
            from_name=settings.from_name,
            to_email=to_email,
            to_name=to_name,
            tracking_id=tracking_id,
            reply_to=reply_to,
        )

        # Determine execution context and run appropriately
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, we can use asyncio.run directly
            return asyncio.run(self.send(content))

        # We're inside a running event loop - use thread pool executor
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, self.send(content))
            return future.result(timeout=60.0)  # 60 second timeout for email send

    def send_email_sync(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: str,
        to_name: Optional[str] = None,
        tracking_id: Optional[str] = None,
        reply_to: Optional[str] = None,
    ) -> DeliveryStatus:
        """
        Direct synchronous send without async overhead.

        This method bypasses async entirely for pure synchronous contexts.
        Use this when you know you're in a synchronous context and want
        to avoid any asyncio complexity.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body_html: HTML body content
            body_text: Plain text body content
            to_name: Optional recipient name
            tracking_id: Optional tracking ID for webhook correlation
            reply_to: Optional reply-to email address

        Returns:
            DeliveryStatus with tracking information
        """
        import time

        alert_id = uuid4()
        status = DeliveryStatus(
            alert_id=alert_id,
            match_id=UUID(tracking_id) if tracking_id else uuid4(),
            channel=DeliveryChannel.EMAIL,
            status="pending",
        )

        content = EmailContent(
            subject=subject,
            body_html=body_html,
            body_text=body_text,
            from_email=settings.from_email,
            from_name=settings.from_name,
            to_email=to_email,
            to_name=to_name,
            tracking_id=tracking_id,
            reply_to=reply_to,
        )

        try:
            message = self._build_message(content)
        except Exception as e:
            status.status = "failed"
            status.error_message = f"Failed to build message: {str(e)}"
            self.logger.error("email_build_failed", to=to_email, error=str(e))
            return status

        last_exception: Optional[Exception] = None

        for attempt in range(self.MAX_RETRIES):
            try:
                response = self.client.send(message)

                message_id = response.headers.get("X-Message-Id", str(alert_id))

                status.status = "sent"
                status.sent_at = datetime.utcnow()
                status.provider_message_id = message_id
                status.retry_count = attempt

                self.logger.info(
                    "email_sent_sync",
                    to=to_email,
                    subject=subject[:50],
                    message_id=message_id,
                    status_code=response.status_code,
                    attempt=attempt + 1,
                )

                return status

            except Exception as e:
                last_exception = e
                status.retry_count = attempt + 1

                self.logger.warning(
                    "email_send_attempt_failed_sync",
                    to=to_email,
                    error=str(e),
                    attempt=attempt + 1,
                    max_retries=self.MAX_RETRIES,
                )

                if attempt < self.MAX_RETRIES - 1 and self._is_retryable_error(e):
                    delay = self.RETRY_DELAYS[attempt]
                    time.sleep(delay)
                else:
                    break

        status.status = "failed"
        status.error_message = str(last_exception) if last_exception else "Unknown error"
        self.logger.error(
            "email_send_failed_sync",
            to=to_email,
            error=status.error_message,
            total_attempts=status.retry_count,
        )

        return status

    @staticmethod
    def track_events(event_data: dict) -> None:
        """
        Process SendGrid webhook events for tracking.

        Expected events: delivered, open, click, bounce, spam_report

        Args:
            event_data: Webhook payload from SendGrid
        """
        log = structlog.get_logger().bind(channel="sendgrid_webhook")

        event_type = event_data.get("event")
        message_id = event_data.get("sg_message_id")
        email = event_data.get("email")
        timestamp = event_data.get("timestamp")

        log.info(
            "sendgrid_event_received",
            event_type=event_type,
            message_id=message_id,
            email=email,
        )

        # In production, this would update the alerts_sent table
        # Example: db.execute(
        #     "UPDATE alerts_sent SET opened_at = :opened_at WHERE provider_message_id = :message_id",
        #     {"opened_at": datetime.fromtimestamp(timestamp), "message_id": message_id}
        # )


class TwilioChannel(BaseChannel):
    """
    Twilio SMS delivery channel.

    Features:
    - SMS sending for critical alerts
    - Delivery status tracking
    - Rate limiting awareness
    """

    def __init__(self):
        self._client: Optional[TwilioClient] = None
        self.logger = structlog.get_logger().bind(channel="twilio")

    @property
    def client(self) -> TwilioClient:
        """Lazy-loaded Twilio client."""
        if self._client is None:
            if not settings.twilio_account_sid or not settings.twilio_auth_token:
                raise ValueError("Twilio credentials not configured")
            self._client = TwilioClient(
                settings.twilio_account_sid, settings.twilio_auth_token
            )
        return self._client

    def is_configured(self) -> bool:
        """Check if Twilio is configured."""
        return bool(
            settings.twilio_account_sid
            and settings.twilio_auth_token
            and settings.twilio_phone_number
        )

    async def send(self, content: SMSContent) -> DeliveryStatus:
        """
        Send SMS via Twilio.

        Args:
            content: SMS content to send

        Returns:
            DeliveryStatus with tracking information
        """
        alert_id = uuid4()
        status = DeliveryStatus(
            alert_id=alert_id,
            match_id=uuid4(),
            channel=DeliveryChannel.SMS,
            status="pending",
        )

        try:
            message = self.client.messages.create(
                body=content.message,
                from_=settings.twilio_phone_number,
                to=content.phone_number,
                status_callback=f"{settings.backend_url}/api/webhooks/twilio/status",
            )

            status.status = "sent"
            status.sent_at = datetime.utcnow()
            status.provider_message_id = message.sid

            self.logger.info(
                "sms_sent",
                to=content.phone_number[-4:],  # Log only last 4 digits
                message_sid=message.sid,
                status=message.status,
            )

        except TwilioRestException as e:
            status.status = "failed"
            status.error_message = str(e)
            self.logger.error(
                "sms_send_failed",
                error_code=e.code,
                error=str(e),
            )

        except Exception as e:
            status.status = "failed"
            status.error_message = str(e)
            self.logger.error(
                "sms_send_failed",
                error=str(e),
            )

        return status

    def send_sms(
        self, phone_number: str, message: str, match_id: Optional[UUID] = None
    ) -> DeliveryStatus:
        """
        Synchronous helper to send SMS.

        Args:
            phone_number: Recipient phone number (E.164 format)
            message: SMS message content (max 160 chars)
            match_id: Optional match ID for tracking

        Returns:
            DeliveryStatus with tracking information
        """
        import asyncio

        content = SMSContent(
            message=message[:160],  # Truncate to SMS limit
            phone_number=phone_number,
        )

        # Run async send in sync context
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.send(content))
                result = future.result()
                if match_id:
                    result.match_id = match_id
                return result
        else:
            result = asyncio.run(self.send(content))
            if match_id:
                result.match_id = match_id
            return result

    @staticmethod
    def track_delivery(event_data: dict) -> None:
        """
        Process Twilio status callback for tracking.

        Expected statuses: queued, sent, delivered, undelivered, failed

        Args:
            event_data: Status callback payload from Twilio
        """
        log = structlog.get_logger().bind(channel="twilio_webhook")

        message_sid = event_data.get("MessageSid")
        message_status = event_data.get("MessageStatus")
        error_code = event_data.get("ErrorCode")

        log.info(
            "twilio_status_received",
            message_sid=message_sid,
            status=message_status,
            error_code=error_code,
        )

        # In production, this would update the alerts_sent table
        # delivered_at would be set when status == "delivered"


class SlackChannel(BaseChannel):
    """
    Slack webhook delivery channel.

    Features:
    - Rich message formatting with Block Kit
    - Custom webhook support per user
    - Fallback to default system webhook
    - Automatic retry with exponential backoff
    - Rate limiting awareness (Slack limits: 1 msg/sec per webhook)
    """

    # Slack webhook rate limits: 1 message per second per webhook
    MAX_RETRIES: int = 3
    RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)  # Exponential backoff in seconds

    def __init__(self):
        self.logger = structlog.get_logger().bind(channel="slack")
        self._http_client: Optional[httpx.AsyncClient] = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Lazy-loaded HTTP client for Slack webhooks."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_keepalive_connections=5, max_connections=10),
            )
        return self._http_client

    def is_configured(self) -> bool:
        """Check if Slack is configured with a default webhook URL."""
        return bool(settings.slack_webhook_url)

    def get_default_webhook_url(self) -> Optional[str]:
        """Get the default system Slack webhook URL from settings."""
        return settings.slack_webhook_url

    async def send(self, content: SlackContent) -> DeliveryStatus:
        """
        Send message via Slack webhook.

        Implements retry logic with exponential backoff for transient failures.
        Handles Slack-specific error responses and rate limiting.

        Args:
            content: Slack message content including webhook URL, text, and optional blocks

        Returns:
            DeliveryStatus with tracking information including sent/delivered timestamps
        """
        import asyncio

        alert_id = uuid4()
        status = DeliveryStatus(
            alert_id=alert_id,
            match_id=uuid4(),
            channel=DeliveryChannel.SLACK,
            status="pending",
        )

        # Validate webhook URL - fall back to default if not provided
        webhook_url = content.webhook_url
        if not webhook_url:
            webhook_url = self.get_default_webhook_url()
            if not webhook_url:
                status.status = "failed"
                status.error_message = "No Slack webhook URL configured"
                self.logger.error("slack_no_webhook_url")
                return status

        # Build the payload
        payload: dict = {"text": content.text}
        if content.blocks:
            payload["blocks"] = content.blocks

        # Attempt send with retries
        last_error: Optional[str] = None
        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.http_client.post(
                    webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )

                # Slack webhook returns "ok" on success with 200 status
                if response.status_code == 200 and response.text == "ok":
                    status.status = "delivered"
                    status.sent_at = datetime.utcnow()
                    status.delivered_at = datetime.utcnow()
                    status.retry_count = attempt

                    self.logger.info(
                        "slack_message_sent",
                        webhook_url=webhook_url[:50] + "..." if len(webhook_url) > 50 else webhook_url,
                        attempts=attempt + 1,
                    )
                    return status

                # Handle rate limiting (429)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", self.RETRY_DELAYS[attempt]))
                    self.logger.warning(
                        "slack_rate_limited",
                        retry_after=retry_after,
                        attempt=attempt + 1,
                    )
                    if attempt < self.MAX_RETRIES - 1:
                        await asyncio.sleep(retry_after)
                        continue

                # Handle other error responses
                last_error = f"Slack API error (HTTP {response.status_code}): {response.text}"
                self.logger.warning(
                    "slack_api_error",
                    status_code=response.status_code,
                    response=response.text[:200],
                    attempt=attempt + 1,
                )

                # Don't retry on client errors (4xx except 429)
                if 400 <= response.status_code < 500 and response.status_code != 429:
                    break

                # Retry on server errors (5xx)
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])

            except httpx.TimeoutException as e:
                last_error = f"Slack webhook timeout: {str(e)}"
                self.logger.warning(
                    "slack_timeout",
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])

            except httpx.RequestError as e:
                last_error = f"Slack webhook request error: {str(e)}"
                self.logger.warning(
                    "slack_request_error",
                    error=str(e),
                    attempt=attempt + 1,
                )
                if attempt < self.MAX_RETRIES - 1:
                    await asyncio.sleep(self.RETRY_DELAYS[attempt])

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                self.logger.error(
                    "slack_send_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                    attempt=attempt + 1,
                )
                break  # Don't retry on unexpected errors

        # All retries exhausted
        status.status = "failed"
        status.error_message = last_error
        status.retry_count = self.MAX_RETRIES

        self.logger.error(
            "slack_send_failed_all_retries",
            error=last_error,
            max_retries=self.MAX_RETRIES,
        )

        return status

    async def send_to_default_webhook(
        self,
        text: str,
        blocks: Optional[list[dict]] = None,
        match_id: Optional[UUID] = None,
    ) -> DeliveryStatus:
        """
        Send message to the default system Slack webhook.

        Convenience method for system notifications that don't target a specific user.

        Args:
            text: Fallback text for notifications
            blocks: Optional Block Kit blocks for rich formatting
            match_id: Optional match ID for tracking

        Returns:
            DeliveryStatus with tracking information
        """
        webhook_url = self.get_default_webhook_url()
        if not webhook_url:
            status = DeliveryStatus(
                alert_id=uuid4(),
                match_id=match_id or uuid4(),
                channel=DeliveryChannel.SLACK,
                status="failed",
                error_message="No default Slack webhook URL configured",
            )
            return status

        content = SlackContent(
            webhook_url=webhook_url,
            text=text,
            blocks=blocks,
        )

        result = await self.send(content)
        if match_id:
            result.match_id = match_id
        return result

    def send_webhook(
        self,
        webhook_url: str,
        text: str,
        blocks: Optional[list[dict]] = None,
        match_id: Optional[UUID] = None,
    ) -> DeliveryStatus:
        """
        Synchronous helper to send Slack message.

        Args:
            webhook_url: Slack incoming webhook URL
            text: Fallback text for notifications
            blocks: Optional Block Kit blocks for rich formatting
            match_id: Optional match ID for tracking

        Returns:
            DeliveryStatus with tracking information
        """
        import asyncio

        content = SlackContent(
            webhook_url=webhook_url,
            text=text,
            blocks=blocks,
        )

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.send(content))
                result = future.result()
                if match_id:
                    result.match_id = match_id
                return result
        else:
            result = asyncio.run(self.send(content))
            if match_id:
                result.match_id = match_id
            return result

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


# Singleton instances for channel access
_sendgrid_channel: Optional[SendGridChannel] = None
_twilio_channel: Optional[TwilioChannel] = None
_slack_channel: Optional[SlackChannel] = None


def get_sendgrid_channel() -> SendGridChannel:
    """Get or create SendGrid channel instance."""
    global _sendgrid_channel
    if _sendgrid_channel is None:
        _sendgrid_channel = SendGridChannel()
    return _sendgrid_channel


def get_twilio_channel() -> TwilioChannel:
    """Get or create Twilio channel instance."""
    global _twilio_channel
    if _twilio_channel is None:
        _twilio_channel = TwilioChannel()
    return _twilio_channel


def get_slack_channel() -> SlackChannel:
    """Get or create Slack channel instance."""
    global _slack_channel
    if _slack_channel is None:
        _slack_channel = SlackChannel()
    return _slack_channel
