"""
Pipeline schemas for grant application tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ApplicationStageEnum(str, Enum):
    """Application pipeline stages."""

    RESEARCHING = "researching"
    WRITING = "writing"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    REJECTED = "rejected"


class PipelineItemCreate(BaseModel):
    """Schema for creating a new pipeline item."""

    grant_id: UUID = Field(..., description="ID of the grant to track")
    match_id: Optional[UUID] = Field(None, description="Optional match ID")
    stage: ApplicationStageEnum = Field(default=ApplicationStageEnum.RESEARCHING, description="Initial stage")
    notes: Optional[str] = Field(None, max_length=5000, description="Notes about this application")
    target_date: Optional[datetime] = Field(None, description="Target submission date")


class PipelineItemUpdate(BaseModel):
    """Schema for updating a pipeline item."""

    stage: Optional[ApplicationStageEnum] = Field(None, description="New stage")
    notes: Optional[str] = Field(None, max_length=5000, description="Updated notes")
    target_date: Optional[datetime] = Field(None, description="Updated target date")


class PipelineItemMove(BaseModel):
    """Schema for moving a pipeline item to a new stage."""

    stage: ApplicationStageEnum = Field(..., description="Target stage")


class GrantSummary(BaseModel):
    """Embedded grant summary for pipeline items."""

    id: UUID
    title: str
    agency: Optional[str] = None
    deadline: Optional[datetime] = None
    amount_min: Optional[int] = None
    amount_max: Optional[int] = None
    url: Optional[str] = None

    class Config:
        from_attributes = True


class PipelineItemResponse(BaseModel):
    """Schema for pipeline item response."""

    id: UUID = Field(..., description="Pipeline item ID")
    user_id: UUID = Field(..., description="User ID")
    grant_id: UUID = Field(..., description="Grant ID")
    match_id: Optional[UUID] = Field(None, description="Match ID")
    stage: ApplicationStageEnum = Field(..., description="Current stage")
    notes: Optional[str] = Field(None, description="User notes")
    target_date: Optional[datetime] = Field(None, description="Target date")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")

    # Embedded grant info
    grant: GrantSummary = Field(..., description="Grant details")

    # Computed fields
    days_until_deadline: Optional[int] = Field(None, description="Days until grant deadline (negative if past)")
    days_until_target: Optional[int] = Field(None, description="Days until target date (negative if past)")

    class Config:
        from_attributes = True


class PipelineStageGroup(BaseModel):
    """Schema for grouped pipeline items by stage."""

    stage: ApplicationStageEnum = Field(..., description="Stage name")
    items: list[PipelineItemResponse] = Field(default_factory=list, description="Items in this stage")
    count: int = Field(..., description="Number of items in stage")


class PipelineResponse(BaseModel):
    """Schema for full pipeline response grouped by stage."""

    stages: list[PipelineStageGroup] = Field(..., description="Pipeline items grouped by stage")
    total: int = Field(..., description="Total items in pipeline")


class PipelineStats(BaseModel):
    """Schema for pipeline statistics."""

    total: int = Field(..., description="Total applications")
    by_stage: dict[str, int] = Field(..., description="Count by stage")
    upcoming_deadlines: int = Field(..., description="Applications with deadlines in next 14 days")
    past_deadlines: int = Field(..., description="Applications with past deadlines")
