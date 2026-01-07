"""
GrantRadar Alert Delivery Agent
Consumes from 'matches:computed' stream and sends personalized alerts.
"""
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID, uuid4

import anthropic
import redis
import structlog
from celery import Celery

from sqlalchemy import select

from backend.core.config import settings
from backend.core.events import MatchComputedEvent, PriorityLevel
from backend.database import get_async_session
from backend.models import Grant, User
from agents.delivery.models import (
    AlertPayload,
    AlertPriority,
    DeliveryChannel,
    DeliveryStatus,
    DigestBatch,
    EmailContent,
    GrantInfo,
    MatchInfo,
    SMSContent,
    UserInfo,
    UserNotificationPreferences,
)
from agents.delivery.channels import (
    get_sendgrid_channel,
    get_twilio_channel,
    get_slack_channel,
)


logger = structlog.get_logger(__name__)

# Initialize Celery app
celery_app = Celery(
    "grantradar_alerter",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_routes={
        "agents.delivery.alerter.send_critical_alert": {"queue": "critical"},
        "agents.delivery.alerter.send_high_priority_alert": {"queue": "high"},
        "agents.delivery.alerter.send_medium_priority_alert": {"queue": "default"},
        "agents.delivery.alerter.process_digest_batch": {"queue": "default"},
    },
    task_default_queue="default",
    task_default_priority=5,
)


