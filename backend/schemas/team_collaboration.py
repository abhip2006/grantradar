"""Team collaboration schemas for grant assignments, comments, and coordination."""
from datetime import datetime
from enum import Enum
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


# ============================================================================
# Enums
# ============================================================================


class AssignmentRole(str, Enum):
    """Role of a team member in a grant assignment."""

    LEAD = "lead"
    CONTRIBUTOR = "contributor"
    REVIEWER = "reviewer"


class AssignmentStatus(str, Enum):
    """Status of a grant assignment."""

    ACTIVE = "active"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class TeamCollaborationNotificationType(str, Enum):
    """Types of team collaboration notifications."""

    ASSIGNMENT_CREATED = "assignment_created"
    ASSIGNMENT_UPDATED = "assignment_updated"
    ASSIGNMENT_COMPLETED = "assignment_completed"
    ASSIGNMENT_REASSIGNED = "assignment_reassigned"
    COMMENT_ADDED = "comment_added"
    COMMENT_REPLY = "comment_reply"
    MENTION = "mention"
    DEADLINE_APPROACHING = "deadline_approaching"
    DEADLINE_CONFLICT = "deadline_conflict"
    WORKLOAD_WARNING = "workload_warning"


# ============================================================================
# Assignment Schemas
# ============================================================================


class AssignmentCreate(BaseModel):
    """Request to create a grant assignment."""

    grant_id: UUID = Field(..., description="ID of the grant to assign")
    match_id: Optional[UUID] = Field(
        None, description="Optional match ID if assigning from a match"
    )
    assigned_to: UUID = Field(..., description="User ID to assign the grant to")
    role: AssignmentRole = Field(
        default=AssignmentRole.CONTRIBUTOR,
        description="Role of the assignee (lead, contributor, reviewer)",
    )
    due_date: Optional[datetime] = Field(
        None, description="Due date for the assignment"
    )
    notes: Optional[str] = Field(
        None, max_length=2000, description="Notes about the assignment"
    )


class AssignmentUpdate(BaseModel):
    """Request to update a grant assignment."""

    role: Optional[AssignmentRole] = Field(
        None, description="Updated role for the assignee"
    )
    status: Optional[AssignmentStatus] = Field(
        None, description="Updated status of the assignment"
    )
    due_date: Optional[datetime] = Field(
        None, description="Updated due date"
    )
    notes: Optional[str] = Field(
        None, max_length=2000, description="Updated notes"
    )


class AssigneeInfo(BaseModel):
    """Information about an assignee."""

    id: UUID = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="User's name")
    email: str = Field(..., description="User's email")

    class Config:
        from_attributes = True


class GrantInfo(BaseModel):
    """Basic grant information for assignment responses."""

    id: UUID = Field(..., description="Grant ID")
    title: str = Field(..., description="Grant title")
    agency: Optional[str] = Field(None, description="Funding agency")
    deadline: Optional[datetime] = Field(None, description="Grant deadline")

    class Config:
        from_attributes = True


class AssignmentResponse(BaseModel):
    """Response schema for a grant assignment."""

    id: UUID = Field(..., description="Assignment ID")
    match_id: Optional[UUID] = Field(None, description="Match ID if applicable")
    grant_id: UUID = Field(..., description="Grant ID")
    assigned_to: UUID = Field(..., description="Assigned user ID")
    assigned_by: Optional[UUID] = Field(None, description="User who made the assignment")
    lab_owner_id: UUID = Field(..., description="Lab owner ID")
    role: str = Field(..., description="Assignment role")
    status: str = Field(..., description="Assignment status")
    due_date: Optional[datetime] = Field(None, description="Due date")
    notes: Optional[str] = Field(None, description="Assignment notes")
    created_at: datetime = Field(..., description="When the assignment was created")
    updated_at: datetime = Field(..., description="When the assignment was last updated")
    assignee: Optional[AssigneeInfo] = Field(None, description="Assignee information")
    assigner: Optional[AssigneeInfo] = Field(None, description="Assigner information")
    grant: Optional[GrantInfo] = Field(None, description="Grant information")

    class Config:
        from_attributes = True


