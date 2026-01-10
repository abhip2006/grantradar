"""
Deadline schemas for request/response models.
Provides Pydantic models for deadline management API endpoints.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field


class DeadlineStatus(str, Enum):
    """Deadline workflow status values."""

    NOT_STARTED = "not_started"
    DRAFTING = "drafting"
    INTERNAL_REVIEW = "internal_review"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    AWARDED = "awarded"
    REJECTED = "rejected"


class DeadlinePriority(str, Enum):
    """Deadline priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# Status display configuration for UI
STATUS_CONFIG = {
    DeadlineStatus.NOT_STARTED: {"label": "Not Started", "color": "gray", "order": 0},
    DeadlineStatus.DRAFTING: {"label": "Drafting", "color": "blue", "order": 1},
    DeadlineStatus.INTERNAL_REVIEW: {"label": "Internal Review", "color": "yellow", "order": 2},
    DeadlineStatus.SUBMITTED: {"label": "Submitted", "color": "purple", "order": 3},
    DeadlineStatus.UNDER_REVIEW: {"label": "Under Review", "color": "orange", "order": 4},
    DeadlineStatus.AWARDED: {"label": "Awarded", "color": "green", "order": 5},
    DeadlineStatus.REJECTED: {"label": "Rejected", "color": "red", "order": 6},
}

# Pre-built recurrence rules for common grant cycles
RECURRENCE_PRESETS = {
    "nih_standard": {
        "label": "NIH Standard (Feb 5, Jun 5, Oct 5)",
        "rule": "FREQ=YEARLY;BYMONTH=2,6,10;BYMONTHDAY=5",
    },
    "nih_aids": {
        "label": "NIH AIDS (Jan 7, May 7, Sep 7)",
        "rule": "FREQ=YEARLY;BYMONTH=1,5,9;BYMONTHDAY=7",
    },
    "nsf_quarterly": {
        "label": "NSF Quarterly",
        "rule": "FREQ=YEARLY;BYMONTH=1,4,7,10;BYMONTHDAY=15",
    },
    "annual": {
        "label": "Annual (same date each year)",
        "rule": "FREQ=YEARLY",
    },
}


