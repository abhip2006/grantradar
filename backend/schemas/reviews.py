"""
Review workflow schemas for request/response models.
Provides Pydantic models for internal review workflow API endpoints.
"""
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, computed_field, field_validator, model_validator

from backend.schemas.common import PaginatedResponse, PaginationInfo
from backend.schemas.jsonb_types import (
    WorkflowStageDict,
    TeamMemberPermissionsDict,
    ReviewActionMetadataDict,
)


class ReviewStatus(str, Enum):
    """Status values for application reviews."""
    PENDING = "pending"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"


class ReviewAction(str, Enum):
    """Actions that can be taken during a review."""
    APPROVED = "approved"
    REJECTED = "rejected"
    RETURNED = "returned"
    COMMENTED = "commented"


class TeamMemberRole(str, Enum):
    """Roles for application team members."""
    PI = "pi"
    CO_I = "co_i"
    GRANT_WRITER = "grant_writer"
    REVIEWER = "reviewer"
    ADMIN = "admin"


# Status display configuration for UI
REVIEW_STATUS_CONFIG = {
    ReviewStatus.PENDING: {"label": "Pending", "color": "gray", "order": 0},
    ReviewStatus.IN_REVIEW: {"label": "In Review", "color": "blue", "order": 1},
    ReviewStatus.APPROVED: {"label": "Approved", "color": "green", "order": 2},
    ReviewStatus.REJECTED: {"label": "Rejected", "color": "red", "order": 3},
    ReviewStatus.ESCALATED: {"label": "Escalated", "color": "orange", "order": 4},
}

# Role display configuration for UI
ROLE_CONFIG = {
    TeamMemberRole.PI: {"label": "Principal Investigator", "short": "PI"},
    TeamMemberRole.CO_I: {"label": "Co-Investigator", "short": "Co-I"},
    TeamMemberRole.GRANT_WRITER: {"label": "Grant Writer", "short": "Writer"},
    TeamMemberRole.REVIEWER: {"label": "Reviewer", "short": "Rev"},
    TeamMemberRole.ADMIN: {"label": "Administrator", "short": "Admin"},
}


# ============================================================================
# Workflow Stage Schemas
# ============================================================================

class WorkflowStage(BaseModel):
    """Schema for a workflow stage configuration."""
    order: int = Field(..., ge=0, description="Stage order (0-indexed)")
    name: str = Field(..., min_length=1, max_length=100, description="Stage name")
    required_role: Optional[TeamMemberRole] = Field(None, description="Required role to approve this stage")
    sla_hours: Optional[int] = Field(None, ge=1, description="SLA time limit in hours")
    auto_escalate: bool = Field(False, description="Whether to auto-escalate when SLA is exceeded")
    description: Optional[str] = Field(None, max_length=500, description="Stage description")


class WorkflowStageResponse(WorkflowStage):
    """Response schema for workflow stage with computed fields."""

    @computed_field
    @property
    def role_config(self) -> Optional[dict]:
        """Get role display configuration."""
        if self.required_role:
            return ROLE_CONFIG.get(self.required_role, {"label": self.required_role.value, "short": self.required_role.value})
        return None


# ============================================================================
# Review Workflow Schemas
# ============================================================================

class ReviewWorkflowCreate(BaseModel):
    """Schema for creating a new review workflow."""
    name: str = Field(..., min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=2000, description="Workflow description")
    stages: List[WorkflowStage] = Field(..., min_length=1, description="Workflow stages")
    is_default: bool = Field(False, description="Set as default workflow")

    @field_validator("stages")
    @classmethod
    def validate_stages_structure(cls, v: List[WorkflowStage]) -> List[WorkflowStage]:
        """Validate that stages conform to WorkflowStageDict structure and are properly ordered."""
        if not v:
            raise ValueError("At least one stage is required")

        # Validate stage orders are sequential starting from 0
        orders = sorted(stage.order for stage in v)
        expected = list(range(len(v)))
        if orders != expected:
            raise ValueError(f"Stage orders must be sequential starting from 0. Got: {orders}")

        # Validate stage names are unique
        names = [stage.name for stage in v]
        if len(names) != len(set(names)):
            raise ValueError("Stage names must be unique")

        return v