class AssignmentListResponse(BaseModel):
    """Response for listing assignments."""

    assignments: List[AssignmentResponse]
    total: int
    has_more: bool


# ============================================================================
# Comment Schemas
# ============================================================================


class MentionInfo(BaseModel):
    """Information about a mentioned user."""

    user_id: UUID = Field(..., description="ID of the mentioned user")
    name: Optional[str] = Field(None, description="Name of the mentioned user")
    email: Optional[str] = Field(None, description="Email of the mentioned user")
    position: int = Field(..., description="Position in the comment text where mention starts")


class CommentCreate(BaseModel):
    """Request to create a comment on a grant."""

    comment_text: str = Field(
        ..., min_length=1, max_length=5000, description="Comment content"
    )
    parent_id: Optional[UUID] = Field(
        None, description="Parent comment ID for replies"
    )
    mentions: Optional[List[MentionInfo]] = Field(
        None, description="List of mentioned users"
    )


class CommentUpdate(BaseModel):
    """Request to update a comment."""

    comment_text: str = Field(
        ..., min_length=1, max_length=5000, description="Updated comment content"
    )
    mentions: Optional[List[MentionInfo]] = Field(
        None, description="Updated list of mentioned users"
    )


class CommentAuthorInfo(BaseModel):
    """Information about a comment author."""

    id: UUID = Field(..., description="User ID")
    name: Optional[str] = Field(None, description="User's name")
    email: str = Field(..., description="User's email")

    class Config:
        from_attributes = True


class CommentResponse(BaseModel):
    """Response schema for a comment."""

    id: UUID = Field(..., description="Comment ID")
    match_id: Optional[UUID] = Field(None, description="Match ID if applicable")
    grant_id: UUID = Field(..., description="Grant ID")
    user_id: UUID = Field(..., description="Author user ID")
    lab_owner_id: UUID = Field(..., description="Lab owner ID")
    comment_text: str = Field(..., description="Comment content")
    parent_id: Optional[UUID] = Field(None, description="Parent comment ID")
    mentions: Optional[List[MentionInfo]] = Field(None, description="Mentioned users")
    is_edited: bool = Field(..., description="Whether the comment was edited")
    created_at: datetime = Field(..., description="When the comment was created")
    updated_at: datetime = Field(..., description="When the comment was last updated")
    author: Optional[CommentAuthorInfo] = Field(None, description="Author information")
    reply_count: int = Field(default=0, description="Number of replies")
    replies: Optional[List["CommentResponse"]] = Field(
        None, description="Nested replies (if requested)"
    )

    class Config:
        from_attributes = True


# Enable forward reference for nested replies
CommentResponse.model_rebuild()


class CommentListResponse(BaseModel):
    """Response for listing comments."""

    comments: List[CommentResponse]
    total: int
    has_more: bool


# ============================================================================
# Workload Schemas
# ============================================================================


class WorkloadAssignment(BaseModel):
    """Assignment summary for workload display."""

    id: UUID = Field(..., description="Assignment ID")
    grant_id: UUID = Field(..., description="Grant ID")
    grant_title: str = Field(..., description="Grant title")
    role: str = Field(..., description="Assignment role")
    status: str = Field(..., description="Assignment status")
    due_date: Optional[datetime] = Field(None, description="Due date")
    days_until_due: Optional[int] = Field(
        None, description="Days until due date (negative if overdue)"
    )


class WorkloadSummary(BaseModel):
    """Summary of a team member's workload."""

    user_id: UUID = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User's name")
    user_email: str = Field(..., description="User's email")
    total_assignments: int = Field(..., description="Total number of assignments")
    active_assignments: int = Field(..., description="Number of active assignments")
    completed_assignments: int = Field(..., description="Number of completed assignments")
    lead_count: int = Field(..., description="Number of assignments where user is lead")
    contributor_count: int = Field(..., description="Number of contributor assignments")
    reviewer_count: int = Field(..., description="Number of reviewer assignments")
    overdue_count: int = Field(..., description="Number of overdue assignments")
    due_this_week: int = Field(..., description="Assignments due this week")
    assignments: List[WorkloadAssignment] = Field(
        default_factory=list, description="List of active assignments"
    )


