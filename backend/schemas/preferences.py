"""
Notification preferences schemas for user settings.
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class DigestFrequency(str, Enum):
    """Notification digest frequency options."""

    IMMEDIATE = "immediate"
    DAILY = "daily"
    WEEKLY = "weekly"


class NotificationPreferencesResponse(BaseModel):
    """Schema for notification preferences response."""

    email_notifications: bool = Field(
        ...,
        description="Email notifications enabled",
    )
    sms_notifications: bool = Field(
        ...,
        description="SMS notifications enabled",
    )
    slack_notifications: bool = Field(
        ...,
        description="Slack notifications enabled",
    )
    digest_frequency: DigestFrequency = Field(
        ...,
        description="Notification frequency: immediate, daily, or weekly",
    )
    minimum_match_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Minimum match score threshold for notifications (0.0 to 1.0)",
    )

    class Config:
        from_attributes = True


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences."""

    email_notifications: Optional[bool] = Field(
        None,
        description="Enable/disable email notifications",
    )
    sms_notifications: Optional[bool] = Field(
        None,
        description="Enable/disable SMS notifications",
    )
    slack_notifications: Optional[bool] = Field(
        None,
        description="Enable/disable Slack notifications",
    )
    digest_frequency: Optional[DigestFrequency] = Field(
        None,
        description="Notification frequency: immediate, daily, or weekly",
    )
    minimum_match_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Minimum match score threshold for notifications (0.0 to 1.0)",
    )

    @field_validator("minimum_match_score")
    @classmethod
    def validate_minimum_match_score(cls, v: Optional[float]) -> Optional[float]:
        """Validate minimum_match_score is within valid range."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("minimum_match_score must be between 0.0 and 1.0")
        return v