class DeadlineCreate(BaseModel):
    """Schema for creating a new deadline."""

    title: str = Field(..., min_length=1, max_length=500, description="Deadline title")
    sponsor_deadline: datetime = Field(..., description="Official sponsor deadline")
    grant_id: Optional[UUID] = Field(None, description="Optional linked grant ID")
    description: Optional[str] = Field(None, description="Detailed description")
    funder: Optional[str] = Field(None, max_length=100, description="Funding organization")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism type")
    internal_deadline: Optional[datetime] = Field(None, description="Internal institutional deadline")
    status: DeadlineStatus = Field(DeadlineStatus.NOT_STARTED, description="Initial status")
    priority: DeadlinePriority = Field(DeadlinePriority.MEDIUM, description="Priority level")
    url: Optional[str] = Field(None, max_length=1000, description="URL to grant opportunity")
    notes: Optional[str] = Field(None, description="Additional notes")
    color: str = Field("#3B82F6", pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code for calendar display")
    # Recurring deadline fields
    is_recurring: bool = Field(False, description="Whether this is a recurring deadline template")
    recurrence_rule: Optional[str] = Field(None, max_length=255, description="RRULE format recurrence rule (RFC 5545)")
    # Reminder configuration
    reminder_config: List[int] = Field(default=[30, 14, 7, 3, 1], description="Days before deadline to send reminders")


class DeadlineUpdate(BaseModel):
    """Schema for updating a deadline."""

    title: Optional[str] = Field(None, min_length=1, max_length=500, description="Deadline title")
    sponsor_deadline: Optional[datetime] = Field(None, description="Official sponsor deadline")
    grant_id: Optional[UUID] = Field(None, description="Optional linked grant ID")
    description: Optional[str] = Field(None, description="Detailed description")
    funder: Optional[str] = Field(None, max_length=100, description="Funding organization")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism type")
    internal_deadline: Optional[datetime] = Field(None, description="Internal institutional deadline")
    status: Optional[DeadlineStatus] = Field(None, description="Deadline status")
    priority: Optional[DeadlinePriority] = Field(None, description="Priority level")
    url: Optional[str] = Field(None, max_length=1000, description="URL to grant opportunity")
    notes: Optional[str] = Field(None, description="Additional notes")
    color: Optional[str] = Field(None, pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color code for calendar display")
    # Recurring deadline fields
    is_recurring: Optional[bool] = Field(None, description="Whether this is a recurring deadline template")
    recurrence_rule: Optional[str] = Field(None, max_length=255, description="RRULE format recurrence rule (RFC 5545)")
    # Reminder configuration
    reminder_config: Optional[List[int]] = Field(None, description="Days before deadline to send reminders")


class DeadlineResponse(BaseModel):
    """Schema for deadline response."""

    id: UUID = Field(..., description="Deadline ID")
    user_id: UUID = Field(..., description="Owner user ID")
    grant_id: Optional[UUID] = Field(None, description="Linked grant ID")
    title: str = Field(..., description="Deadline title")
    description: Optional[str] = Field(None, description="Detailed description")
    funder: Optional[str] = Field(None, description="Funding organization")
    mechanism: Optional[str] = Field(None, description="Grant mechanism type")
    sponsor_deadline: datetime = Field(..., description="Official sponsor deadline")
    internal_deadline: Optional[datetime] = Field(None, description="Internal institutional deadline")
    status: DeadlineStatus = Field(..., description="Deadline status")
    priority: DeadlinePriority = Field(..., description="Priority level")
    url: Optional[str] = Field(None, description="URL to grant opportunity")
    notes: Optional[str] = Field(None, description="Additional notes")
    color: str = Field(..., description="Hex color code for calendar display")
    # Recurring fields
    is_recurring: bool = Field(False, description="Whether this is a recurring deadline template")
    recurrence_rule: Optional[str] = Field(None, description="RRULE format recurrence rule")
    parent_deadline_id: Optional[UUID] = Field(None, description="Parent recurring deadline ID")
    # Reminder configuration
    reminder_config: List[int] = Field(default=[30, 14, 7, 3, 1], description="Days before deadline to send reminders")
    escalation_sent: bool = Field(False, description="Whether escalation alert has been sent")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def days_until_deadline(self) -> int:
        """Calculate days until the sponsor deadline."""
        now = datetime.now(timezone.utc)
        deadline = self.sponsor_deadline
        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)
        delta = deadline - now
        return delta.days

    @computed_field
    @property
    def is_overdue(self) -> bool:
        """Check if deadline is overdue and not yet submitted/awarded/rejected."""
        terminal_statuses = {DeadlineStatus.SUBMITTED, DeadlineStatus.AWARDED, DeadlineStatus.REJECTED}
        return self.days_until_deadline < 0 and self.status not in terminal_statuses

    @computed_field
    @property
    def urgency_level(self) -> str:
        """Determine urgency level based on days remaining and status."""
        if self.status in {DeadlineStatus.AWARDED, DeadlineStatus.REJECTED, DeadlineStatus.SUBMITTED}:
            return "none"
        days = self.days_until_deadline
        if days < 0:
            return "overdue"
        elif days <= 3:
            return "critical"
        elif days <= 7:
            return "high"
        elif days <= 14:
            return "medium"
        else:
            return "low"

    @computed_field
    @property
    def status_config(self) -> dict:
        """Get status display configuration."""
        return STATUS_CONFIG.get(self.status, {"label": self.status.value, "color": "gray", "order": 99})

    class Config:
        from_attributes = True


class DeadlineList(BaseModel):
    """Schema for list of deadlines."""

    items: List[DeadlineResponse] = Field(..., description="List of deadlines")
    total: int = Field(..., description="Total count")


class LinkGrantRequest(BaseModel):
    """Schema for linking a grant to create a deadline."""

    grant_id: UUID = Field(..., description="Grant ID to link")


class StatusChangeRequest(BaseModel):
    """Schema for changing a deadline's status with optional notes."""

    status: DeadlineStatus = Field(..., description="New status")
    notes: Optional[str] = Field(None, max_length=1000, description="Notes about the status change")


class StatusHistoryResponse(BaseModel):
    """Schema for status history entry."""

    id: UUID = Field(..., description="History entry ID")
    deadline_id: UUID = Field(..., description="Deadline ID")
    previous_status: Optional[str] = Field(None, description="Status before change")
    new_status: str = Field(..., description="Status after change")
    changed_by: Optional[UUID] = Field(None, description="User who made the change")
    changed_at: datetime = Field(..., description="When the change was made")
    notes: Optional[str] = Field(None, description="Notes about the change")

    class Config:
        from_attributes = True


class StatusHistoryList(BaseModel):
    """Schema for list of status history entries."""

    items: List[StatusHistoryResponse] = Field(..., description="List of history entries")
    total: int = Field(..., description="Total count")


class RecurrencePreset(BaseModel):
    """Schema for recurrence preset information."""

    key: str = Field(..., description="Preset key")
    label: str = Field(..., description="Human-readable label")
    rule: str = Field(..., description="RRULE format rule")


class RecurrencePresetsResponse(BaseModel):
    """Schema for list of recurrence presets."""

    presets: List[RecurrencePreset] = Field(..., description="Available presets")


class ReminderConfigUpdate(BaseModel):
    """Schema for updating reminder configuration."""

    reminder_config: List[int] = Field(
        ..., min_length=1, max_length=10, description="Days before deadline to send reminders (e.g., [30, 14, 7, 3, 1])"
    )


class DeadlineStatsResponse(BaseModel):
    """Schema for deadline statistics."""

    total: int = Field(..., description="Total deadlines")
    by_status: dict = Field(..., description="Count by status")
    by_priority: dict = Field(..., description="Count by priority")
    overdue: int = Field(..., description="Overdue count")
    due_this_week: int = Field(..., description="Due within 7 days")
    due_this_month: int = Field(..., description="Due within 30 days")
    recurring_templates: int = Field(..., description="Recurring deadline templates")
