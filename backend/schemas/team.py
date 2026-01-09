"""Team collaboration schemas for member management and activity tracking."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class InvitationStatus(str, Enum):
    """Status of a team invitation."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class MemberRole(str, Enum):
    """Role of a team member in the lab."""

    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class ActivityType(str, Enum):
    """Types of team activities for logging."""

    INVITATION_SENT = "invitation_sent"
    INVITATION_RESENT = "invitation_resent"
    INVITATION_ACCEPTED = "invitation_accepted"
    INVITATION_DECLINED = "invitation_declined"
    INVITATION_EXPIRED = "invitation_expired"
    INVITATION_CANCELLED = "invitation_cancelled"
    MEMBER_REMOVED = "member_removed"
    ROLE_CHANGED = "role_changed"
    PERMISSIONS_UPDATED = "permissions_updated"


class EntityType(str, Enum):
    """Types of entities involved in team activities."""

    MEMBER = "member"
    INVITATION = "invitation"
    PERMISSION = "permission"


# ============================================================================
# Permission Schemas
# ============================================================================


class MemberPermissions(BaseModel):
    """Role-based permissions for team members."""

    can_view: bool = Field(default=True, description="Can view applications and data")
    can_edit: bool = Field(default=False, description="Can edit applications and notes")
    can_create: bool = Field(
        default=False, description="Can create new applications and deadlines"
    )
    can_delete: bool = Field(default=False, description="Can delete applications")
    can_invite: bool = Field(default=False, description="Can invite other team members")

    class Config:
        from_attributes = True


# ============================================================================
# Invitation Schemas
# ============================================================================


class TeamInviteRequest(BaseModel):
    """Request to invite a new team member."""

    email: EmailStr = Field(..., description="Email address of the person to invite")
    role: MemberRole = Field(
        default=MemberRole.MEMBER, description="Role to assign to the new member"
    )
    message: Optional[str] = Field(
        None, max_length=1000, description="Optional personal message for the invitation"
    )


class InvitationAcceptRequest(BaseModel):
    """Request to accept an invitation."""

    token: str = Field(..., min_length=32, max_length=64, description="Invitation token")


class InvitationDeclineRequest(BaseModel):
    """Request to decline an invitation."""

    token: str = Field(..., min_length=32, max_length=64, description="Invitation token")
    reason: Optional[str] = Field(
        None, max_length=500, description="Optional reason for declining"
    )


# ============================================================================
# Member Schemas
# ============================================================================


class TeamMemberBase(BaseModel):
    """Base schema for team member data."""

    member_email: str = Field(..., description="Email address of the team member")
    role: str = Field(..., description="Role of the team member")
    permissions: Optional[MemberPermissions] = Field(
        None, description="Member's permissions"
    )


class TeamMemberResponse(BaseModel):
    """Response schema for team member data."""

    id: UUID = Field(..., description="Unique identifier for the lab member record")
    lab_owner_id: UUID = Field(..., description="ID of the lab owner/PI")
    member_email: str = Field(..., description="Email address of the team member")
    member_user_id: Optional[UUID] = Field(
        None, description="User ID if member has registered"
    )
    role: str = Field(..., description="Role of the team member (admin, member, viewer)")
    invited_at: datetime = Field(..., description="When the invitation was sent")
    accepted_at: Optional[datetime] = Field(
        None, description="When the invitation was accepted"
    )
    invitation_status: str = Field(..., description="Current status of the invitation")
    invitation_expires_at: Optional[datetime] = Field(
        None, description="When the invitation expires"
    )
    declined_at: Optional[datetime] = Field(
        None, description="When the invitation was declined"
    )
    permissions: Optional[MemberPermissions] = Field(
        None, description="Member's role-based permissions"
    )
    member_name: Optional[str] = Field(
        None, description="Name of the member if registered"
    )

    class Config:
        from_attributes = True


class TeamMemberUpdate(BaseModel):
    """Request to update a team member's role and permissions."""

    role: Optional[MemberRole] = Field(None, description="New role for the member")
    permissions: Optional[MemberPermissions] = Field(
        None, description="Updated permissions"
    )


