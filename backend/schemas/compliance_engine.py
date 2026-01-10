"""
Compliance Engine Schemas
Pydantic models for the compliance engine API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import PaginationInfo


# =============================================================================
# Enums
# =============================================================================


class RequirementType(str, Enum):
    """Types of compliance requirements."""

    REPORTING = "reporting"
    FINANCIAL = "financial"
    ETHICAL = "ethical"
    DATA_MANAGEMENT = "data_management"


class RequirementFrequency(str, Enum):
    """Frequency of compliance requirements."""

    ONE_TIME = "one_time"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    FINAL = "final"


class ComplianceTaskStatus(str, Enum):
    """Status of a compliance task."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    OVERDUE = "overdue"


class TemplateType(str, Enum):
    """Types of compliance templates."""

    PROGRESS_REPORT = "progress_report"
    FINANCIAL_REPORT = "financial_report"
    DATA_PLAN = "data_plan"
    INVENTION_REPORT = "invention_report"
    OUTCOMES_REPORT = "outcomes_report"


# =============================================================================
# Funder Requirement Schemas
# =============================================================================


class FunderRequirementBase(BaseModel):
    """Base schema for funder requirements."""

    funder_name: str = Field(..., min_length=1, max_length=255, description="Name of the funding organization")
    requirement_type: RequirementType = Field(..., description="Type of requirement")
    requirement_text: str = Field(..., min_length=1, description="Description of the requirement")
    frequency: RequirementFrequency = Field(..., description="How often this requirement recurs")
    deadline_offset_days: Optional[int] = Field(None, ge=0, description="Days after award start/anniversary when due")
    mechanism: Optional[str] = Field(None, max_length=50, description="Specific grant mechanism (e.g., R01, R21)")
    notes: Optional[str] = Field(None, description="Additional notes about the requirement")


class FunderRequirementCreate(FunderRequirementBase):
    """Schema for creating a funder requirement."""

    is_active: bool = Field(True, description="Whether this requirement is active")


