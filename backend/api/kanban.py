"""Kanban board API router."""

import os
import uuid
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import CurrentUser
from backend.schemas.kanban import (
    KanbanBoardResponse,
    KanbanCardResponse,
    CardUpdate,
    ReorderRequest,
    SubtaskCreate,
    SubtaskUpdate,
    SubtaskResponse,
    SubtaskReorderRequest,
    ActivityResponse,
    CommentCreate,
    AttachmentResponse,
    FieldDefinitionCreate,
    FieldDefinitionUpdate,
    FieldDefinitionResponse,
    FieldValuesUpdate,
    TeamInvite,
    LabMemberResponse,
    AssigneeResponse,
    AssigneesUpdate,
)
from backend.api.kanban_service import KanbanService


router = APIRouter(prefix="/api/kanban", tags=["kanban"])

# Upload directory for attachments
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads", "attachments")
os.makedirs(UPLOAD_DIR, exist_ok=True)


def get_service(db: AsyncSession = Depends(get_db)) -> KanbanService:
    return KanbanService(db)


# ===== Board Endpoints =====


@router.get("", response_model=KanbanBoardResponse)
async def get_board(
    current_user: CurrentUser,
    stages: Optional[str] = None,
    priorities: Optional[str] = None,
    assignee_ids: Optional[str] = None,
    search: Optional[str] = None,
    show_archived: bool = False,
    service: KanbanService = Depends(get_service),
):
    """Get the kanban board with all cards."""
    stages_list = stages.split(",") if stages else None
    priorities_list = priorities.split(",") if priorities else None
    assignee_list = [UUID(a) for a in assignee_ids.split(",")] if assignee_ids else None

    return await service.get_board(
        user_id=current_user.id,
        stages=stages_list,
        priorities=priorities_list,
        assignee_ids=assignee_list,
        search=search,
        show_archived=show_archived,
    )


