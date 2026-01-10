"""Funding alert schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from enum import Enum


class AlertFrequency(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class FundingAlertPreferencesCreate(BaseModel):
    """Create/update funding alert preferences."""

    enabled: bool = True
    frequency: AlertFrequency = AlertFrequency.WEEKLY
    min_match_score: int = Field(default=70, ge=0, le=100)
    include_deadlines: bool = True
    include_new_grants: bool = True
    include_insights: bool = True
    preferred_funders: Optional[List[str]] = None


class FundingAlertPreferencesResponse(BaseModel):
    """Funding alert preferences response."""

    id: UUID
    user_id: UUID
    enabled: bool
    frequency: AlertFrequency
    min_match_score: int
    include_deadlines: bool
    include_new_grants: bool
    include_insights: bool
    preferred_funders: Optional[List[str]]
    last_sent_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertGrantSummary(BaseModel):
    """Grant summary for alert email."""

    id: UUID
    title: str
    funder: str
    mechanism: Optional[str]
    amount_max: Optional[int]
    deadline: Optional[datetime]
    match_score: int
    match_reason: str


class AlertDeadlineSummary(BaseModel):
    """Deadline summary for alert email."""

    id: UUID
    title: str
    funder: Optional[str]
    sponsor_deadline: datetime
    days_until: int
    priority: str


class FundingAlertPreview(BaseModel):
    """Preview of what alert email would contain."""

    new_grants: List[AlertGrantSummary]
    upcoming_deadlines: List[AlertDeadlineSummary]
    personalized_insights: Optional[str]
    would_send: bool
    reason: Optional[str]  # Why it would/wouldn't send
