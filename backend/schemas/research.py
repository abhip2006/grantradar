"""Deep research schemas."""
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from enum import Enum


class ResearchStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ResearchGrantResult(BaseModel):
    """A grant discovered through research."""
    id: UUID
    title: str
    funder: str
    mechanism: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    amount_min: Optional[int] = None
    amount_max: Optional[int] = None
    relevance_score: float
    match_reasons: List[str]


class ResearchSessionCreate(BaseModel):
    """Create a new research session."""
    query: str = Field(..., min_length=10, max_length=2000)


class ResearchSessionResponse(BaseModel):
    """Research session response."""
    id: UUID
    user_id: UUID
    query: str
    status: ResearchStatus
    results: Optional[List[ResearchGrantResult]] = None
    insights: Optional[str] = None
    grants_found: Optional[int] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ResearchSessionListItem(BaseModel):
    """Summary item for research session listing."""
    id: UUID
    query: str
    status: ResearchStatus
    grants_found: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class ResearchQuickSearch(BaseModel):
    """Quick synchronous research search."""
    query: str = Field(..., min_length=5, max_length=500)
    max_results: int = Field(default=10, ge=1, le=50)