@router.post("/reorder", response_model=KanbanCardResponse)
async def reorder_card(
    data: ReorderRequest,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Reorder a card (move between/within columns)."""
    try:
        app = await service.reorder_card(current_user.id, data)
        return service._build_card_response(app)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{app_id}", response_model=KanbanCardResponse)
async def update_card(
    app_id: UUID,
    data: CardUpdate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Update a card's properties."""
    try:
        app = await service.update_card(current_user.id, app_id, data)
        return service._build_card_response(app)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Subtask Endpoints =====


@router.get("/{app_id}/subtasks", response_model=List[SubtaskResponse])
async def get_subtasks(
    app_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Get all subtasks for an application."""
    try:
        return await service.get_subtasks(current_user.id, app_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_id}/subtasks", response_model=SubtaskResponse)
async def create_subtask(
    app_id: UUID,
    data: SubtaskCreate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Create a new subtask."""
    try:
        return await service.create_subtask(current_user.id, app_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/subtasks/{subtask_id}", response_model=SubtaskResponse)
async def update_subtask(
    subtask_id: UUID,
    data: SubtaskUpdate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Update a subtask."""
    try:
        return await service.update_subtask(current_user.id, subtask_id, data)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/subtasks/{subtask_id}")
async def delete_subtask(
    subtask_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Delete a subtask."""
    try:
        await service.delete_subtask(current_user.id, subtask_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_id}/subtasks/reorder", response_model=List[SubtaskResponse])
async def reorder_subtasks(
    app_id: UUID,
    data: SubtaskReorderRequest,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Reorder subtasks."""
    try:
        return await service.reorder_subtasks(current_user.id, app_id, data.subtask_ids)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Activity Endpoints =====


@router.get("/{app_id}/activities", response_model=List[ActivityResponse])
async def get_activities(
    app_id: UUID,
    current_user: CurrentUser,
    limit: int = 50,
    offset: int = 0,
    service: KanbanService = Depends(get_service),
):
    """Get activity log for an application."""
    try:
        activities = await service.get_activities(current_user.id, app_id, limit, offset)
        return [
            {
                "id": a.id,
                "application_id": a.application_id,
                "user_id": a.user_id,
                "action": a.action,
                "details": a.details,
                "created_at": a.created_at,
                "user_name": a.user.name if a.user else None,
                "user_email": a.user.email if a.user else None,
            }
            for a in activities
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_id}/comments", response_model=ActivityResponse)
async def add_comment(
    app_id: UUID,
    data: CommentCreate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Add a comment to an application."""
    try:
        activity = await service.add_comment(current_user.id, app_id, data.content)
        return {
            "id": activity.id,
            "application_id": activity.application_id,
            "user_id": activity.user_id,
            "action": activity.action,
            "details": activity.details,
            "created_at": activity.created_at,
            "user_name": current_user.name,
            "user_email": current_user.email,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Attachment Endpoints =====


@router.get("/{app_id}/attachments", response_model=List[AttachmentResponse])
async def get_attachments(
    app_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Get all attachments for an application."""
    try:
        attachments = await service.get_attachments(current_user.id, app_id)
        return [
            {
                "id": a.id,
                "application_id": a.application_id,
                "user_id": a.user_id,
                "filename": a.filename,
                "file_type": a.file_type,
                "file_size": a.file_size,
                "description": a.description,
                "category": a.category,
                "template_id": a.template_id,
                "created_at": a.created_at,
                "user_name": a.user.name if a.user else None,
            }
            for a in attachments
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{app_id}/attachments", response_model=AttachmentResponse)
async def upload_attachment(
    app_id: UUID,
    current_user: CurrentUser,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    category: Optional[str] = Form(None),
    service: KanbanService = Depends(get_service),
):
    """Upload an attachment."""
    try:
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1] if file.filename else ""
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        # Save file
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)

        attachment = await service.create_attachment(
            user_id=current_user.id,
            app_id=app_id,
            filename=file.filename or "unnamed",
            file_type=file.content_type,
            file_size=len(content),
            storage_path=file_path,
            description=description,
            category=category,
        )

        return {
            "id": attachment.id,
            "application_id": attachment.application_id,
            "user_id": attachment.user_id,
            "filename": attachment.filename,
            "file_type": attachment.file_type,
            "file_size": attachment.file_size,
            "description": attachment.description,
            "category": attachment.category,
            "template_id": attachment.template_id,
            "created_at": attachment.created_at,
            "user_name": current_user.name,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Delete an attachment."""
    try:
        storage_path = await service.delete_attachment(current_user.id, attachment_id)
        # Delete file
        if os.path.exists(storage_path):
            os.remove(storage_path)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Download an attachment."""
    try:
        attachment = await service.get_attachment_by_id(current_user.id, attachment_id)
        if not os.path.exists(attachment.storage_path):
            raise HTTPException(status_code=404, detail="File not found")
        return FileResponse(
            attachment.storage_path,
            filename=attachment.filename,
            media_type=attachment.file_type or "application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Custom Field Endpoints =====


@router.get("/fields", response_model=List[FieldDefinitionResponse])
async def get_field_definitions(
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Get all custom field definitions."""
    fields = await service.get_field_definitions(current_user.id)
    return [service._build_field_response(f) for f in fields]


@router.post("/fields", response_model=FieldDefinitionResponse)
async def create_field_definition(
    data: FieldDefinitionCreate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Create a custom field definition."""
    field = await service.create_field_definition(current_user.id, data)
    return service._build_field_response(field)


@router.patch("/fields/{field_id}", response_model=FieldDefinitionResponse)
async def update_field_definition(
    field_id: UUID,
    data: FieldDefinitionUpdate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Update a custom field definition."""
    try:
        field = await service.update_field_definition(current_user.id, field_id, data)
        return service._build_field_response(field)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/fields/{field_id}")
async def delete_field_definition(
    field_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Delete a custom field definition."""
    try:
        await service.delete_field_definition(current_user.id, field_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{app_id}/fields", response_model=KanbanCardResponse)
async def update_card_fields(
    app_id: UUID,
    data: FieldValuesUpdate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Update custom field values for an application."""
    try:
        app = await service.update_card_fields(current_user.id, app_id, data.fields)
        return service._build_card_response(app)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# ===== Team Endpoints =====


@router.get("/team", response_model=List[LabMemberResponse])
async def get_team_members(
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Get all lab team members."""
    members = await service.get_team_members(current_user.id)
    return [service._build_member_response(m) for m in members]


@router.post("/team/invite", response_model=LabMemberResponse)
async def invite_team_member(
    data: TeamInvite,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Invite a new team member."""
    try:
        member = await service.invite_team_member(current_user.id, data)
        return service._build_member_response(member)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/team/{member_id}")
async def remove_team_member(
    member_id: UUID,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Remove a team member."""
    try:
        await service.remove_team_member(current_user.id, member_id)
        return {"status": "deleted"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/{app_id}/assignees", response_model=List[AssigneeResponse])
async def update_assignees(
    app_id: UUID,
    data: AssigneesUpdate,
    current_user: CurrentUser,
    service: KanbanService = Depends(get_service),
):
    """Update assignees for an application."""
    try:
        assignees = await service.update_assignees(current_user.id, app_id, data.user_ids)
        return [
            {
                "application_id": a.application_id,
                "user_id": a.user_id,
                "assigned_at": a.assigned_at,
                "assigned_by": a.assigned_by,
                "user_name": a.user.name if a.user else None,
                "user_email": a.user.email if a.user else None,
            }
            for a in assignees
        ]
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
