"""Permission template schemas for API request/response validation."""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Permission Schemas
# ============================================================================


class TemplatePermissions(BaseModel):
    """Permission settings for a template."""

    can_view: bool = Field(default=True, description="Can view applications and data")
    can_edit: bool = Field(default=False, description="Can edit applications and notes")
    can_create: bool = Field(default=False, description="Can create new applications and deadlines")
    can_delete: bool = Field(default=False, description="Can delete applications")
    can_invite: bool = Field(default=False, description="Can invite other team members")
    can_manage_grants: bool = Field(default=False, description="Can manage grant pipeline")
    can_export: bool = Field(default=False, description="Can export data")

    class Config:
        from_attributes = True


# ============================================================================
# Request Schemas
# ============================================================================


class PermissionTemplateCreate(BaseModel):
    """Request schema for creating a permission template."""

    name: str = Field(..., min_length=1, max_length=100, description="Template name for display")
    description: Optional[str] = Field(None, max_length=500, description="Description of when to use this template")
    permissions: TemplatePermissions = Field(..., description="Permission settings for this template")
    is_default: bool = Field(
        default=False,
        description="Whether this is the default template for new invitations",
    )


class PermissionTemplateUpdate(BaseModel):
    """Request schema for updating a permission template."""

    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Template name for display")
    description: Optional[str] = Field(None, max_length=500, description="Description of when to use this template")
    permissions: Optional[TemplatePermissions] = Field(None, description="Permission settings for this template")
    is_default: Optional[bool] = Field(None, description="Whether this is the default template for new invitations")


# ============================================================================
# Response Schemas
# ============================================================================


class PermissionTemplateResponse(BaseModel):
    """Response schema for a permission template."""

    id: UUID = Field(..., description="Unique identifier for the template")
    owner_id: UUID = Field(..., description="User who created/owns this template")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    permissions: TemplatePermissions = Field(..., description="Permission settings for this template")
    is_default: bool = Field(..., description="Whether this is the default template for new invitations")
    created_at: datetime = Field(..., description="Template creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class PermissionTemplateListResponse(BaseModel):
    """Response schema for listing permission templates."""

    templates: List[PermissionTemplateResponse] = Field(..., description="List of permission templates")
    total: int = Field(..., description="Total number of templates")


class DefaultTemplatesResponse(BaseModel):
    """Response schema for default built-in templates."""

    templates: List[PermissionTemplateResponse] = Field(..., description="List of default templates")


class ApplyTemplateResponse(BaseModel):
    """Response schema for applying a template to a member."""

    success: bool = Field(..., description="Whether the operation succeeded")
    message: str = Field(..., description="Status message")
    member_id: UUID = Field(..., description="ID of the member updated")
    template_id: UUID = Field(..., description="ID of the template applied")
    permissions: TemplatePermissions = Field(..., description="Permissions applied to the member")
