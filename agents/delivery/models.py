"""
GrantRadar Alert Delivery Models
Pydantic models for alert payloads and delivery tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AlertPriority(str, Enum):
    """Priority levels for alert routing."""

    CRITICAL = "critical"  # >95% match + <14 days deadline -> SMS + Email + Slack
    HIGH = "high"  # 85-95% match -> Email + Slack
    MEDIUM = "medium"  # 70-85% match -> Email only (batched if >3/day)
    LOW = "low"  # Below threshold, no alert


class DeliveryChannel(str, Enum):
    """Available delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    SLACK = "slack"


class UserNotificationPreferences(BaseModel):
    """User notification preferences for alert delivery."""

    email_notifications: bool = True
    sms_notifications: bool = False
    slack_notifications: bool = False
    digest_frequency: str = "immediate"  # immediate, daily, weekly
    minimum_match_score: float = Field(default=0.7, ge=0.0, le=1.0)


class UserInfo(BaseModel):
    """User information for alert delivery."""

    user_id: UUID
    name: str
    email: str
    phone: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    alert_preferences: dict = Field(default_factory=dict)


class GrantInfo(BaseModel):
    """Grant information for alert content generation."""

    grant_id: UUID
    title: str
    description: str
    funding_agency: str
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    deadline: Optional[datetime] = None
    url: str
    categories: list[str] = Field(default_factory=list)
    eligibility_criteria: list[str] = Field(default_factory=list)
    posted_at: Optional[datetime] = None


class MatchInfo(BaseModel):
    """Match details for alert generation."""

    match_id: UUID
    match_score: float = Field(..., ge=0.0, le=1.0)
    matching_criteria: list[str] = Field(default_factory=list)
    explanation: Optional[str] = None


class AlertPayload(BaseModel):
    """Complete payload for alert processing."""

    match_id: UUID
    user: UserInfo
    grant: GrantInfo
    match: MatchInfo
    priority: AlertPriority
    channels: list[DeliveryChannel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class EmailContent(BaseModel):
    """Generated email content."""

    subject: str = Field(..., max_length=100)
    body_html: str
    body_text: str
    from_email: str
    from_name: str
    to_email: str
    to_name: Optional[str] = None
    reply_to: Optional[str] = None
    tracking_id: Optional[str] = None


class SMSContent(BaseModel):
    """Generated SMS content."""

    message: str = Field(..., max_length=160)
    phone_number: str
    short_url: Optional[str] = None


class SlackContent(BaseModel):
    """Generated Slack message content."""

    webhook_url: str
    text: str
    blocks: Optional[list[dict]] = None


class DeliveryStatus(BaseModel):
    """Track delivery status for an alert."""

    alert_id: UUID
    match_id: UUID
    channel: DeliveryChannel
    status: str = "pending"  # pending, sent, delivered, failed
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    error_message: Optional[str] = None
    provider_message_id: Optional[str] = None
    retry_count: int = 0


class DigestBatch(BaseModel):
    """Batch of medium-priority alerts for digest delivery."""

    user_id: UUID
    alerts: list[AlertPayload]
    created_at: datetime = Field(default_factory=datetime.utcnow)
