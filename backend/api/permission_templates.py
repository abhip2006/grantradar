"""Permission Templates API endpoints for managing reusable permission configurations."""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError, ConflictError, ValidationError
from backend.models import PermissionTemplate, LabMember
from backend.schemas.permission_templates import (
    TemplatePermissions,
    PermissionTemplateCreate,
    PermissionTemplateUpdate,
    PermissionTemplateResponse,
    PermissionTemplateListResponse,
    DefaultTemplatesResponse,
    ApplyTemplateResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/team/permission-templates",
    tags=["Permission Templates"],
)


# =============================================================================
# Default Templates
# =============================================================================

# Built-in default templates that are available to all users
DEFAULT_TEMPLATES = [
    {
        "name": "Admin",
        "description": "Full access to all features including team management",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": True,
            "can_invite": True,
            "can_manage_grants": True,
            "can_export": True,
        },
    },
    {
        "name": "Member",
        "description": "Standard access for team members - can view, edit, and create",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": False,
            "can_export": True,
        },
    },
    {
        "name": "Viewer",
        "description": "Read-only access - can view but not modify anything",
        "permissions": {
            "can_view": True,
            "can_edit": False,
            "can_create": False,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": False,
            "can_export": False,
        },
    },
    {
        "name": "Contributor",
        "description": "Can create and edit own content but not delete or manage team",
        "permissions": {
            "can_view": True,
            "can_edit": True,
            "can_create": True,
            "can_delete": False,
            "can_invite": False,
            "can_manage_grants": False,
            "can_export": False,
        },
    },
]


# =============================================================================
# Helper Functions
# =============================================================================


