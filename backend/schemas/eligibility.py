"""Eligibility check schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from enum import Enum


class EligibilityStatus(str, Enum):
    """Status of eligibility assessment."""
    ELIGIBLE = "eligible"
    NOT_ELIGIBLE = "not_eligible"
    PARTIAL = "partial"  # Meets some criteria
    UNKNOWN = "unknown"  # Not enough info


class EligibilityCriterion(BaseModel):
    """Individual eligibility criterion result."""
    criterion: str
    met: bool
    explanation: str
    confidence: float = Field(ge=0.0, le=1.0)


class EligibilityCheckRequest(BaseModel):
    """Request to check eligibility for a grant."""
    grant_id: UUID
    additional_context: Optional[str] = None  # Extra info about researcher


class EligibilityCheckResponse(BaseModel):
    """Eligibility check result."""
    grant_id: UUID
    grant_title: str
    overall_status: EligibilityStatus
    overall_confidence: float = Field(ge=0.0, le=1.0)
    criteria: List[EligibilityCriterion]
    summary: str
    recommendations: List[str]
    missing_info: List[str]  # What info would help
    session_id: Optional[UUID] = None  # Chat session for follow-up
    checked_at: datetime


class EligibilityFollowUpRequest(BaseModel):
    """Follow-up question in eligibility conversation."""
    session_id: UUID
    message: str


class EligibilityFollowUpResponse(BaseModel):
    """Response to follow-up question."""
    session_id: UUID
    response: str
    updated_status: Optional[EligibilityStatus] = None
    updated_criteria: Optional[List[EligibilityCriterion]] = None
