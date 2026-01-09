"""
API Key Pydantic Schemas
Request and response schemas for API key management endpoints.
"""
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# Available scopes for documentation
AVAILABLE_SCOPES = [
    "read:grants",
    "write:grants",
    "read:applications",
    "write:applications",
    "read:matches",
    "read:profile",
    "write:profile",
    "read:analytics",
    "admin:api_keys",
]


class APIKeyCreate(BaseModel):
    """Schema for creating a new API key."""

    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Friendly name for the API key (e.g., 'My Integration', 'CI/CD Pipeline')",
        examples=["My Integration", "CI/CD Pipeline", "Data Sync"],
    )
    scopes: List[str] = Field(
        default=[],
        description="List of permission scopes for the API key",
        examples=[["read:grants", "read:applications"]],
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Optional expiration datetime (ISO 8601 format). If not set, key never expires.",
    )
    rate_limit: int = Field(
        default=1000,
        ge=1,
        le=100000,
        description="Maximum requests per hour (default: 1000)",
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Validate that all scopes are known."""
        invalid_scopes = [scope for scope in v if scope not in AVAILABLE_SCOPES]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}. Valid scopes are: {AVAILABLE_SCOPES}")
        return v


class APIKeyCreateResponse(BaseModel):
    """
    Response schema for API key creation.

    IMPORTANT: This is the ONLY time the plain text API key is returned.
    Store it securely - it cannot be recovered later.
    """

    id: UUID = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Friendly name for the API key")
    key: str = Field(
        ...,
        description="The plain text API key. STORE THIS SECURELY - it will not be shown again!",
    )
    key_prefix: str = Field(..., description="First 8 characters of the key for identification")
    scopes: List[str] = Field(..., description="Permission scopes granted to this key")
    rate_limit: int = Field(..., description="Maximum requests per hour")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime, if set")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class APIKeyResponse(BaseModel):
    """Schema for API key information (without the actual key)."""

    id: UUID = Field(..., description="Unique identifier for the API key")
    name: str = Field(..., description="Friendly name for the API key")
    key_prefix: str = Field(..., description="First 8 characters of the key for identification")
    scopes: List[str] = Field(..., description="Permission scopes granted to this key")
    rate_limit: int = Field(..., description="Maximum requests per hour")
    request_count: int = Field(..., description="Total number of requests made with this key")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime, if set")
    is_active: bool = Field(..., description="Whether the key is currently active")
    created_at: datetime = Field(..., description="Creation timestamp")

    class Config:
        from_attributes = True


class APIKeyListResponse(BaseModel):
    """Schema for listing API keys."""

    keys: List[APIKeyResponse] = Field(..., description="List of API keys")
    total: int = Field(..., description="Total number of API keys")


class APIKeyRotateResponse(BaseModel):
    """
    Response schema for API key rotation.

    Returns the new key - store it securely!
    """

    id: UUID = Field(..., description="Unique identifier for the NEW API key")
    name: str = Field(..., description="Friendly name (copied from old key)")
    key: str = Field(
        ...,
        description="The NEW plain text API key. STORE THIS SECURELY - it will not be shown again!",
    )
    key_prefix: str = Field(..., description="First 8 characters of the new key")
    scopes: List[str] = Field(..., description="Permission scopes (copied from old key)")
    rate_limit: int = Field(..., description="Maximum requests per hour")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime, if set")
    created_at: datetime = Field(..., description="Creation timestamp")
    old_key_id: UUID = Field(..., description="ID of the revoked old key")

    class Config:
        from_attributes = True


class APIKeyUsageStats(BaseModel):
    """Schema for API key usage statistics."""

    id: UUID = Field(..., description="API key ID")
    name: str = Field(..., description="API key name")
    key_prefix: str = Field(..., description="First 8 characters of the key")
    total_requests: int = Field(..., description="Total number of requests made")
    rate_limit: int = Field(..., description="Maximum requests per hour")
    last_used_at: Optional[datetime] = Field(None, description="Last usage timestamp")
    created_at: datetime = Field(..., description="Creation timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")
    is_active: bool = Field(..., description="Whether the key is active")
    scopes: List[str] = Field(..., description="Permission scopes")


class APIKeyUpdateScopes(BaseModel):
    """Schema for updating API key scopes."""

    scopes: List[str] = Field(
        ...,
        description="New list of permission scopes",
        examples=[["read:grants", "read:applications"]],
    )

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, v: List[str]) -> List[str]:
        """Validate that all scopes are known."""
        invalid_scopes = [scope for scope in v if scope not in AVAILABLE_SCOPES]
        if invalid_scopes:
            raise ValueError(f"Invalid scopes: {invalid_scopes}. Valid scopes are: {AVAILABLE_SCOPES}")
        return v


class AvailableScopesResponse(BaseModel):
    """Schema for listing available scopes."""

    scopes: List[str] = Field(
        default=AVAILABLE_SCOPES,
        description="List of available permission scopes",
    )


class APIKeyDeleteResponse(BaseModel):
    """Schema for API key deletion response."""

    success: bool = Field(..., description="Whether the key was successfully revoked")
    message: str = Field(..., description="Status message")
    id: UUID = Field(..., description="ID of the revoked API key")