class AlertDeliveryAgent:
    """
    Alert Delivery Agent for GrantRadar.

    Consumes from 'matches:computed' Redis stream and routes alerts
    to appropriate channels based on priority:
    - Critical (>95% match + <14 days): SMS + Email + Slack
    - High (85-95% match): Email + Slack
    - Medium (70-85% match): Email only (batched as digest)
    """

    MATCHES_STREAM = "matches:computed"
    CONSUMER_GROUP = "alerter"
    CONSUMER_NAME = "alerter-worker-1"
    DIGEST_KEY_PREFIX = "digest:pending:"
    ALERTS_SENT_KEY = "alerts:sent"

    def __init__(self):
        self.logger = structlog.get_logger().bind(agent="alerter")
        self._redis_client: Optional[redis.Redis] = None
        self._anthropic_client: Optional[anthropic.Anthropic] = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy-loaded Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                settings.redis_url, decode_responses=True
            )
        return self._redis_client

    @property
    def anthropic_client(self) -> anthropic.Anthropic:
        """Lazy-loaded Anthropic client for content generation."""
        if self._anthropic_client is None:
            if not settings.anthropic_api_key:
                raise ValueError("Anthropic API key not configured")
            self._anthropic_client = anthropic.Anthropic(
                api_key=settings.anthropic_api_key
            )
        return self._anthropic_client

    def _ensure_consumer_group(self) -> None:
        """Create consumer group if it doesn't exist."""
        try:
            self.redis_client.xgroup_create(
                self.MATCHES_STREAM,
                self.CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
            self.logger.info("consumer_group_created", group=self.CONSUMER_GROUP)
        except redis.ResponseError as e:
            if "BUSYGROUP" in str(e):
                self.logger.debug("consumer_group_exists", group=self.CONSUMER_GROUP)
            else:
                raise

    def determine_priority(
        self, match_score: float, deadline: Optional[datetime]
    ) -> AlertPriority:
        """
        Determine alert priority based on match score and deadline.

        Rules:
        - Critical: >95% match AND <14 days to deadline
        - High: 85-95% match
        - Medium: 70-85% match
        - Low: <70% match (no alert)
        """
        match_percentage = match_score * 100
        days_to_deadline = None

        if deadline:
            days_to_deadline = (deadline - datetime.utcnow()).days

        # Critical: high match + urgent deadline
        if match_percentage > 95 and days_to_deadline is not None and days_to_deadline < 14:
            return AlertPriority.CRITICAL

        # High priority
        if 85 <= match_percentage <= 95:
            return AlertPriority.HIGH

        # Medium priority
        if 70 <= match_percentage < 85:
            return AlertPriority.MEDIUM

        # Low priority - no alert
        return AlertPriority.LOW

    def determine_channels(
        self,
        priority: AlertPriority,
        preferences: Optional[UserNotificationPreferences] = None,
    ) -> list[DeliveryChannel]:
        """
        Determine delivery channels based on priority and user preferences.

        Default channel assignment by priority:
        - Critical: SMS + Email + Slack
        - High: Email + Slack
        - Medium: Email only

        User preferences can disable specific channels.

        Args:
            priority: The alert priority level.
            preferences: User's notification preferences (optional).

        Returns:
            List of enabled delivery channels for this alert.
        """
        # Start with priority-based channel assignment
        if priority == AlertPriority.CRITICAL:
            channels = [DeliveryChannel.SMS, DeliveryChannel.EMAIL, DeliveryChannel.SLACK]
        elif priority == AlertPriority.HIGH:
            channels = [DeliveryChannel.EMAIL, DeliveryChannel.SLACK]
        elif priority == AlertPriority.MEDIUM:
            channels = [DeliveryChannel.EMAIL]
        else:
            return []

        # If no preferences provided, return default channels
        if preferences is None:
            return channels

        # Filter channels based on user preferences
        enabled_channels = []
        for channel in channels:
            if channel == DeliveryChannel.EMAIL and preferences.email_notifications:
                enabled_channels.append(channel)
            elif channel == DeliveryChannel.SMS and preferences.sms_notifications:
                enabled_channels.append(channel)
            elif channel == DeliveryChannel.SLACK and preferences.slack_notifications:
                enabled_channels.append(channel)

        return enabled_channels

    async def generate_email_content(
        self,
        user: UserInfo,
        grant: GrantInfo,
        match: MatchInfo,
    ) -> EmailContent:
        """
        Generate personalized email content using Claude.

        Uses two prompts:
        1. Subject line generation
        2. Body content generation
        """
        # Generate subject line
        subject_prompt = f"""Write an engaging subject line (under 50 characters) for this grant alert:
Grant title: {grant.title}
Match score: {int(match.match_score * 100)}%
Deadline: {grant.deadline.strftime('%B %d, %Y') if grant.deadline else 'Open'}

Return ONLY the subject line, no quotes or explanation."""

        subject_response = self.anthropic_client.messages.create(
            model=settings.llm_model,
            max_tokens=100,
            messages=[{"role": "user", "content": subject_prompt}],
        )
        subject = subject_response.content[0].text.strip()[:100]

        # Generate body content
        body_prompt = f"""Write a personalized alert email for {user.name} about this grant:

Grant Title: {grant.title}
Funding Agency: {grant.funding_agency}
Amount: {f'${grant.amount_min:,.0f} - ${grant.amount_max:,.0f}' if grant.amount_min and grant.amount_max else 'Not specified'}
Deadline: {grant.deadline.strftime('%B %d, %Y') if grant.deadline else 'Rolling/Open'}
Description: {grant.description[:500]}

Match Score: {int(match.match_score * 100)}%
Matching Criteria: {', '.join(match.matching_criteria) if match.matching_criteria else 'Strong overall fit'}
Reasoning: {match.explanation or 'This grant aligns well with your research profile.'}

Requirements:
1. Tone: Professional but friendly
2. Include: (1) Why this is a great fit, (2) Key deadline info, (3) Strategic recommendations, (4) CTA to view full details
3. Keep under 200 words
4. Format for HTML email with proper paragraphs

Return the email body only, no subject line or signature."""

        body_response = self.anthropic_client.messages.create(
            model=settings.llm_model,
            max_tokens=1000,
            messages=[{"role": "user", "content": body_prompt}],
        )
        body_html = body_response.content[0].text.strip()

        # Convert to plain text (simple version)
        body_text = body_html.replace("<p>", "").replace("</p>", "\n\n")
        body_text = body_text.replace("<br>", "\n").replace("<br/>", "\n")
        body_text = body_text.replace("<strong>", "").replace("</strong>", "")
        body_text = body_text.replace("<em>", "").replace("</em>", "")

        # Wrap in email template
        body_html_full = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #fff; padding: 24px; border: 1px solid #e5e7eb; border-top: none; }}
        .match-score {{ display: inline-block; background: #10b981; color: white; padding: 4px 12px; border-radius: 20px; font-weight: bold; }}
        .cta-button {{ display: inline-block; background: #667eea; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; margin-top: 16px; }}
        .footer {{ text-align: center; padding: 16px; color: #6b7280; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1 style="margin: 0;">New Grant Match</h1>
            <p style="margin: 8px 0 0;">GrantRadar found a {int(match.match_score * 100)}% match for you</p>
        </div>
        <div class="content">
            <h2 style="margin-top: 0;">{grant.title}</h2>
            <p><strong>Agency:</strong> {grant.funding_agency}</p>
            <p><span class="match-score">{int(match.match_score * 100)}% Match</span></p>

            {body_html}

            <a href="{grant.url}" class="cta-button">View Full Grant Details</a>
        </div>
        <div class="footer">
            <p>You're receiving this because you have grant alerts enabled.</p>
            <p>GrantRadar - AI-Powered Grant Discovery</p>
        </div>
    </div>
</body>
</html>
"""

        return EmailContent(
            subject=subject,
            body_html=body_html_full,
            body_text=f"Hi {user.name},\n\n{body_text}\n\nView grant: {grant.url}\n\n-- GrantRadar",
            from_email=settings.from_email,
            from_name=settings.from_name,
            to_email=user.email,
            to_name=user.name,
            tracking_id=str(match.match_id),
        )

    def generate_sms_content(
        self,
        grant: GrantInfo,
        match: MatchInfo,
        short_url: str,
    ) -> SMSContent:
        """
        Generate SMS content for critical alerts.

        Template: "GrantRadar Alert: {grant_title} matches your research {match_score}%.
                   Deadline: {deadline}. View: {short_url}"
        """
        # Truncate title to fit within 160 char limit
        title_max_len = 50
        title = grant.title[:title_max_len] + "..." if len(grant.title) > title_max_len else grant.title

        deadline_str = (
            grant.deadline.strftime("%m/%d")
            if grant.deadline
            else "Open"
        )

        message = (
            f"GrantRadar Alert: {title} matches your research "
            f"{int(match.match_score * 100)}%. Deadline: {deadline_str}. "
            f"View: {short_url}"
        )

        return SMSContent(
            message=message[:160],
            phone_number="",  # Will be filled in by caller
            short_url=short_url,
        )

    def generate_slack_blocks(
        self,
        user: UserInfo,
        grant: GrantInfo,
        match: MatchInfo,
    ) -> list[dict]:
        """Generate rich Slack message blocks."""
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"New Grant Match: {int(match.match_score * 100)}%",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{grant.title}*\n{grant.funding_agency}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Match Score:*\n{int(match.match_score * 100)}%",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Deadline:*\n{grant.deadline.strftime('%B %d, %Y') if grant.deadline else 'Open'}",
                    },
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Why it's a match:*\n{match.explanation or 'Strong alignment with your research profile.'}",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "View Grant Details",
                        },
                        "url": grant.url,
                        "style": "primary",
                    },
                ],
            },
        ]

    async def send_alert(self, payload: AlertPayload) -> list[DeliveryStatus]:
        """
        Send alert through all specified channels.

        Returns list of delivery statuses for each channel.
        """
        statuses = []

        for channel in payload.channels:
            try:
                if channel == DeliveryChannel.EMAIL:
                    email_content = await self.generate_email_content(
                        payload.user, payload.grant, payload.match
                    )
                    sendgrid = get_sendgrid_channel()
                    status = await sendgrid.send(email_content)
                    status.match_id = payload.match_id
                    statuses.append(status)

                elif channel == DeliveryChannel.SMS and payload.user.phone:
                    sms_content = self.generate_sms_content(
                        payload.grant,
                        payload.match,
                        short_url=f"{settings.frontend_url}/g/{payload.grant.grant_id}",
                    )
                    sms_content.phone_number = payload.user.phone
                    twilio = get_twilio_channel()
                    status = await twilio.send(sms_content)
                    status.match_id = payload.match_id
                    statuses.append(status)

                elif channel == DeliveryChannel.SLACK and payload.user.slack_webhook_url:
                    slack = get_slack_channel()
                    from agents.delivery.models import SlackContent

                    slack_content = SlackContent(
                        webhook_url=payload.user.slack_webhook_url,
                        text=f"New {int(payload.match.match_score * 100)}% grant match: {payload.grant.title}",
                        blocks=self.generate_slack_blocks(
                            payload.user, payload.grant, payload.match
                        ),
                    )
                    status = await slack.send(slack_content)
                    status.match_id = payload.match_id
                    statuses.append(status)

            except Exception as e:
                self.logger.error(
                    "channel_send_failed",
                    channel=channel,
                    match_id=str(payload.match_id),
                    error=str(e),
                )
                # Create failed status
                failed_status = DeliveryStatus(
                    alert_id=uuid4(),
                    match_id=payload.match_id,
                    channel=channel,
                    status="failed",
                    error_message=str(e),
                )
                statuses.append(failed_status)

        # Log alert to Redis for tracking
        self._log_alert_sent(payload, statuses)

        return statuses

    def _log_alert_sent(
        self, payload: AlertPayload, statuses: list[DeliveryStatus]
    ) -> None:
        """Log sent alert to Redis for tracking and analytics."""
        for status in statuses:
            alert_record = {
                "match_id": str(payload.match_id),
                "user_id": str(payload.user.user_id),
                "grant_id": str(payload.grant.grant_id),
                "channel": status.channel.value,
                "status": status.status,
                "sent_at": status.sent_at.isoformat() if status.sent_at else None,
                "provider_message_id": status.provider_message_id,
                "error_message": status.error_message,
                "grant_posted_at": (
                    payload.grant.posted_at.isoformat()
                    if payload.grant.posted_at
                    else None
                ),
            }

            # Calculate latency if we have posted_at
            if payload.grant.posted_at and status.sent_at:
                latency_seconds = (
                    status.sent_at - payload.grant.posted_at
                ).total_seconds()
                alert_record["latency_seconds"] = latency_seconds
                self.logger.info(
                    "alert_latency",
                    match_id=str(payload.match_id),
                    channel=status.channel.value,
                    latency_seconds=latency_seconds,
                    target_met=latency_seconds < 300,  # 5 minute target
                )

            self.redis_client.hset(
                f"{self.ALERTS_SENT_KEY}:{status.alert_id}",
                mapping=alert_record,
            )
            # Set expiry for cleanup (30 days)
            self.redis_client.expire(
                f"{self.ALERTS_SENT_KEY}:{status.alert_id}",
                60 * 60 * 24 * 30,
            )

    def should_batch_for_digest(self, user_id: UUID, priority: AlertPriority) -> bool:
        """
        Check if alert should be batched for digest.

        Medium priority alerts are batched if user has >3 medium matches per day.
        """
        if priority != AlertPriority.MEDIUM:
            return False

        digest_key = f"{self.DIGEST_KEY_PREFIX}{user_id}:{datetime.utcnow().strftime('%Y-%m-%d')}"
        count = self.redis_client.llen(digest_key)

        return count >= 3

    def add_to_digest_batch(self, payload: AlertPayload) -> None:
        """Add alert to user's digest batch."""
        digest_key = (
            f"{self.DIGEST_KEY_PREFIX}{payload.user.user_id}:"
            f"{datetime.utcnow().strftime('%Y-%m-%d')}"
        )

        self.redis_client.lpush(digest_key, payload.model_dump_json())
        # Expire at end of day + 1 hour buffer
        self.redis_client.expireat(
            digest_key,
            int(
                (
                    datetime.utcnow().replace(hour=23, minute=59, second=59)
                    + timedelta(hours=1)
                ).timestamp()
            ),
        )

    async def process_match_event(self, event_data: dict) -> None:
        """
        Process a match event from the Redis stream.

        This is the main entry point for the alerter. It respects user
        notification preferences including:
        - minimum_match_score: Skip alerts below user's threshold
        - email/sms/slack_notifications: Enable/disable specific channels
        - digest_frequency: Batch alerts for daily/weekly digests

        Args:
            event_data: The match event data from Redis stream.
        """
        try:
            match_event = MatchComputedEvent(**event_data)

            # Fetch user and grant details
            user_result = await self._fetch_user(match_event.user_id)
            grant = await self._fetch_grant(match_event.grant_id)

            if not user_result or not grant:
                self.logger.warning(
                    "missing_user_or_grant",
                    user_id=str(match_event.user_id),
                    grant_id=str(match_event.grant_id),
                )
                return

            user, preferences = user_result

            # Check user's minimum match score threshold
            if match_event.match_score < preferences.minimum_match_score:
                self.logger.debug(
                    "match_below_user_threshold",
                    match_id=str(match_event.match_id),
                    score=match_event.match_score,
                    user_threshold=preferences.minimum_match_score,
                )
                return

            # Determine priority and channels (respecting user preferences)
            priority = self.determine_priority(
                match_event.match_score, match_event.grant_deadline
            )

            if priority == AlertPriority.LOW:
                self.logger.debug(
                    "match_below_threshold",
                    match_id=str(match_event.match_id),
                    score=match_event.match_score,
                )
                return

            channels = self.determine_channels(priority, preferences)

            # If no channels are enabled, skip sending
            if not channels:
                self.logger.debug(
                    "no_channels_enabled",
                    match_id=str(match_event.match_id),
                    user_id=str(match_event.user_id),
                )
                return

            # Build payload
            payload = AlertPayload(
                match_id=match_event.match_id,
                user=user,
                grant=grant,
                match=MatchInfo(
                    match_id=match_event.match_id,
                    match_score=match_event.match_score,
                    matching_criteria=match_event.matching_criteria or [],
                    explanation=match_event.explanation,
                ),
                priority=priority,
                channels=channels,
            )

            # Route based on user's digest frequency preference
            if preferences.digest_frequency == "daily":
                # Batch all alerts for daily digest (except critical)
                if priority == AlertPriority.CRITICAL:
                    send_critical_alert.delay(payload.model_dump_json())
                else:
                    self.add_to_digest_batch(payload)
            elif preferences.digest_frequency == "weekly":
                # Batch all alerts for weekly digest (except critical)
                if priority == AlertPriority.CRITICAL:
                    send_critical_alert.delay(payload.model_dump_json())
                else:
                    self.add_to_digest_batch(payload)
            else:
                # Immediate delivery (default)
                if priority == AlertPriority.CRITICAL:
                    send_critical_alert.delay(payload.model_dump_json())
                elif priority == AlertPriority.HIGH:
                    send_high_priority_alert.delay(payload.model_dump_json())
                elif priority == AlertPriority.MEDIUM:
                    if self.should_batch_for_digest(user.user_id, priority):
                        self.add_to_digest_batch(payload)
                    else:
                        send_medium_priority_alert.delay(payload.model_dump_json())

            self.logger.info(
                "match_processed",
                match_id=str(match_event.match_id),
                priority=priority.value,
                channels=[c.value for c in channels],
                digest_frequency=preferences.digest_frequency,
            )

        except Exception as e:
            self.logger.error(
                "match_processing_failed",
                error=str(e),
                event_data=event_data,
            )
            raise

    async def _fetch_user(self, user_id: UUID) -> Optional[tuple[UserInfo, UserNotificationPreferences]]:
        """
        Fetch user information and notification preferences from database.

        Queries the users table and returns user details formatted
        for alert delivery, including email, phone, name, institution,
        and notification preferences.

        Args:
            user_id: The UUID of the user to fetch.

        Returns:
            Tuple of (UserInfo, UserNotificationPreferences) if user exists, None otherwise.
        """
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()

                if user is None:
                    self.logger.warning(
                        "user_not_found",
                        user_id=str(user_id),
                    )
                    return None

                user_info = UserInfo(
                    user_id=user.id,
                    name=user.name or user.email.split("@")[0],
                    email=user.email,
                    phone=user.phone,
                    slack_webhook_url=None,  # Not stored in User model currently
                    alert_preferences={},  # Could be extended with user preferences
                )

                # Extract notification preferences
                preferences = UserNotificationPreferences(
                    email_notifications=user.email_notifications,
                    sms_notifications=user.sms_notifications,
                    slack_notifications=user.slack_notifications,
                    digest_frequency=user.digest_frequency,
                    minimum_match_score=user.minimum_match_score,
                )

                return user_info, preferences

        except Exception as e:
            self.logger.error(
                "user_fetch_error",
                user_id=str(user_id),
                error=str(e),
            )
            return None

    async def _fetch_grant(self, grant_id: UUID) -> Optional[GrantInfo]:
        """
        Fetch grant information from database.

        Queries the grants table and returns grant details formatted
        for alert content generation, including title, agency, deadline,
        URL, and description.

        Args:
            grant_id: The UUID of the grant to fetch.

        Returns:
            GrantInfo if grant exists, None otherwise.
        """
        try:
            async with get_async_session() as session:
                result = await session.execute(
                    select(Grant).where(Grant.id == grant_id)
                )
                grant = result.scalar_one_or_none()

                if grant is None:
                    self.logger.warning(
                        "grant_not_found",
                        grant_id=str(grant_id),
                    )
                    return None

                # Extract eligibility criteria as a list of strings if available
                eligibility_criteria = []
                if grant.eligibility:
                    # Handle various eligibility formats
                    if isinstance(grant.eligibility, dict):
                        eligibility_criteria = [
                            f"{k}: {v}" for k, v in grant.eligibility.items()
                            if v and isinstance(v, (str, bool, int, float))
                        ]
                    elif isinstance(grant.eligibility, list):
                        eligibility_criteria = [str(item) for item in grant.eligibility]

                return GrantInfo(
                    grant_id=grant.id,
                    title=grant.title,
                    description=grant.description or "",
                    funding_agency=grant.agency or "Unknown Agency",
                    amount_min=float(grant.amount_min) if grant.amount_min else None,
                    amount_max=float(grant.amount_max) if grant.amount_max else None,
                    deadline=grant.deadline,
                    url=grant.url or "",
                    categories=grant.categories or [],
                    eligibility_criteria=eligibility_criteria,
                    posted_at=grant.posted_at,
                )

        except Exception as e:
            self.logger.error(
                "grant_fetch_error",
                grant_id=str(grant_id),
                error=str(e),
            )
            return None

    async def run(self) -> None:
        """
        Main run loop - consume from matches:computed stream.
        """
        self._ensure_consumer_group()

        self.logger.info("alerter_starting", stream=self.MATCHES_STREAM)

        while True:
            try:
                # Read from stream with consumer group
                messages = self.redis_client.xreadgroup(
                    self.CONSUMER_GROUP,
                    self.CONSUMER_NAME,
                    {self.MATCHES_STREAM: ">"},
                    count=10,
                    block=5000,  # 5 second block
                )

                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            # Parse the event data
                            if "data" in message_data:
                                event_data = json.loads(message_data["data"])
                            else:
                                event_data = message_data

                            await self.process_match_event(event_data)

                            # Acknowledge the message
                            self.redis_client.xack(
                                self.MATCHES_STREAM,
                                self.CONSUMER_GROUP,
                                message_id,
                            )

                        except Exception as e:
                            self.logger.error(
                                "message_processing_failed",
                                message_id=message_id,
                                error=str(e),
                            )
                            # Don't ACK - message will be redelivered

            except Exception as e:
                self.logger.error("stream_read_error", error=str(e))
                # Brief pause before retry
                import asyncio

                await asyncio.sleep(1)

    def close(self) -> None:
        """Clean up resources."""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None


# Celery Tasks

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def send_critical_alert(self, payload_json: str) -> dict:
    """
    Send critical priority alert (SMS + Email + Slack).

    This task runs on the 'critical' queue with highest priority.
    """
    import asyncio

    try:
        payload = AlertPayload.model_validate_json(payload_json)
        agent = AlertDeliveryAgent()

        # Run async send
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            statuses = loop.run_until_complete(agent.send_alert(payload))
        finally:
            loop.close()

        return {
            "match_id": str(payload.match_id),
            "priority": "critical",
            "channels_sent": len(statuses),
            "statuses": [
                {"channel": s.channel.value, "status": s.status}
                for s in statuses
            ],
        }

    except Exception as e:
        logger.error("critical_alert_failed", error=str(e))
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=120)
def send_high_priority_alert(self, payload_json: str) -> dict:
    """
    Send high priority alert (Email + Slack).

    This task runs on the 'high' queue.
    """
    import asyncio

    try:
        payload = AlertPayload.model_validate_json(payload_json)
        agent = AlertDeliveryAgent()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            statuses = loop.run_until_complete(agent.send_alert(payload))
        finally:
            loop.close()

        return {
            "match_id": str(payload.match_id),
            "priority": "high",
            "channels_sent": len(statuses),
            "statuses": [
                {"channel": s.channel.value, "status": s.status}
                for s in statuses
            ],
        }

    except Exception as e:
        logger.error("high_priority_alert_failed", error=str(e))
        raise self.retry(exc=e)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=300)
def send_medium_priority_alert(self, payload_json: str) -> dict:
    """
    Send medium priority alert (Email only).

    This task runs on the 'default' queue.
    """
    import asyncio

    try:
        payload = AlertPayload.model_validate_json(payload_json)
        agent = AlertDeliveryAgent()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            statuses = loop.run_until_complete(agent.send_alert(payload))
        finally:
            loop.close()

        return {
            "match_id": str(payload.match_id),
            "priority": "medium",
            "channels_sent": len(statuses),
            "statuses": [
                {"channel": s.channel.value, "status": s.status}
                for s in statuses
            ],
        }

    except Exception as e:
        logger.error("medium_priority_alert_failed", error=str(e))
        raise self.retry(exc=e)


@celery_app.task
def process_digest_batch(user_id: str, date_str: str) -> dict:
    """
    Process batched digest alerts for a user.

    Called at end of day to send digest email.
    """
    import asyncio

    agent = AlertDeliveryAgent()
    digest_key = f"{agent.DIGEST_KEY_PREFIX}{user_id}:{date_str}"

    # Get all pending alerts
    alert_data = agent.redis_client.lrange(digest_key, 0, -1)

    if not alert_data:
        return {"user_id": user_id, "alerts_processed": 0}

    alerts = [AlertPayload.model_validate_json(data) for data in alert_data]

    # Generate digest email
    # In production, this would be a separate template
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        # Send single digest email with all alerts
        # Implementation would combine all grants into one email
        pass
    finally:
        loop.close()

    # Clear processed batch
    agent.redis_client.delete(digest_key)

    return {"user_id": user_id, "alerts_processed": len(alerts)}


# Celery Beat schedule for digest processing
celery_app.conf.beat_schedule = {
    "process-daily-digests": {
        "task": "agents.delivery.alerter.process_all_digests",
        "schedule": 86400,  # Daily
        "options": {"queue": "default"},
    },
}


@celery_app.task
def process_all_digests() -> dict:
    """
    Process all pending digest batches.

    Called once daily by Celery Beat.
    """
    agent = AlertDeliveryAgent()
    date_str = datetime.utcnow().strftime("%Y-%m-%d")

    # Find all pending digest keys
    pattern = f"{agent.DIGEST_KEY_PREFIX}*:{date_str}"
    keys = agent.redis_client.keys(pattern)

    processed = 0
    for key in keys:
        # Extract user_id from key
        parts = key.split(":")
        if len(parts) >= 3:
            user_id = parts[2]
            process_digest_batch.delay(user_id, date_str)
            processed += 1

    return {"date": date_str, "digests_queued": processed}


# Entry point for running as standalone worker
if __name__ == "__main__":
    import asyncio

    agent = AlertDeliveryAgent()
    try:
        asyncio.run(agent.run())
    except KeyboardInterrupt:
        logger.info("alerter_shutting_down")
    finally:
        agent.close()
