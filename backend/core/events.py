"""
GrantRadar Event Models
Pydantic models for Redis Streams event payloads
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PriorityLevel(str, Enum):
    """Priority levels for grant matches."""

    CRITICAL = "critical"  # Deadline within 7 days, high match score
    HIGH = "high"  # Deadline within 30 days, high match score
    MEDIUM = "medium"  # Good match, flexible deadline
    LOW = "low"  # Marginal match or distant deadline


class AlertChannel(str, Enum):
    """Available alert delivery channels."""

    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"
    WEBSOCKET = "websocket"


class BaseEvent(BaseModel):
    """Base event model with common fields."""

    event_id: UUID = Field(..., description="Unique identifier for this event")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event was created",
    )
    version: str = Field(
        default="1.0",
        description="Event schema version for backward compatibility",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class GrantDiscoveredEvent(BaseEvent):
    """
    Event emitted when a new grant is discovered by a scraper.

    Published to: grants:discovered stream
    """

    grant_id: UUID = Field(..., description="Unique identifier for the grant")
    source: str = Field(..., description="Source of the grant (e.g., 'grants.gov', 'nih_reporter')")
    title: str = Field(..., description="Grant title")
    url: str = Field(..., description="URL to the original grant posting")
    discovered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the grant was discovered",
    )
    funding_agency: Optional[str] = Field(
        default=None,
        description="Name of the funding agency",
    )
    estimated_amount: Optional[float] = Field(
        default=None,
        description="Estimated funding amount in USD",
    )
    deadline: Optional[datetime] = Field(
        default=None,
        description="Application deadline if known",
    )
    raw_data: Optional[dict] = Field(
        default=None,
        description="Raw data from the source for debugging",
    )


class GrantValidatedEvent(BaseEvent):
    """
    Event emitted when a grant passes quality validation.

    Published to: grants:validated stream
    """

    grant_id: UUID = Field(..., description="Unique identifier for the grant")
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score from validation (0.0 to 1.0)",
    )
    categories: list[str] = Field(
        default_factory=list,
        description="Inferred grant categories",
    )
    embedding_generated: bool = Field(
        default=False,
        description="Whether embedding was successfully generated",
    )
    validation_details: Optional[dict] = Field(
        default=None,
        description="Detailed validation results",
    )
    eligibility_criteria: Optional[list[str]] = Field(
        default=None,
        description="Extracted eligibility criteria",
    )
    keywords: Optional[list[str]] = Field(
        default=None,
        description="Extracted keywords for matching",
    )


class MatchComputedEvent(BaseEvent):
    """
    Event emitted when a grant-user match is computed.

    Published to: matches:computed stream
    """

    match_id: UUID = Field(..., description="Unique identifier for the match")
    grant_id: UUID = Field(..., description="Identifier of the matched grant")
    user_id: UUID = Field(..., description="Identifier of the matched user")
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Match score between user profile and grant (0.0 to 1.0)",
    )
    priority_level: PriorityLevel = Field(
        ...,
        description="Computed priority level for this match",
    )
    matching_criteria: Optional[list[str]] = Field(
        default=None,
        description="List of criteria that contributed to the match",
    )
    explanation: Optional[str] = Field(
        default=None,
        description="Human-readable explanation of the match",
    )
    grant_deadline: Optional[datetime] = Field(
        default=None,
        description="Grant deadline for priority calculation",
    )


class AlertPendingEvent(BaseEvent):
    """
    Event emitted when an alert is ready to be sent.

    Published to: alerts:pending stream
    """

    alert_id: UUID = Field(..., description="Unique identifier for the alert")
    match_id: UUID = Field(..., description="Identifier of the associated match")
    channel: AlertChannel = Field(..., description="Delivery channel for the alert")
    user_email: Optional[str] = Field(
        default=None,
        description="User email address (required for email channel)",
    )
    user_phone: Optional[str] = Field(
        default=None,
        description="User phone number (required for SMS channel)",
    )
    user_id: Optional[UUID] = Field(
        default=None,
        description="User ID for push/websocket channels",
    )
    alert_title: Optional[str] = Field(
        default=None,
        description="Alert title/subject",
    )
    alert_body: Optional[str] = Field(
        default=None,
        description="Alert body/content",
    )
    retry_count: int = Field(
        default=0,
        description="Number of delivery attempts",
    )
    max_retries: int = Field(
        default=3,
        description="Maximum delivery attempts before DLQ",
    )


class DeadLetterEvent(BaseEvent):
    """
    Event for messages that failed processing and moved to DLQ.

    Published to: dlq:<original_stream> stream
    """

    original_stream: str = Field(..., description="Original stream the message came from")
    original_message_id: str = Field(..., description="Original message ID in Redis")
    original_payload: dict = Field(..., description="Original event payload")
    error_message: str = Field(..., description="Error message from failed processing")
    error_type: str = Field(..., description="Exception type that caused the failure")
    failure_count: int = Field(..., description="Number of processing attempts")
    first_failure_at: datetime = Field(..., description="When the first failure occurred")
    last_failure_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the last failure occurred",
    )


# =============================================================================
# WebSocket Event Payloads
# =============================================================================


class WebSocketEvent(BaseModel):
    """Base class for WebSocket event payloads."""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event was created",
    )

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v),
        }


class NewMatchEvent(WebSocketEvent):
    """
    Event payload for 'new_match' WebSocket event.

    Sent when a grant is matched to a user profile.
    """

    grant_id: UUID = Field(..., description="ID of the matched grant")
    title: str = Field(..., description="Grant title")
    match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Match score between user profile and grant (0.0 to 1.0)",
    )
    deadline: Optional[datetime] = Field(
        default=None,
        description="Grant application deadline",
    )
    agency: Optional[str] = Field(
        default=None,
        description="Funding agency name",
    )
    amount_range: Optional[str] = Field(
        default=None,
        description="Funding amount range (e.g., '$50,000 - $100,000')",
    )


class DeadlineReminderEvent(WebSocketEvent):
    """
    Event payload for 'deadline_soon' WebSocket event.

    Sent 3 days before a grant deadline (configurable).
    """

    grant_id: UUID = Field(..., description="ID of the grant with upcoming deadline")
    title: str = Field(..., description="Grant title")
    days_remaining: int = Field(
        ...,
        ge=0,
        description="Number of days until deadline",
    )
    deadline: datetime = Field(..., description="Actual deadline datetime")
    url: Optional[str] = Field(
        default=None,
        description="URL to the grant opportunity",
    )


class GrantUpdateEvent(WebSocketEvent):
    """
    Event payload for 'grant_update' WebSocket event.

    Sent when a saved grant is updated (deadline changed, amount updated, etc.).
    """

    grant_id: UUID = Field(..., description="ID of the updated grant")
    title: str = Field(..., description="Grant title")
    update_type: str = Field(
        ...,
        description="Type of update (e.g., 'deadline_changed', 'amount_updated', 'description_updated')",
    )
    changes: Optional[dict] = Field(
        default=None,
        description="Dictionary of changed fields with old and new values",
    )
    message: Optional[str] = Field(
        default=None,
        description="Human-readable update message",
    )


class StatsUpdateEvent(WebSocketEvent):
    """
    Event payload for 'stats_update' WebSocket event.

    Sent to update dashboard counters in real-time.
    """

    new_grants_count: int = Field(
        default=0,
        ge=0,
        description="Number of new grants since last check",
    )
    high_matches_count: int = Field(
        default=0,
        ge=0,
        description="Number of high-scoring matches (>80%)",
    )
    pending_deadlines_count: int = Field(
        default=0,
        ge=0,
        description="Number of saved grants with upcoming deadlines",
    )
    total_saved_count: Optional[int] = Field(
        default=None,
        ge=0,
        description="Total number of saved grants",
    )
