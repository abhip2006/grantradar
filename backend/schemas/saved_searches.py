"""
Saved search schemas for managing saved filter combinations.
"""
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SavedSearchFilters(BaseModel):
    """Schema for saved search filter configuration."""

    search_query: Optional[str] = Field(None, description="Text search query")
    source: Optional[str] = Field(None, description="Grant source filter (federal, foundation, state)")
    min_score: Optional[float] = Field(None, ge=0, le=100, description="Minimum match score (0-100)")
    min_amount: Optional[int] = Field(None, ge=0, description="Minimum funding amount")
    max_amount: Optional[int] = Field(None, ge=0, description="Maximum funding amount")
    categories: Optional[list[str]] = Field(None, description="Category filters")
    show_saved_only: Optional[bool] = Field(None, description="Show only saved grants")
    active_only: Optional[bool] = Field(None, description="Show only active grants")

    class Config:
        extra = "allow"  # Allow additional filter fields for flexibility


class SavedSearchCreate(BaseModel):
    """Schema for creating a new saved search."""

    name: str = Field(..., min_length=1, max_length=100, description="Name for the saved search")
    filters: SavedSearchFilters = Field(..., description="Search filters to save")
    alert_enabled: bool = Field(default=False, description="Enable email alerts for new matches")


class SavedSearchUpdate(BaseModel):
    """Schema for updating a saved search."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="New name")
    filters: Optional[SavedSearchFilters] = Field(None, description="Updated filters")
    alert_enabled: Optional[bool] = Field(None, description="Enable/disable alerts")


class SavedSearchResponse(BaseModel):
    """Schema for saved search response."""

    id: UUID = Field(..., description="Saved search ID")
    name: str = Field(..., description="Saved search name")
    filters: dict[str, Any] = Field(..., description="Saved filter configuration")
    alert_enabled: bool = Field(..., description="Whether alerts are enabled")
    created_at: datetime = Field(..., description="When the search was saved")
    last_alerted_at: Optional[datetime] = Field(None, description="Last alert timestamp")

    class Config:
        from_attributes = True


class SavedSearchList(BaseModel):
    """Schema for list of saved searches."""

    saved_searches: list[SavedSearchResponse] = Field(..., description="List of saved searches")
    total: int = Field(..., description="Total number of saved searches")