# ============================================================================
# Activity Schemas
# ============================================================================


class TeamActivityResponse(BaseModel):
    """Response schema for team activity log entries."""

    id: UUID = Field(..., description="Unique identifier for the activity")
    lab_owner_id: UUID = Field(..., description="ID of the lab owner")
    actor_id: Optional[UUID] = Field(
        None, description="ID of the user who performed the action"
    )
    action_type: str = Field(..., description="Type of action performed")
    entity_type: str = Field(..., description="Type of entity affected")
    entity_id: Optional[UUID] = Field(None, description="ID of the affected entity")
    entity_name: Optional[str] = Field(
        None, description="Name or description of the affected entity"
    )
    metadata: Optional[dict[str, Any]] = Field(
        None, description="Additional metadata about the activity"
    )
    created_at: datetime = Field(..., description="When the activity occurred")
    actor_name: Optional[str] = Field(
        None, description="Name of the user who performed the action"
    )
    actor_email: Optional[str] = Field(
        None, description="Email of the user who performed the action"
    )

    class Config:
        from_attributes = True


class TeamActivityFilters(BaseModel):
    """Filters for querying team activities."""

    action_types: Optional[List[ActivityType]] = Field(
        None, description="Filter by action types"
    )
    entity_types: Optional[List[EntityType]] = Field(
        None, description="Filter by entity types"
    )
    actor_id: Optional[UUID] = Field(None, description="Filter by actor")
    entity_id: Optional[UUID] = Field(None, description="Filter by entity")
    from_date: Optional[datetime] = Field(
        None, description="Activities from this date onwards"
    )
    to_date: Optional[datetime] = Field(
        None, description="Activities until this date"
    )
    limit: int = Field(default=50, ge=1, le=200, description="Maximum results")
    offset: int = Field(default=0, ge=0, description="Skip first N results")


# ============================================================================
# Stats Schemas
# ============================================================================


class TeamStatsResponse(BaseModel):
    """Response schema for team statistics."""

    total_members: int = Field(..., description="Total number of team members")
    active_members: int = Field(
        ..., description="Number of members who accepted invitations"
    )
    pending_invitations: int = Field(
        ..., description="Number of pending invitations"
    )
    declined_invitations: int = Field(
        ..., description="Number of declined invitations"
    )
    expired_invitations: int = Field(
        ..., description="Number of expired invitations"
    )
    members_by_role: dict[str, int] = Field(
        ..., description="Count of members per role"
    )
    recent_activity_count: int = Field(
        ..., description="Number of activities in the last 7 days"
    )


# ============================================================================
# List Response Schemas
# ============================================================================


class TeamMembersListResponse(BaseModel):
    """Response schema for listing team members."""

    members: List[TeamMemberResponse]
    total: int
    pending_count: int
    active_count: int


class TeamActivitiesListResponse(BaseModel):
    """Response schema for listing team activities."""

    activities: List[TeamActivityResponse]
    total: int
    has_more: bool


class InvitationResponse(BaseModel):
    """Response after sending or processing an invitation."""

    success: bool
    message: str
    member: Optional[TeamMemberResponse] = None


# ============================================================================
# Permission Template Schemas
# ============================================================================


class PermissionTemplatePermissions(BaseModel):
    """Permissions configuration for a template."""

    can_view: bool = Field(default=True, description="Can view applications and data")
    can_edit: bool = Field(default=False, description="Can edit applications and notes")
    can_create: bool = Field(
        default=False, description="Can create new applications and deadlines"
    )
    can_delete: bool = Field(default=False, description="Can delete applications")
    can_invite: bool = Field(default=False, description="Can invite other team members")
    can_manage_grants: bool = Field(
        default=False, description="Can manage grant submissions and tracking"
    )
    can_export: bool = Field(default=False, description="Can export data and reports")

    class Config:
        from_attributes = True


class PermissionTemplateCreate(BaseModel):
    """Request to create a new permission template."""

    name: str = Field(
        ..., min_length=1, max_length=100, description="Template name for identification"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Description of when to use this template"
    )
    permissions: PermissionTemplatePermissions = Field(
        ..., description="Permission configuration for this template"
    )
    is_default: bool = Field(
        default=False, description="Set as default template for new invitations"
    )


