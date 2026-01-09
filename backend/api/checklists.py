"""
Checklist management API endpoints.
CRUD operations for checklist templates and application checklists.
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import selectinload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import AuthorizationError, ConflictError, NotFoundError, ValidationError
from backend.models import GrantApplication
from backend.models.checklists import ApplicationChecklist, ChecklistTemplate
from backend.schemas.checklists import (
    ApplicationChecklistCreate,
    ApplicationChecklistList,
    ApplicationChecklistResponse,
    ChecklistItemCategory,
    ChecklistItemStatus,
    ChecklistItemUpdate,
    ChecklistProgressSummary,
    ChecklistTemplateCreate,
    ChecklistTemplateList,
    ChecklistTemplateResponse,
    FunderTemplatesResponse,
)
from backend.schemas.common import PaginationInfo

router = APIRouter(prefix="/api/checklists", tags=["Checklists"])


# =============================================================================
# Helper Functions
# =============================================================================


def _convert_template_items_to_checklist_items(template_items: list) -> list:
    """Convert template items to checklist items with status fields."""
    checklist_items = []
    for item in template_items:
        checklist_item = {
            "item_id": item.get("id", str(uuid.uuid4())),
            "title": item.get("title", ""),
            "description": item.get("description"),
            "required": item.get("required", True),
            "weight": item.get("weight", 1.0),
            "category": item.get("category", ChecklistItemCategory.OTHER.value),
            "dependencies": item.get("dependencies", []),
            "completed": False,
            "completed_at": None,
            "completed_by": None,
            "notes": None,
        }
        checklist_items.append(checklist_item)
    return checklist_items


def _calculate_progress(items: list) -> float:
    """Calculate weighted completion percentage."""
    if not items:
        return 0.0

    total_weight = sum(item.get("weight", 1.0) for item in items)
    if total_weight == 0:
        return 0.0

    completed_weight = sum(
        item.get("weight", 1.0)
        for item in items
        if item.get("completed", False)
    )

    return (completed_weight / total_weight) * 100.0


def _build_checklist_response(checklist: ApplicationChecklist) -> ApplicationChecklistResponse:
    """Build response object from checklist model."""
    items = [
        ChecklistItemStatus(
            item_id=item.get("item_id", ""),
            title=item.get("title", ""),
            description=item.get("description"),
            required=item.get("required", True),
            weight=item.get("weight", 1.0),
            category=item.get("category", ChecklistItemCategory.OTHER.value),
            dependencies=item.get("dependencies", []),
            completed=item.get("completed", False),
            completed_at=item.get("completed_at"),
            completed_by=item.get("completed_by"),
            notes=item.get("notes"),
        )
        for item in checklist.items
    ]

    return ApplicationChecklistResponse(
        id=checklist.id,
        kanban_card_id=checklist.kanban_card_id,
        template_id=checklist.template_id,
        name=checklist.name,
        items=items,
        progress_percent=checklist.progress_percent,
        created_at=checklist.created_at,
        updated_at=checklist.updated_at,
    )


# =============================================================================
# Checklist Template Endpoints
# =============================================================================


@router.get(
    "/templates",
    response_model=ChecklistTemplateList,
    summary="List checklist templates",
    description="Get all available checklist templates, optionally filtered by funder.",
)
async def list_templates(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: Optional[str] = Query(None, description="Filter by funder name"),
    mechanism: Optional[str] = Query(None, description="Filter by grant mechanism"),
    system_only: bool = Query(False, description="Only show system templates"),
) -> ChecklistTemplateList:
    """
    List all available checklist templates.

    Includes both system templates and user-created templates.
    """
    query = select(ChecklistTemplate)

    # Apply filters
    if funder:
        query = query.where(ChecklistTemplate.funder.ilike(f"%{funder}%"))
    if mechanism:
        query = query.where(ChecklistTemplate.mechanism.ilike(f"%{mechanism}%"))
    if system_only:
        query = query.where(ChecklistTemplate.is_system == True)
    else:
        # Show system templates and user's own templates only
        # Non-system templates are strictly filtered to those created by the current user
        query = query.where(
            or_(
                ChecklistTemplate.is_system == True,
                ChecklistTemplate.created_by == current_user.id,
            )
        )

    query = query.order_by(ChecklistTemplate.funder, ChecklistTemplate.name)

    result = await db.execute(query)
    templates = result.scalars().all()

    return ChecklistTemplateList(
        data=list(templates),
        pagination=PaginationInfo(
            total=len(templates),
            offset=0,
            limit=len(templates),
            has_more=False,
        ),
    )


@router.get(
    "/templates/{funder}",
    response_model=FunderTemplatesResponse,
    summary="Get templates for a specific funder",
    description="Get all checklist templates for a specific funding organization.",
)
async def get_templates_by_funder(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: str,
    mechanism: Optional[str] = Query(None, description="Filter by grant mechanism"),
) -> FunderTemplatesResponse:
    """
    Get all checklist templates for a specific funder.

    Returns templates matching the funder name (case-insensitive).
    """
    # Show system templates and user's own templates only for the specified funder
    query = select(ChecklistTemplate).where(
        and_(
            ChecklistTemplate.funder.ilike(funder),
            or_(
                ChecklistTemplate.is_system == True,
                ChecklistTemplate.created_by == current_user.id,
            ),
        )
    )

    if mechanism:
        query = query.where(ChecklistTemplate.mechanism.ilike(f"%{mechanism}%"))

    query = query.order_by(ChecklistTemplate.mechanism, ChecklistTemplate.name)

    result = await db.execute(query)
    templates = result.scalars().all()

    return FunderTemplatesResponse(
        funder=funder,
        templates=templates,
        total=len(templates),
    )


@router.get(
    "/templates/detail/{template_id}",
    response_model=ChecklistTemplateResponse,
    summary="Get template details",
    description="Get detailed information about a specific checklist template.",
)
async def get_template(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    template_id: UUID,
) -> ChecklistTemplateResponse:
    """Get a specific checklist template by ID."""
    result = await db.execute(
        select(ChecklistTemplate).where(ChecklistTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Template")

    # Check access: system templates are public, user templates are private
    if not template.is_system and template.created_by != current_user.id:
        raise AuthorizationError("Not authorized to access this template")

    return template


@router.post(
    "/templates",
    response_model=ChecklistTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create checklist template",
    description="Create a new user-defined checklist template.",
)
async def create_template(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: ChecklistTemplateCreate,
) -> ChecklistTemplateResponse:
    """
    Create a new checklist template.

    User-created templates are not system templates and can only be
    viewed/edited by the creator.
    """
    # Convert items to the expected format with generated IDs
    items = [
        {
            "id": str(uuid.uuid4()),
            "title": item.title,
            "description": item.description,
            "required": item.required,
            "weight": item.weight,
            "category": item.category.value,
            "dependencies": item.dependencies,
        }
        for item in data.items
    ]

    template = ChecklistTemplate(
        funder=data.funder,
        mechanism=data.mechanism,
        name=data.name,
        description=data.description,
        items=items,
        is_system=False,
        created_by=current_user.id,
    )

    db.add(template)
    await db.commit()
    await db.refresh(template)

    return template


# =============================================================================
# Application Checklist Endpoints
# =============================================================================


@router.post(
    "/{card_id}/checklist",
    response_model=ApplicationChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create checklist for application",
    description="Create a new checklist for a grant application from a template or custom.",
)
async def create_checklist(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    data: ApplicationChecklistCreate,
) -> ApplicationChecklistResponse:
    """
    Create a checklist for a grant application.

    Can create from a template (provide template_id) or custom
    (provide name and items).
    """
    # Verify the card exists and belongs to the user
    result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise NotFoundError("Application")

    # Handle template-based checklist
    if data.template_id:
        result = await db.execute(
            select(ChecklistTemplate).where(ChecklistTemplate.id == data.template_id)
        )
        template = result.scalar_one_or_none()

        if not template:
            raise NotFoundError("Template")

        # Check if checklist already exists for this template and card
        existing = await db.execute(
            select(ApplicationChecklist).where(
                and_(
                    ApplicationChecklist.kanban_card_id == card_id,
                    ApplicationChecklist.template_id == data.template_id,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ConflictError("Checklist from this template already exists for this application")

        checklist_items = _convert_template_items_to_checklist_items(template.items)
        checklist_name = data.name or template.name

        checklist = ApplicationChecklist(
            kanban_card_id=card_id,
            template_id=template.id,
            name=checklist_name,
            items=checklist_items,
            progress_percent=0.0,
        )

    # Handle custom checklist
    else:
        if not data.name or not data.items:
            raise ValidationError("Either template_id or both name and items are required")

        checklist_items = [
            {
                "item_id": str(uuid.uuid4()),
                "title": item.title,
                "description": item.description,
                "required": item.required,
                "weight": item.weight,
                "category": item.category.value,
                "dependencies": item.dependencies,
                "completed": False,
                "completed_at": None,
                "completed_by": None,
                "notes": None,
            }
            for item in data.items
        ]

        checklist = ApplicationChecklist(
            kanban_card_id=card_id,
            template_id=None,
            name=data.name,
            items=checklist_items,
            progress_percent=0.0,
        )

    db.add(checklist)
    await db.commit()
    await db.refresh(checklist)

    return _build_checklist_response(checklist)


@router.get(
    "/{card_id}/checklist",
    response_model=ChecklistProgressSummary,
    summary="Get all checklists for application",
    description="Get all checklists associated with a grant application.",
)
async def get_checklists(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
) -> ChecklistProgressSummary:
    """
    Get all checklists for a grant application.

    Returns a summary with overall progress and individual checklists.
    """
    # Verify the card exists and belongs to the user
    result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise NotFoundError("Application")

    # Get all checklists for this application with eager-loaded templates
    result = await db.execute(
        select(ApplicationChecklist)
        .options(selectinload(ApplicationChecklist.template))
        .where(ApplicationChecklist.kanban_card_id == card_id)
        .order_by(ApplicationChecklist.created_at)
    )
    checklists = result.scalars().all()

    checklist_responses = [_build_checklist_response(c) for c in checklists]

    # Calculate overall progress
    if checklists:
        overall_progress = sum(c.progress_percent for c in checklists) / len(checklists)
        all_complete = all(c.progress_percent >= 100.0 for c in checklists)
    else:
        overall_progress = 0.0
        all_complete = False

    return ChecklistProgressSummary(
        total_checklists=len(checklists),
        overall_progress=overall_progress,
        all_complete=all_complete,
        checklists=checklist_responses,
    )


@router.patch(
    "/{card_id}/checklist/items/{item_id}",
    response_model=ApplicationChecklistResponse,
    summary="Update checklist item status",
    description="Update the completion status of a checklist item.",
)
async def update_checklist_item(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    item_id: str,
    data: ChecklistItemUpdate,
    checklist_id: Optional[UUID] = Query(None, description="Specific checklist ID (if multiple)"),
) -> ApplicationChecklistResponse:
    """
    Update a checklist item's status.

    Marks an item as completed/incomplete and optionally adds notes.
    Automatically recalculates progress percentage.
    """
    # Verify the card exists and belongs to the user
    result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise NotFoundError("Application")

    # Find the checklist containing this item
    query = select(ApplicationChecklist).where(
        ApplicationChecklist.kanban_card_id == card_id
    )
    if checklist_id:
        query = query.where(ApplicationChecklist.id == checklist_id)

    result = await db.execute(query)
    checklists = result.scalars().all()

    # Find the item in any of the checklists
    target_checklist = None
    target_item_index = None

    for checklist in checklists:
        for i, item in enumerate(checklist.items):
            if item.get("item_id") == item_id:
                target_checklist = checklist
                target_item_index = i
                break
        if target_checklist:
            break

    if not target_checklist or target_item_index is None:
        raise NotFoundError("Checklist item")

    # Update the item
    items = list(target_checklist.items)  # Create a mutable copy
    item = dict(items[target_item_index])  # Create a mutable copy of the item

    if data.completed is not None:
        item["completed"] = data.completed
        if data.completed:
            item["completed_at"] = datetime.now(timezone.utc).isoformat()
            item["completed_by"] = str(current_user.id)
        else:
            item["completed_at"] = None
            item["completed_by"] = None

    if data.notes is not None:
        item["notes"] = data.notes

    items[target_item_index] = item
    target_checklist.items = items

    # Recalculate progress
    target_checklist.progress_percent = _calculate_progress(items)
    target_checklist.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(target_checklist)

    return _build_checklist_response(target_checklist)


@router.delete(
    "/{card_id}/checklist/{checklist_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete checklist",
    description="Delete a checklist from an application.",
)
async def delete_checklist(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    checklist_id: UUID,
) -> None:
    """Delete a checklist from an application."""
    # Verify the card exists and belongs to the user
    result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise NotFoundError("Application")

    # Find and delete the checklist
    result = await db.execute(
        select(ApplicationChecklist).where(
            and_(
                ApplicationChecklist.id == checklist_id,
                ApplicationChecklist.kanban_card_id == card_id,
            )
        )
    )
    checklist = result.scalar_one_or_none()

    if not checklist:
        raise NotFoundError("Checklist")

    await db.delete(checklist)
    await db.commit()


# =============================================================================
# Kanban Integration Router (for /api/kanban/{card_id}/checklist endpoints)
# =============================================================================

kanban_router = APIRouter(prefix="/api/kanban", tags=["Kanban Checklists"])


@kanban_router.post(
    "/{card_id}/checklist",
    response_model=ApplicationChecklistResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create checklist for kanban card",
    description="Create a new checklist for a kanban card from a template or custom.",
)
async def kanban_create_checklist(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    data: ApplicationChecklistCreate,
) -> ApplicationChecklistResponse:
    """Proxy to create_checklist for kanban integration."""
    return await create_checklist(db, current_user, card_id, data)


@kanban_router.patch(
    "/{card_id}/checklist/items/{item_id}",
    response_model=ApplicationChecklistResponse,
    summary="Update checklist item for kanban card",
    description="Update the completion status of a checklist item.",
)
async def kanban_update_checklist_item(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
    item_id: str,
    data: ChecklistItemUpdate,
    checklist_id: Optional[UUID] = Query(None, description="Specific checklist ID"),
) -> ApplicationChecklistResponse:
    """Proxy to update_checklist_item for kanban integration."""
    return await update_checklist_item(db, current_user, card_id, item_id, data, checklist_id)


@kanban_router.get(
    "/{card_id}/checklist",
    response_model=ChecklistProgressSummary,
    summary="Get checklists for kanban card",
    description="Get all checklists associated with a kanban card.",
)
async def kanban_get_checklists(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    card_id: UUID,
) -> ChecklistProgressSummary:
    """Proxy to get_checklists for kanban integration."""
    return await get_checklists(db, current_user, card_id)
