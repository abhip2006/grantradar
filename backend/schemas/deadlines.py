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
    """Deadline status values."""

    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class DeadlinePriority(str, Enum):
    """Deadline priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeadlineCreate(BaseModel):
    """Schema for creating a new deadline."""

    title: str = Field(..., min_length=1, max_length=500, description="Deadline title")
    sponsor_deadline: datetime = Field(..., description="Official sponsor deadline")
    grant_id: Optional[UUID] = Field(None, description="Optional linked grant ID")
    description: Optional[str] = Field(None, description="Detailed description")
    funder: Optional[str] = Field(None, max_length=100, description="Funding organization")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism type")
    internal_deadline: Optional[datetime] = Field(None, description="Internal institutional deadline")
    priority: DeadlinePriority = Field(
        DeadlinePriority.MEDIUM,
        description="Priority level"
    )
    url: Optional[str] = Field(None, max_length=1000, description="URL to grant opportunity")
    notes: Optional[str] = Field(None, description="Additional notes")
    color: str = Field(
        "#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for calendar display"
    )


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
    color: Optional[str] = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Hex color code for calendar display"
    )


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
        """Check if deadline is overdue and still active."""
        return self.days_until_deadline < 0 and self.status == DeadlineStatus.ACTIVE

    class Config:
        from_attributes = True


class DeadlineList(BaseModel):
    """Schema for list of deadlines."""

    items: List[DeadlineResponse] = Field(..., description="List of deadlines")
    total: int = Field(..., description="Total count")


class LinkGrantRequest(BaseModel):
    """Schema for linking a grant to create a deadline."""

    grant_id: UUID = Field(..., description="Grant ID to link")