class FunderRequirementUpdate(BaseModel):
    """Schema for updating a funder requirement."""

    requirement_text: Optional[str] = Field(None, min_length=1)
    frequency: Optional[RequirementFrequency] = None
    deadline_offset_days: Optional[int] = Field(None, ge=0)
    mechanism: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FunderRequirementResponse(FunderRequirementBase):
    """Schema for funder requirement response."""

    id: UUID = Field(..., description="Requirement ID")
    is_active: bool = Field(..., description="Whether this requirement is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class FunderRequirementList(BaseModel):
    """Schema for list of funder requirements."""

    data: List[FunderRequirementResponse] = Field(..., description="List of requirements")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


# =============================================================================
# Compliance Task Schemas
# =============================================================================


class ComplianceTaskBase(BaseModel):
    """Base schema for compliance tasks."""

    title: str = Field(..., min_length=1, max_length=500, description="Task title")
    description: Optional[str] = Field(None, description="Task description")
    due_date: datetime = Field(..., description="Due date for the task")
    notes: Optional[str] = Field(None, description="Additional notes")


class ComplianceTaskCreate(ComplianceTaskBase):
    """Schema for creating a compliance task."""

    match_id: Optional[UUID] = Field(None, description="Associated match ID")
    grant_id: Optional[UUID] = Field(None, description="Associated grant ID")
    application_id: Optional[UUID] = Field(None, description="Associated application ID")
    requirement_id: Optional[UUID] = Field(None, description="Associated requirement ID")
    award_date: Optional[datetime] = Field(None, description="Award start date")


class ComplianceTaskUpdate(BaseModel):
    """Schema for updating a compliance task."""

    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None
    status: Optional[ComplianceTaskStatus] = None
    notes: Optional[str] = None


class ComplianceTaskResponse(ComplianceTaskBase):
    """Schema for compliance task response."""

    id: UUID = Field(..., description="Task ID")
    user_id: UUID = Field(..., description="Owner user ID")
    match_id: Optional[UUID] = Field(None, description="Associated match ID")
    grant_id: Optional[UUID] = Field(None, description="Associated grant ID")
    application_id: Optional[UUID] = Field(None, description="Associated application ID")
    requirement_id: Optional[UUID] = Field(None, description="Associated requirement ID")
    status: ComplianceTaskStatus = Field(..., description="Task status")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    completed_by: Optional[UUID] = Field(None, description="User who completed the task")
    reminder_sent_at: Optional[datetime] = Field(None, description="When reminder was sent")
    award_date: Optional[datetime] = Field(None, description="Award start date")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    # Computed fields for frontend convenience
    is_overdue: bool = Field(False, description="Whether the task is overdue")
    days_until_due: Optional[int] = Field(None, description="Days until due date")

    class Config:
        from_attributes = True

    @field_validator("is_overdue", mode="before")
    @classmethod
    def compute_is_overdue(cls, v, info):
        """Compute if task is overdue based on due_date and status."""
        values = info.data
        if values.get("status") == ComplianceTaskStatus.COMPLETED.value:
            return False
        due_date = values.get("due_date")
        if due_date and isinstance(due_date, datetime):
            return due_date < datetime.now(due_date.tzinfo)
        return False


class ComplianceTaskList(BaseModel):
    """Schema for list of compliance tasks."""

    data: List[ComplianceTaskResponse] = Field(..., description="List of tasks")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


class ComplianceTaskComplete(BaseModel):
    """Schema for completing a compliance task."""

    notes: Optional[str] = Field(None, description="Completion notes")


# =============================================================================
# Compliance Template Schemas
# =============================================================================


class TemplateSection(BaseModel):
    """A section within a compliance template."""

    name: str = Field(..., description="Section name")
    description: Optional[str] = Field(None, description="Section description")
    required: bool = Field(True, description="Whether this section is required")
    fields: Optional[List[Dict[str, Any]]] = Field(None, description="Fields within this section")


class ComplianceTemplateBase(BaseModel):
    """Base schema for compliance templates."""

    funder_name: str = Field(..., min_length=1, max_length=255, description="Funder name")
    mechanism: Optional[str] = Field(None, max_length=50, description="Grant mechanism")
    template_name: str = Field(..., min_length=1, max_length=255, description="Template name")
    template_type: TemplateType = Field(..., description="Type of template")
    template_content: Dict[str, Any] = Field(..., description="Template structure/content")
    description: Optional[str] = Field(None, description="Template description")


class ComplianceTemplateCreate(ComplianceTemplateBase):
    """Schema for creating a compliance template."""

    is_active: bool = Field(True, description="Whether this template is active")


class ComplianceTemplateUpdate(BaseModel):
    """Schema for updating a compliance template."""

    template_name: Optional[str] = Field(None, min_length=1, max_length=255)
    template_content: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ComplianceTemplateResponse(ComplianceTemplateBase):
    """Schema for compliance template response."""

    id: UUID = Field(..., description="Template ID")
    is_active: bool = Field(..., description="Whether this template is active")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True


class ComplianceTemplateList(BaseModel):
    """Schema for list of compliance templates."""

    data: List[ComplianceTemplateResponse] = Field(..., description="List of templates")
    pagination: PaginationInfo = Field(..., description="Pagination metadata")


# =============================================================================
# Compliance Checklist Schemas
# =============================================================================


class ChecklistItem(BaseModel):
    """A single item in the compliance checklist."""

    requirement_id: Optional[UUID] = Field(None, description="Requirement ID")
    task_id: Optional[UUID] = Field(None, description="Task ID if task exists")
    title: str = Field(..., description="Requirement/task title")
    description: Optional[str] = Field(None, description="Description")
    requirement_type: RequirementType = Field(..., description="Type of requirement")
    frequency: RequirementFrequency = Field(..., description="Frequency")
    due_date: Optional[datetime] = Field(None, description="Due date if applicable")
    status: Optional[ComplianceTaskStatus] = Field(None, description="Task status if task exists")
    is_completed: bool = Field(False, description="Whether completed")


class ComplianceChecklist(BaseModel):
    """Compliance checklist for a grant."""

    grant_id: UUID = Field(..., description="Grant ID")
    funder_name: str = Field(..., description="Funder name")
    mechanism: Optional[str] = Field(None, description="Grant mechanism")
    award_date: Optional[datetime] = Field(None, description="Award date")
    items: List[ChecklistItem] = Field(..., description="Checklist items")
    total_items: int = Field(..., description="Total number of items")
    completed_items: int = Field(..., description="Number of completed items")
    pending_items: int = Field(..., description="Number of pending items")
    overdue_items: int = Field(..., description="Number of overdue items")


# =============================================================================
# Upcoming Deadlines Schema
# =============================================================================


class UpcomingDeadline(BaseModel):
    """An upcoming compliance deadline."""

    task_id: UUID = Field(..., description="Task ID")
    title: str = Field(..., description="Task title")
    due_date: datetime = Field(..., description="Due date")
    days_until_due: int = Field(..., description="Days until due")
    status: ComplianceTaskStatus = Field(..., description="Task status")
    grant_title: Optional[str] = Field(None, description="Associated grant title")
    funder_name: Optional[str] = Field(None, description="Funder name")
    requirement_type: Optional[RequirementType] = Field(None, description="Requirement type")


class UpcomingDeadlinesList(BaseModel):
    """List of upcoming compliance deadlines."""

    data: List[UpcomingDeadline] = Field(..., description="List of upcoming deadlines")
    total: int = Field(..., description="Total count")


# =============================================================================
# Generate Tasks Request
# =============================================================================


class GenerateComplianceTasksRequest(BaseModel):
    """Request to generate compliance tasks for an awarded grant."""

    application_id: UUID = Field(..., description="Application ID for the awarded grant")
    award_date: datetime = Field(..., description="Award start date")
    funder_name: Optional[str] = Field(None, description="Funder name (auto-detected if not provided)")
    mechanism: Optional[str] = Field(None, description="Grant mechanism")


class GenerateComplianceTasksResponse(BaseModel):
    """Response from generating compliance tasks."""

    tasks_created: int = Field(..., description="Number of tasks created")
    tasks: List[ComplianceTaskResponse] = Field(..., description="Created tasks")