class ReviewWorkflowUpdate(BaseModel):
    """Schema for updating a review workflow."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Workflow name")
    description: Optional[str] = Field(None, max_length=2000, description="Workflow description")
    stages: Optional[List[WorkflowStage]] = Field(None, min_length=1, description="Workflow stages")
    is_default: Optional[bool] = Field(None, description="Set as default workflow")
    is_active: Optional[bool] = Field(None, description="Whether workflow is active")

    @field_validator("stages")
    @classmethod
    def validate_stages_structure(cls, v: Optional[List[WorkflowStage]]) -> Optional[List[WorkflowStage]]:
        """Validate that stages conform to WorkflowStageDict structure if provided."""
        if v is None:
            return v

        if not v:
            raise ValueError("At least one stage is required when updating stages")

        # Validate stage orders are sequential starting from 0
        orders = sorted(stage.order for stage in v)
        expected = list(range(len(v)))
        if orders != expected:
            raise ValueError(f"Stage orders must be sequential starting from 0. Got: {orders}")

        # Validate stage names are unique
        names = [stage.name for stage in v]
        if len(names) != len(set(names)):
            raise ValueError("Stage names must be unique")

        return v


class ReviewWorkflowResponse(BaseModel):
    """Schema for review workflow response."""
    id: UUID = Field(..., description="Workflow ID")
    user_id: UUID = Field(..., description="Owner user ID")
    name: str = Field(..., description="Workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    stages: List[WorkflowStageResponse] = Field(..., description="Workflow stages")
    is_default: bool = Field(..., description="Whether this is the default workflow")
    is_active: bool = Field(..., description="Whether this workflow is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    @computed_field
    @property
    def stage_count(self) -> int:
        """Number of stages in the workflow."""
        return len(self.stages)

    class Config:
        from_attributes = True


class ReviewWorkflowList(BaseModel):
    """Schema for list of review workflows (standard paginated format)."""
    data: List[ReviewWorkflowResponse] = Field(..., description="List of workflows")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[ReviewWorkflowResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# ============================================================================
# Application Review Schemas
# ============================================================================

class StartReviewRequest(BaseModel):
    """Schema for starting a review process."""
    workflow_id: Optional[UUID] = Field(None, description="Workflow ID (uses default if not provided)")


class ReviewActionRequest(BaseModel):
    """Schema for submitting a review action."""
    action: ReviewAction = Field(..., description="Action to take")
    comments: Optional[str] = Field(None, max_length=5000, description="Comments/feedback")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional action metadata")


class ReviewStageActionResponse(BaseModel):
    """Schema for a review stage action response."""
    id: UUID = Field(..., description="Action ID")
    review_id: UUID = Field(..., description="Review ID")
    stage_order: int = Field(..., description="Stage index when action was taken")
    stage_name: str = Field(..., description="Stage name when action was taken")
    reviewer_id: Optional[UUID] = Field(None, description="Reviewer user ID")
    reviewer_name: Optional[str] = Field(None, description="Reviewer name")
    reviewer_email: Optional[str] = Field(None, description="Reviewer email")
    action: ReviewAction = Field(..., description="Action taken")
    comments: Optional[str] = Field(None, description="Comments/feedback")
    metadata: Optional[dict[str, Any]] = Field(None, description="Additional action metadata")
    acted_at: datetime = Field(..., description="When the action was taken")

    @computed_field
    @property
    def action_label(self) -> str:
        """Human-readable action label."""
        labels = {
            ReviewAction.APPROVED: "Approved",
            ReviewAction.REJECTED: "Rejected",
            ReviewAction.RETURNED: "Returned for Revision",
            ReviewAction.COMMENTED: "Added Comment",
        }
        return labels.get(self.action, self.action.value)

    class Config:
        from_attributes = True


class ApplicationReviewResponse(BaseModel):
    """Schema for application review response."""
    id: UUID = Field(..., description="Review ID")
    kanban_card_id: UUID = Field(..., description="Application ID")
    workflow_id: Optional[UUID] = Field(None, description="Workflow ID")
    workflow_name: Optional[str] = Field(None, description="Workflow name")
    current_stage: int = Field(..., description="Current stage index")
    current_stage_name: Optional[str] = Field(None, description="Current stage name")
    total_stages: int = Field(0, description="Total number of stages")
    status: ReviewStatus = Field(..., description="Review status")
    started_by: Optional[UUID] = Field(None, description="User who started the review")
    started_by_name: Optional[str] = Field(None, description="Name of user who started the review")
    started_at: datetime = Field(..., description="When the review was started")
    completed_at: Optional[datetime] = Field(None, description="When the review was completed")
    stage_started_at: datetime = Field(..., description="When the current stage started")
    escalation_sent: bool = Field(..., description="Whether escalation was sent for current stage")
    sla_hours: Optional[int] = Field(None, description="SLA hours for current stage")
    actions: List[ReviewStageActionResponse] = Field(default_factory=list, description="Review actions history")

    @computed_field
    @property
    def status_config(self) -> dict:
        """Get status display configuration."""
        return REVIEW_STATUS_CONFIG.get(self.status, {"label": self.status.value, "color": "gray", "order": 99})

    @computed_field
    @property
    def progress_percent(self) -> float:
        """Calculate review progress percentage."""
        if self.total_stages == 0:
            return 0.0
        if self.status in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
            return 100.0
        return round((self.current_stage / self.total_stages) * 100, 1)

    class Config:
        from_attributes = True


class ReviewHistoryResponse(BaseModel):
    """Schema for review history (all actions)."""
    review: ApplicationReviewResponse = Field(..., description="Review details")
    actions: List[ReviewStageActionResponse] = Field(..., description="All actions taken")


# ============================================================================
# Team Member Schemas
# ============================================================================

class TeamMemberPermissions(BaseModel):
    """Schema for team member permissions."""
    can_edit: bool = Field(True, description="Can edit application content")
    can_approve: bool = Field(False, description="Can approve review stages")
    can_submit: bool = Field(False, description="Can submit the application")
    sections: Optional[List[str]] = Field(None, description="Specific sections they can access")


class AddTeamMemberRequest(BaseModel):
    """Schema for adding a team member to an application."""
    user_id: Optional[UUID] = Field(None, description="User ID (if known)")
    email: Optional[str] = Field(None, description="User email (to invite)")
    role: TeamMemberRole = Field(..., description="Role in the application")
    permissions: Optional[TeamMemberPermissions] = Field(None, description="Custom permissions")


class UpdateTeamMemberRequest(BaseModel):
    """Schema for updating a team member."""
    role: Optional[TeamMemberRole] = Field(None, description="New role")
    permissions: Optional[TeamMemberPermissions] = Field(None, description="Updated permissions")


class TeamMemberResponse(BaseModel):
    """Schema for team member response."""
    id: UUID = Field(..., description="Team member record ID")
    kanban_card_id: UUID = Field(..., description="Application ID")
    user_id: UUID = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="User name")
    user_email: Optional[str] = Field(None, description="User email")
    role: TeamMemberRole = Field(..., description="Role in the application")
    permissions: Optional[TeamMemberPermissions] = Field(None, description="Custom permissions")
    added_by: Optional[UUID] = Field(None, description="User who added this member")
    added_at: datetime = Field(..., description="When the member was added")

    @computed_field
    @property
    def role_config(self) -> dict:
        """Get role display configuration."""
        return ROLE_CONFIG.get(self.role, {"label": self.role.value, "short": self.role.value})

    @computed_field
    @property
    def default_permissions(self) -> TeamMemberPermissions:
        """Get default permissions based on role."""
        defaults = {
            TeamMemberRole.PI: TeamMemberPermissions(can_edit=True, can_approve=True, can_submit=True),
            TeamMemberRole.CO_I: TeamMemberPermissions(can_edit=True, can_approve=True, can_submit=False),
            TeamMemberRole.GRANT_WRITER: TeamMemberPermissions(can_edit=True, can_approve=False, can_submit=False),
            TeamMemberRole.REVIEWER: TeamMemberPermissions(can_edit=False, can_approve=True, can_submit=False),
            TeamMemberRole.ADMIN: TeamMemberPermissions(can_edit=True, can_approve=True, can_submit=True),
        }
        return defaults.get(self.role, TeamMemberPermissions())

    class Config:
        from_attributes = True


class TeamMemberList(BaseModel):
    """Schema for list of team members (standard paginated format)."""
    data: List[TeamMemberResponse] = Field(..., description="List of team members")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def items(self) -> List[TeamMemberResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# ============================================================================
# Default Workflow Templates
# ============================================================================

DEFAULT_WORKFLOWS = {
    "standard": {
        "name": "Standard Review",
        "description": "Standard internal review workflow for grant applications",
        "stages": [
            {"order": 0, "name": "Draft Review", "required_role": "grant_writer", "sla_hours": 48, "auto_escalate": False},
            {"order": 1, "name": "PI Review", "required_role": "pi", "sla_hours": 72, "auto_escalate": True},
            {"order": 2, "name": "Department Approval", "required_role": "admin", "sla_hours": 96, "auto_escalate": True},
            {"order": 3, "name": "Sponsored Programs", "required_role": "admin", "sla_hours": 120, "auto_escalate": True},
        ],
    },
    "quick": {
        "name": "Quick Review",
        "description": "Expedited review for smaller grants or renewals",
        "stages": [
            {"order": 0, "name": "PI Review", "required_role": "pi", "sla_hours": 24, "auto_escalate": False},
            {"order": 1, "name": "Admin Approval", "required_role": "admin", "sla_hours": 48, "auto_escalate": False},
        ],
    },
    "comprehensive": {
        "name": "Comprehensive Review",
        "description": "Full review cycle for major grants",
        "stages": [
            {"order": 0, "name": "Draft Review", "required_role": "grant_writer", "sla_hours": 48, "auto_escalate": False},
            {"order": 1, "name": "Co-I Review", "required_role": "co_i", "sla_hours": 72, "auto_escalate": False},
            {"order": 2, "name": "PI Review", "required_role": "pi", "sla_hours": 72, "auto_escalate": True},
            {"order": 3, "name": "Department Chair", "required_role": "admin", "sla_hours": 96, "auto_escalate": True},
            {"order": 4, "name": "College Review", "required_role": "admin", "sla_hours": 96, "auto_escalate": True},
            {"order": 5, "name": "Sponsored Programs", "required_role": "admin", "sla_hours": 120, "auto_escalate": True},
        ],
    },
}


class DefaultWorkflowResponse(BaseModel):
    """Schema for default workflow template."""
    key: str = Field(..., description="Template key")
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    stages: List[WorkflowStage] = Field(..., description="Template stages")
    stage_count: int = Field(..., description="Number of stages")