class TeamWorkloadResponse(BaseModel):
    """Team workload overview."""

    lab_owner_id: UUID = Field(..., description="Lab owner ID")
    total_team_members: int = Field(..., description="Total team members")
    total_assignments: int = Field(..., description="Total assignments across team")
    active_assignments: int = Field(..., description="Active assignments")
    members: List[WorkloadSummary] = Field(..., description="Workload per team member")


# ============================================================================
# Activity Feed Schemas
# ============================================================================


class ActivityItem(BaseModel):
    """A single item in the team activity feed."""

    id: UUID = Field(..., description="Activity ID")
    activity_type: str = Field(..., description="Type of activity")
    actor_id: Optional[UUID] = Field(None, description="User who performed the action")
    actor_name: Optional[str] = Field(None, description="Actor's name")
    actor_email: Optional[str] = Field(None, description="Actor's email")
    entity_type: str = Field(..., description="Type of entity (assignment, comment, etc.)")
    entity_id: UUID = Field(..., description="Entity ID")
    entity_name: Optional[str] = Field(None, description="Entity description")
    grant_id: Optional[UUID] = Field(None, description="Related grant ID")
    grant_title: Optional[str] = Field(None, description="Related grant title")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional details")
    created_at: datetime = Field(..., description="When the activity occurred")


class ActivityFeedResponse(BaseModel):
    """Response for team activity feed."""

    activities: List[ActivityItem]
    total: int
    has_more: bool


# ============================================================================
# Deadline Conflict Schemas
# ============================================================================


class DeadlineAssignment(BaseModel):
    """Assignment with deadline for conflict checking."""

    id: UUID = Field(..., description="Assignment ID")
    grant_id: UUID = Field(..., description="Grant ID")
    grant_title: str = Field(..., description="Grant title")
    due_date: datetime = Field(..., description="Assignment due date")
    role: str = Field(..., description="Assignment role")
    assigned_to: UUID = Field(..., description="Assignee user ID")
    assignee_name: Optional[str] = Field(None, description="Assignee name")


class DeadlineConflict(BaseModel):
    """A deadline conflict between assignments."""

    user_id: UUID = Field(..., description="User with the conflict")
    user_name: Optional[str] = Field(None, description="User's name")
    user_email: str = Field(..., description="User's email")
    conflict_date: datetime = Field(
        ..., description="Date when conflicts occur (within range)"
    )
    conflicting_assignments: List[DeadlineAssignment] = Field(
        ..., description="Assignments with overlapping deadlines"
    )
    severity: str = Field(
        ..., description="Severity level (low, medium, high, critical)"
    )


class DeadlineConflictsResponse(BaseModel):
    """Response for deadline conflicts check."""

    conflicts: List[DeadlineConflict]
    total_conflicts: int
    users_with_conflicts: int
    conflict_window_days: int = Field(
        default=7, description="Days window used for conflict detection"
    )


# ============================================================================
# Team Notification Schemas
# ============================================================================


class TeamNotificationResponse(BaseModel):
    """Response schema for a team notification."""

    id: UUID = Field(..., description="Notification ID")
    user_id: UUID = Field(..., description="User ID")
    team_id: UUID = Field(..., description="Team/Lab owner ID")
    notification_type: str = Field(..., description="Type of notification")
    message: str = Field(..., description="Notification message")
    entity_type: Optional[str] = Field(None, description="Related entity type")
    entity_id: Optional[UUID] = Field(None, description="Related entity ID")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional metadata")
    is_read: bool = Field(..., description="Whether notification is read")
    read_at: Optional[datetime] = Field(None, description="When notification was read")
    created_at: datetime = Field(..., description="When notification was created")

    class Config:
        from_attributes = True


class TeamNotificationListResponse(BaseModel):
    """Response for listing team notifications."""

    notifications: List[TeamNotificationResponse]
    total: int
    unread_count: int
    has_more: bool


class MarkNotificationsReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: Optional[List[UUID]] = Field(
        None, description="Specific notification IDs to mark as read (if None, marks all)"
    )
