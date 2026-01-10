"""
Sharing and Resource Permission Schemas
Pydantic models for resource-level access control and sharing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ResourceType(str, Enum):
    """Types of resources that can be shared."""

    GRANT = "grant"
    APPLICATION = "application"
    DOCUMENT = "document"


class PermissionLevel(str, Enum):
    """Permission levels for shared resources."""

    VIEW = "view"
    COMMENT = "comment"
    EDIT = "edit"
    ADMIN = "admin"


# =============================================================================
# Share Resource Request/Response Schemas
# =============================================================================


class ShareResourceRequest(BaseModel):
    """Request to share a resource with a user."""

    user_id: Optional[UUID] = Field(None, description="ID of the user to share with (required if email not provided)")
    email: Optional[str] = Field(None, description="Email of the user to share with (required if user_id not provided)")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.VIEW,
        description="Permission level to grant: view, comment, edit, admin",
    )
    expires_at: Optional[datetime] = Field(None, description="When the permission expires (null = never)")
    notify: bool = Field(default=True, description="Whether to send notification to the user")
    message: Optional[str] = Field(None, max_length=1000, description="Optional message to include in notification")

    @field_validator("email", "user_id")
    @classmethod
    def validate_identifier(cls, v, info):
        """At least one of user_id or email must be provided."""
        return v


class ResourcePermissionResponse(BaseModel):
    """Response schema for a resource permission."""

    id: UUID = Field(..., description="Unique identifier for the permission")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    user_id: Optional[UUID] = Field(None, description="ID of the user with permission")
    team_id: Optional[UUID] = Field(None, description="ID of the team with permission")
    permission_level: str = Field(..., description="Permission level granted")
    granted_by: UUID = Field(..., description="ID of user who granted permission")
    granted_at: datetime = Field(..., description="When permission was granted")
    expires_at: Optional[datetime] = Field(None, description="When permission expires")

    # Populated user info
    user_email: Optional[str] = Field(None, description="Email of user with permission")
    user_name: Optional[str] = Field(None, description="Name of user with permission")
    granter_email: Optional[str] = Field(None, description="Email of user who granted permission")
    granter_name: Optional[str] = Field(None, description="Name of user who granted permission")

    class Config:
        from_attributes = True


class ResourcePermissionListResponse(BaseModel):
    """Response schema for listing resource permissions."""

    permissions: List[ResourcePermissionResponse]
    total: int
    resource_type: str
    resource_id: UUID


# =============================================================================
# Share Link Request/Response Schemas
# =============================================================================


class CreateShareLinkRequest(BaseModel):
    """Request to create a shareable link."""

    resource_type: ResourceType = Field(..., description="Type of resource to share")
    resource_id: UUID = Field(..., description="ID of the resource to share")
    permission_level: PermissionLevel = Field(
        default=PermissionLevel.VIEW,
        description="Permission level: view, comment, edit",
    )
    expires_at: Optional[datetime] = Field(None, description="When the link expires (null = never)")
    max_uses: Optional[int] = Field(None, ge=1, description="Maximum number of uses (null = unlimited)")
    password: Optional[str] = Field(None, min_length=4, max_length=100, description="Optional password protection")
    name: Optional[str] = Field(None, max_length=255, description="Optional name for the share link")


class ShareLinkResponse(BaseModel):
    """Response schema for a share link."""

    id: UUID = Field(..., description="Unique identifier for the share link")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    token: str = Field(..., description="Unique token for the share link")
    permission_level: str = Field(..., description="Permission level granted")
    created_by: UUID = Field(..., description="ID of user who created the link")
    created_at: datetime = Field(..., description="When the link was created")
    expires_at: Optional[datetime] = Field(None, description="When the link expires")
    max_uses: Optional[int] = Field(None, description="Maximum number of uses")
    use_count: int = Field(..., description="Number of times the link has been used")
    is_active: bool = Field(..., description="Whether the link is active")
    is_password_protected: bool = Field(..., description="Whether the link has a password")
    name: Optional[str] = Field(None, description="Name of the share link")

    # Computed URL
    share_url: Optional[str] = Field(None, description="Full URL to access the shared resource")

    # Creator info
    creator_email: Optional[str] = Field(None, description="Email of link creator")
    creator_name: Optional[str] = Field(None, description="Name of link creator")

    class Config:
        from_attributes = True


class ShareLinkListResponse(BaseModel):
    """Response schema for listing share links."""

    links: List[ShareLinkResponse]
    total: int


class AccessShareLinkRequest(BaseModel):
    """Request to access a resource via share link."""

    password: Optional[str] = Field(None, description="Password if the link is protected")


class AccessShareLinkResponse(BaseModel):
    """Response when accessing via share link."""

    success: bool = Field(..., description="Whether access was granted")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    permission_level: str = Field(..., description="Permission level granted")
    resource_data: Optional[dict[str, Any]] = Field(None, description="Resource data if access granted")
    message: Optional[str] = Field(None, description="Additional message")


# =============================================================================
# Shared With Me Schemas
# =============================================================================


class SharedResourceInfo(BaseModel):
    """Information about a resource shared with the user."""

    permission_id: UUID = Field(..., description="ID of the permission")
    resource_type: str = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    permission_level: str = Field(..., description="Permission level")
    granted_at: datetime = Field(..., description="When access was granted")
    expires_at: Optional[datetime] = Field(None, description="When access expires")

    # Resource details
    resource_title: Optional[str] = Field(None, description="Title of the resource")
    resource_description: Optional[str] = Field(None, description="Description of the resource")

    # Granter info
    granted_by: UUID = Field(..., description="ID of user who shared")
    granter_email: Optional[str] = Field(None, description="Email of user who shared")
    granter_name: Optional[str] = Field(None, description="Name of user who shared")

    class Config:
        from_attributes = True


class SharedWithMeResponse(BaseModel):
    """Response schema for resources shared with the user."""

    resources: List[SharedResourceInfo]
    total: int
    grants_count: int = Field(0, description="Number of shared grants")
    applications_count: int = Field(0, description="Number of shared applications")
    documents_count: int = Field(0, description="Number of shared documents")


# =============================================================================
# Permission Check Schemas
# =============================================================================


class CheckPermissionRequest(BaseModel):
    """Request to check if user has permission on a resource."""

    resource_type: ResourceType = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="ID of the resource")
    required_level: PermissionLevel = Field(
        default=PermissionLevel.VIEW,
        description="Required permission level",
    )


class CheckPermissionResponse(BaseModel):
    """Response for permission check."""

    has_permission: bool = Field(..., description="Whether user has required permission")
    actual_level: Optional[str] = Field(None, description="User's actual permission level")
    source: Optional[str] = Field(None, description="Source of permission: 'owner', 'direct', 'team', 'link'")


# =============================================================================
# Update/Revoke Schemas
# =============================================================================


class UpdatePermissionRequest(BaseModel):
    """Request to update a resource permission."""

    permission_level: Optional[PermissionLevel] = Field(None, description="New permission level")
    expires_at: Optional[datetime] = Field(None, description="New expiration date")


class UpdateShareLinkRequest(BaseModel):
    """Request to update a share link."""

    permission_level: Optional[PermissionLevel] = Field(None, description="New permission level")
    expires_at: Optional[datetime] = Field(None, description="New expiration date")
    max_uses: Optional[int] = Field(None, ge=1, description="New maximum uses")
    is_active: Optional[bool] = Field(None, description="Whether the link is active")
    name: Optional[str] = Field(None, max_length=255, description="New name for the share link")


class RevokePermissionResponse(BaseModel):
    """Response after revoking a permission."""

    success: bool = Field(..., description="Whether revocation was successful")
    message: str = Field(..., description="Status message")


# =============================================================================
# Batch Operations
# =============================================================================


class BatchShareRequest(BaseModel):
    """Request to share a resource with multiple users."""

    users: List[ShareResourceRequest] = Field(
        ..., min_length=1, max_length=50, description="List of users to share with"
    )


class BatchShareResultItem(BaseModel):
    """Result for a single batch share item."""

    user_id: Optional[UUID] = Field(None, description="User ID if provided")
    email: Optional[str] = Field(None, description="Email if provided")
    success: bool = Field(..., description="Whether sharing was successful")
    message: str = Field(..., description="Status message")
    permission: Optional[ResourcePermissionResponse] = Field(None, description="Created permission if successful")


class BatchShareResponse(BaseModel):
    """Response for batch share operation."""

    total_requested: int = Field(..., description="Total shares requested")
    successful: int = Field(..., description="Number of successful shares")
    failed: int = Field(..., description="Number of failed shares")
    results: List[BatchShareResultItem] = Field(..., description="Individual results")
