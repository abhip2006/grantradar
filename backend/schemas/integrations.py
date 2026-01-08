"""
Calendar Integration Schemas
Pydantic models for calendar integration API.
"""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProviderStatus(BaseModel):
    """Status of a single calendar provider."""

    connected: bool = Field(..., description="Whether the provider is connected")
    calendar_id: Optional[str] = Field(None, description="ID of the synced calendar")
    last_synced_at: Optional[str] = Field(None, description="ISO timestamp of last sync")
    sync_enabled: bool = Field(default=False, description="Whether sync is enabled")


class CalendarStatusResponse(BaseModel):
    """Status response for all calendar providers."""

    google: ProviderStatus = Field(..., description="Google Calendar status")
    outlook: ProviderStatus = Field(..., description="Outlook Calendar status")


class CalendarIntegrationResponse(BaseModel):
    """Calendar integration details."""

    id: UUID = Field(..., description="Integration ID")
    user_id: UUID = Field(..., description="User ID")
    provider: str = Field(..., description="Calendar provider (google, outlook)")
    calendar_id: str = Field(..., description="Calendar ID in provider")
    sync_enabled: bool = Field(..., description="Whether sync is enabled")
    last_synced_at: Optional[datetime] = Field(None, description="Last sync timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class OAuthCallbackRequest(BaseModel):
    """OAuth callback parameters."""

    code: str = Field(..., description="Authorization code from OAuth provider")
    state: str = Field(..., description="State parameter for CSRF protection")


class SyncResponse(BaseModel):
    """Response from sync operation."""

    synced_count: int = Field(..., description="Number of events synced")
    last_synced_at: datetime = Field(..., description="Timestamp of sync completion")


class UpdateIntegrationRequest(BaseModel):
    """Request to update integration settings."""

    sync_enabled: bool = Field(..., description="Enable or disable sync")