def _build_template_response(
    template: PermissionTemplate,
) -> PermissionTemplateResponse:
    """Build a PermissionTemplateResponse from a PermissionTemplate model."""
    permissions = TemplatePermissions(**template.permissions)
    return PermissionTemplateResponse(
        id=template.id,
        owner_id=template.owner_id,
        name=template.name,
        description=template.description,
        permissions=permissions,
        is_default=template.is_default,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


async def _get_template_by_id(
    db: AsyncSession,
    user_id: UUID,
    template_id: UUID,
) -> PermissionTemplate:
    """
    Get a permission template by ID with ownership check.

    Args:
        db: Database session.
        user_id: ID of the user who owns the template.
        template_id: ID of the template.

    Returns:
        PermissionTemplate record.

    Raises:
        NotFoundError: If template not found or ownership mismatch.
    """
    result = await db.execute(
        select(PermissionTemplate).where(
            PermissionTemplate.id == template_id,
            PermissionTemplate.owner_id == user_id,
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise NotFoundError("Permission template", str(template_id))

    return template


async def _check_name_conflict(
    db: AsyncSession,
    user_id: UUID,
    name: str,
    exclude_id: Optional[UUID] = None,
) -> None:
    """
    Check if a template name already exists for this user.

    Args:
        db: Database session.
        user_id: ID of the user.
        name: Template name to check.
        exclude_id: Optional template ID to exclude from check (for updates).

    Raises:
        ConflictError: If a template with this name already exists.
    """
    query = select(PermissionTemplate).where(
        PermissionTemplate.owner_id == user_id,
        PermissionTemplate.name == name,
    )

    if exclude_id:
        query = query.where(PermissionTemplate.id != exclude_id)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        raise ConflictError(f"A permission template named '{name}' already exists")


# =============================================================================
# Permission Template Endpoints
# =============================================================================


@router.get(
    "",
    response_model=PermissionTemplateListResponse,
    summary="List permission templates",
    description="Get all custom permission templates for the current user.",
)
async def list_permission_templates(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PermissionTemplateListResponse:
    """
    List all permission templates for the current user.

    Returns custom templates created by the user, sorted by name.
    """
    result = await db.execute(
        select(PermissionTemplate)
        .where(PermissionTemplate.owner_id == current_user.id)
        .order_by(PermissionTemplate.name)
    )
    templates = list(result.scalars().all())

    template_responses = [_build_template_response(t) for t in templates]

    return PermissionTemplateListResponse(
        templates=template_responses,
        total=len(templates),
    )


@router.get(
    "/defaults",
    response_model=DefaultTemplatesResponse,
    summary="Get default templates",
    description="Get the built-in default permission templates.",
)
async def get_default_templates(
    current_user: CurrentUser,
) -> DefaultTemplatesResponse:
    """
    Get the built-in default permission templates.

    These are system-provided templates that users can use as a starting
    point or apply directly to team members.
    """
    from uuid import uuid4
    from datetime import datetime, timezone

    # Create response objects for default templates (with dummy IDs)
    templates = []
    for default in DEFAULT_TEMPLATES:
        templates.append(
            PermissionTemplateResponse(
                id=uuid4(),  # Generate a temporary ID
                owner_id=current_user.id,
                name=default["name"],
                description=default["description"],
                permissions=TemplatePermissions(**default["permissions"]),
                is_default=True,
                created_at=datetime.now(timezone.utc),
                updated_at=None,
            )
        )

    return DefaultTemplatesResponse(templates=templates)


@router.post(
    "",
    response_model=PermissionTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create permission template",
    description="Create a new custom permission template.",
)
async def create_permission_template(
    data: PermissionTemplateCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PermissionTemplateResponse:
    """
    Create a new custom permission template.

    The template can be applied to team members to quickly set their permissions.
    """
    # Check for name conflict
    await _check_name_conflict(db, current_user.id, data.name)

    # If setting as default, clear existing default
    if data.is_default:
        result = await db.execute(
            select(PermissionTemplate).where(
                PermissionTemplate.owner_id == current_user.id,
                PermissionTemplate.is_default,
            )
        )
        existing_defaults = result.scalars().all()
        for existing in existing_defaults:
            existing.is_default = False

    # Create the template
    template = PermissionTemplate(
        owner_id=current_user.id,
        name=data.name,
        description=data.description,
        permissions=data.permissions.model_dump(),
        is_default=data.is_default,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(f"Permission template created: id={template.id}, name={template.name}, owner={current_user.id}")

    return _build_template_response(template)


@router.get(
    "/{template_id}",
    response_model=PermissionTemplateResponse,
    summary="Get permission template",
    description="Get details of a specific permission template.",
)
async def get_permission_template(
    template_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PermissionTemplateResponse:
    """
    Get details of a specific permission template.

    Returns the template with its full permission configuration.
    """
    template = await _get_template_by_id(db, current_user.id, template_id)
    return _build_template_response(template)


@router.patch(
    "/{template_id}",
    response_model=PermissionTemplateResponse,
    summary="Update permission template",
    description="Update an existing permission template.",
)
async def update_permission_template(
    template_id: UUID,
    data: PermissionTemplateUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PermissionTemplateResponse:
    """
    Update an existing permission template.

    Only provided fields will be updated.
    """
    template = await _get_template_by_id(db, current_user.id, template_id)

    # Check for name conflict if name is being updated
    if data.name is not None and data.name != template.name:
        await _check_name_conflict(db, current_user.id, data.name, exclude_id=template_id)
        template.name = data.name

    if data.description is not None:
        template.description = data.description

    if data.permissions is not None:
        template.permissions = data.permissions.model_dump()

    if data.is_default is not None:
        if data.is_default and not template.is_default:
            # Clear existing default
            result = await db.execute(
                select(PermissionTemplate).where(
                    PermissionTemplate.owner_id == current_user.id,
                    PermissionTemplate.is_default,
                    PermissionTemplate.id != template_id,
                )
            )
            existing_defaults = result.scalars().all()
            for existing in existing_defaults:
                existing.is_default = False

        template.is_default = data.is_default

    await db.commit()
    await db.refresh(template)

    logger.info(f"Permission template updated: id={template_id}")

    return _build_template_response(template)


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete permission template",
    description="Delete a permission template.",
)
async def delete_permission_template(
    template_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete a permission template.

    This will not affect members who were assigned permissions using this
    template - their permissions will remain unchanged.
    """
    template = await _get_template_by_id(db, current_user.id, template_id)

    await db.delete(template)
    await db.commit()

    logger.info(f"Permission template deleted: id={template_id}")


@router.post(
    "/{template_id}/apply/{member_id}",
    response_model=ApplyTemplateResponse,
    summary="Apply template to member",
    description="Apply a permission template to a team member.",
)
async def apply_template_to_member(
    template_id: UUID,
    member_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ApplyTemplateResponse:
    """
    Apply a permission template to a team member.

    This will update the member's permissions to match the template.
    """
    # Get the template
    template = await _get_template_by_id(db, current_user.id, template_id)

    # Get the lab member
    result = await db.execute(
        select(LabMember).where(
            LabMember.id == member_id,
            LabMember.lab_owner_id == current_user.id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise NotFoundError("Team member", str(member_id))

    # Validate member status
    if member.invitation_status != "accepted":
        raise ValidationError("Cannot apply permissions to a member who has not accepted the invitation")

    # Apply the template permissions
    member.permissions = template.permissions
    member.permission_template_id = template.id

    await db.commit()
    await db.refresh(member)

    logger.info(f"Permission template applied: template={template_id}, member={member_id}")

    return ApplyTemplateResponse(
        success=True,
        message=f"Template '{template.name}' applied to team member",
        member_id=member_id,
        template_id=template_id,
        permissions=TemplatePermissions(**template.permissions),
    )
