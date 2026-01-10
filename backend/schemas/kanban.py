"""Kanban board schemas for grant application management."""

from datetime import datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field
from enum import Enum


class ApplicationStage(str, Enum):
    RESEARCHING = "researching"
    WRITING = "writing"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    REJECTED = "rejected"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MemberRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    VIEWER = "viewer"


class AttachmentCategory(str, Enum):
    BUDGET = "budget"
    BIOSKETCH = "biosketch"
    LETTER = "letter"
    DRAFT = "draft"
    OTHER = "other"


class FieldType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"
    URL = "url"
    CHECKBOX = "checkbox"


# Subtask schemas
class SubtaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    due_date: Optional[datetime] = None


class SubtaskCreate(SubtaskBase):
    pass


class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    is_completed: Optional[bool] = None
    due_date: Optional[datetime] = None
    position: Optional[int] = None


class SubtaskResponse(SubtaskBase):
    id: UUID
    application_id: UUID
    is_completed: bool
    completed_at: Optional[datetime] = None
    completed_by: Optional[UUID] = None
    position: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Activity schemas
class ActivityResponse(BaseModel):
    id: UUID
    application_id: UUID
    user_id: Optional[UUID] = None
    action: str
    details: Optional[dict] = None
    created_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=5000)


# Attachment schemas
class AttachmentResponse(BaseModel):
    id: UUID
    application_id: UUID
    user_id: UUID
    filename: str
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    description: Optional[str] = None
    category: Optional[str] = None
    template_id: Optional[UUID] = None
    created_at: datetime
    user_name: Optional[str] = None

    class Config:
        from_attributes = True


# Custom field schemas
class FieldOption(BaseModel):
    value: str
    label: str
    color: Optional[str] = None


class FieldDefinitionCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    field_type: FieldType
    options: Optional[List[FieldOption]] = None
    is_required: bool = False
    show_in_card: bool = True


class FieldDefinitionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    options: Optional[List[FieldOption]] = None
    is_required: Optional[bool] = None
    show_in_card: Optional[bool] = None
    position: Optional[int] = None


class FieldDefinitionResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    field_type: str
    options: Optional[List[FieldOption]] = None
    is_required: bool
    show_in_card: bool
    position: int
    created_at: datetime

    class Config:
        from_attributes = True


class FieldValuesUpdate(BaseModel):
    fields: dict[str, Any]


# Team schemas
class TeamInvite(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    role: MemberRole = MemberRole.MEMBER


class LabMemberResponse(BaseModel):
    id: UUID
    lab_owner_id: UUID
    member_email: str
    member_user_id: Optional[UUID] = None
    role: str
    invited_at: datetime
    accepted_at: Optional[datetime] = None
    member_name: Optional[str] = None

    class Config:
        from_attributes = True


class AssigneeResponse(BaseModel):
    application_id: UUID
    user_id: UUID
    assigned_at: datetime
    assigned_by: Optional[UUID] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None

    class Config:
        from_attributes = True


class AssigneesUpdate(BaseModel):
    user_ids: List[UUID]


# Card schemas
class CardUpdate(BaseModel):
    stage: Optional[ApplicationStage] = None
    position: Optional[int] = None
    priority: Optional[Priority] = None
    color: Optional[str] = Field(None, max_length=7)
    notes: Optional[str] = None
    target_date: Optional[datetime] = None
    archived: Optional[bool] = None


class SubtaskProgress(BaseModel):
    completed: int
    total: int


class KanbanCardResponse(BaseModel):
    id: UUID
    user_id: UUID
    grant_id: Optional[UUID] = None
    match_id: Optional[UUID] = None
    stage: str
    position: int
    priority: str
    color: Optional[str] = None
    notes: Optional[str] = None
    target_date: Optional[datetime] = None
    archived: bool
    subtask_progress: SubtaskProgress
    attachments_count: int
    assignees: List[AssigneeResponse] = []
    custom_fields: dict = {}
    created_at: datetime
    updated_at: datetime
    grant_title: Optional[str] = None
    grant_agency: Optional[str] = None
    grant_deadline: Optional[datetime] = None

    class Config:
        from_attributes = True


# Board schemas
class ReorderRequest(BaseModel):
    card_id: UUID
    from_stage: ApplicationStage
    to_stage: ApplicationStage
    new_position: int


class SubtaskReorderRequest(BaseModel):
    subtask_ids: List[UUID]


class BoardTotals(BaseModel):
    total: int
    by_stage: dict[str, int]
    overdue: int


class KanbanBoardResponse(BaseModel):
    columns: dict[str, List[KanbanCardResponse]]
    field_definitions: List[FieldDefinitionResponse]
    team_members: List[LabMemberResponse]
    totals: BoardTotals
