"""
Calendar schemas for deadline calendar view.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CalendarEventType(str, Enum):
    """Type of calendar event based on source."""

    SAVED = "saved"
    PIPELINE = "pipeline"


class UrgencyLevel(str, Enum):
    """Urgency level based on days until deadline."""

    CRITICAL = "critical"  # < 7 days
    WARNING = "warning"  # < 14 days
    NORMAL = "normal"  # >= 14 days


class CalendarEvent(BaseModel):
    """Schema for a calendar deadline event."""

    grant_id: UUID = Field(..., description="ID of the grant")
    title: str = Field(..., description="Grant title")
    deadline: datetime = Field(..., description="Grant deadline")
    event_type: CalendarEventType = Field(..., description="Source type: saved match or pipeline")
    stage: Optional[str] = Field(None, description="Pipeline stage if from pipeline")
    urgency: UrgencyLevel = Field(..., description="Urgency level based on days remaining")
    days_until_deadline: int = Field(..., description="Days until deadline (negative if past)")
    agency: Optional[str] = Field(None, description="Funding agency")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    url: Optional[str] = Field(None, description="Grant URL")

    # Optional related IDs
    match_id: Optional[UUID] = Field(None, description="Match ID if from saved matches")
    pipeline_item_id: Optional[UUID] = Field(None, description="Pipeline item ID if from pipeline")

    class Config:
        from_attributes = True


class CalendarDay(BaseModel):
    """Schema for a single day on the calendar."""

    date: datetime = Field(..., description="The date")
    events: list[CalendarEvent] = Field(default_factory=list, description="Events on this day")
    count: int = Field(..., description="Number of events on this day")


class CalendarDeadlinesResponse(BaseModel):
    """Schema for calendar deadlines response."""

    events: list[CalendarEvent] = Field(default_factory=list, description="All deadline events")
    total: int = Field(..., description="Total number of events")
    start_date: datetime = Field(..., description="Start of date range")
    end_date: datetime = Field(..., description="End of date range")


class CalendarMonthResponse(BaseModel):
    """Schema for calendar month view response."""

    year: int = Field(..., description="Year")
    month: int = Field(..., description="Month (1-12)")
    days: list[CalendarDay] = Field(default_factory=list, description="Days with events")
    total_events: int = Field(..., description="Total events in month")


class UpcomingDeadline(BaseModel):
    """Schema for an upcoming deadline with urgency."""

    grant_id: UUID = Field(..., description="Grant ID")
    title: str = Field(..., description="Grant title")
    deadline: datetime = Field(..., description="Deadline datetime")
    days_until_deadline: int = Field(..., description="Days remaining")
    urgency: UrgencyLevel = Field(..., description="Urgency level")
    event_type: CalendarEventType = Field(..., description="Source type")
    stage: Optional[str] = Field(None, description="Pipeline stage if applicable")
    agency: Optional[str] = Field(None, description="Funding agency")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")

    class Config:
        from_attributes = True


class UpcomingDeadlinesResponse(BaseModel):
    """Schema for upcoming deadlines response."""

    deadlines: list[UpcomingDeadline] = Field(default_factory=list, description="Upcoming deadlines sorted by date")
    total: int = Field(..., description="Total count")
    critical_count: int = Field(..., description="Count of critical (< 7 days) deadlines")
    warning_count: int = Field(..., description="Count of warning (< 14 days) deadlines")
