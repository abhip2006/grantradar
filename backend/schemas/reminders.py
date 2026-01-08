"""
Reminder Schemas
Pydantic models for reminder API.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ReminderScheduleCreate(BaseModel):
    """Create a single reminder schedule."""

    reminder_type: str = Field(..., pattern="^(email|sms|push)$")
    remind_before_minutes: int = Field(..., ge=5, le=20160)  # 5 min to 2 weeks


class BulkReminderCreate(BaseModel):
    """Create multiple reminders at once."""

    reminders: List[ReminderScheduleCreate]


class ReminderScheduleResponse(BaseModel):
    """Reminder schedule response."""

    id: UUID
    deadline_id: UUID
    reminder_type: str
    remind_before_minutes: int
    is_sent: bool
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReminderSettingsResponse(BaseModel):
    """User reminder settings."""

    email_enabled: bool
    sms_enabled: bool
    default_reminders: List[int]  # minutes before deadline


class ReminderSettingsUpdate(BaseModel):
    """Update reminder settings."""

    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