class PermissionTemplateUpdate(BaseModel):
    """Request to update a permission template."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=100, description="Updated template name"
    )
    description: Optional[str] = Field(
        None, max_length=500, description="Updated description"
    )
    permissions: Optional[PermissionTemplatePermissions] = Field(
        None, description="Updated permissions"
    )
    is_default: Optional[bool] = Field(
        None, description="Set as default template"
    )


class PermissionTemplateResponse(BaseModel):
    """Response schema for permission template data."""

    id: UUID = Field(..., description="Unique identifier for the template")
    owner_id: UUID = Field(..., description="ID of the template owner")
    name: str = Field(..., description="Template name")
    description: Optional[str] = Field(None, description="Template description")
    permissions: PermissionTemplatePermissions = Field(
        ..., description="Permission configuration"
    )
    is_default: bool = Field(..., description="Whether this is the default template")
    created_at: datetime = Field(..., description="Template creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    member_count: Optional[int] = Field(
        None, description="Number of members using this template"
    )

    class Config:
        from_attributes = True


class PermissionTemplatesListResponse(BaseModel):
    """Response schema for listing permission templates."""

    templates: List[PermissionTemplateResponse]
    total: int


# ============================================================================
# Notification Schemas
# ============================================================================


class NotificationType(str, Enum):
    """Types of notifications."""

    TEAM_INVITE = "team_invite"
    ROLE_CHANGED = "role_changed"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    PERMISSIONS_UPDATED = "permissions_updated"
    DEADLINE_REMINDER = "deadline_reminder"
    GRANT_MATCH = "grant_match"
    APPLICATION_UPDATE = "application_update"
    SYSTEM = "system"


class NotificationResponse(BaseModel):
    """Response schema for notification data."""

    id: UUID = Field(..., description="Unique identifier for the notification")
    user_id: UUID = Field(..., description="ID of the notification recipient")
    type: str = Field(..., description="Notification type")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message content")
    metadata: Optional[dict[str, Any]] = Field(
        None, description="Additional context data"
    )
    read: bool = Field(..., description="Whether the notification has been read")
    read_at: Optional[datetime] = Field(
        None, description="When the notification was read"
    )
    action_url: Optional[str] = Field(
        None, description="URL to navigate to on click"
    )
    created_at: datetime = Field(..., description="Notification creation timestamp")

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Response schema for listing notifications."""

    notifications: List[NotificationResponse]
    total: int
    unread_count: int
    has_more: bool


class NotificationMarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: Optional[List[UUID]] = Field(
        None, description="Specific notification IDs to mark as read (if None, marks all)"
    )


# ============================================================================
# Bulk Invite Schemas
# ============================================================================


class BulkInviteItem(BaseModel):
    """Single item in a bulk invite request."""

    email: EmailStr = Field(..., description="Email address to invite")
    role: MemberRole = Field(
        default=MemberRole.MEMBER, description="Role to assign"
    )
    permission_template_id: Optional[UUID] = Field(
        None, description="Permission template to apply"
    )


class BulkInviteRequest(BaseModel):
    """Request to send multiple team invitations at once."""

    invites: List[BulkInviteItem] = Field(
        ..., min_length=1, max_length=50, description="List of invitations to send"
    )
    message: Optional[str] = Field(
        None, max_length=1000, description="Personal message to include in all invitations"
    )


class BulkInviteResultItem(BaseModel):
    """Result for a single bulk invite item."""

    email: str = Field(..., description="Email address that was invited")
    success: bool = Field(..., description="Whether the invitation was sent successfully")
    message: str = Field(..., description="Status message")
    member: Optional[TeamMemberResponse] = Field(
        None, description="Created member record if successful"
    )


class BulkInviteResponse(BaseModel):
    """Response for bulk invite operation."""

    total_requested: int = Field(..., description="Total invitations requested")
    successful: int = Field(..., description="Number of successful invitations")
    failed: int = Field(..., description="Number of failed invitations")
    results: List[BulkInviteResultItem] = Field(
        ..., description="Individual results for each invitation"
    )
