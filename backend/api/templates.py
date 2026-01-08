"""
Document Templates API Endpoints
CRUD operations for reusable grant proposal templates.
"""
import logging
import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, func, or_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import Template, TemplateCategory
from backend.schemas.templates import (
    TemplateCategoryResponse,
    TemplateCreate,
    TemplateListResponse,
    TemplateRenderRequest,
    TemplateRenderResponse,
    TemplateResponse,
    TemplateUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Templates"])


# =============================================================================
# Categories
# =============================================================================

@router.get("/categories", response_model=List[TemplateCategoryResponse])
async def list_categories(
    db: AsyncSessionDep,
) -> List[TemplateCategoryResponse]:
    """Get all template categories with template counts."""
    result = await db.execute(
        select(TemplateCategory).order_by(TemplateCategory.display_order)
    )
    categories = result.scalars().all()

    # Get template counts per category
    count_result = await db.execute(
        select(Template.category_id, func.count(Template.id))
        .group_by(Template.category_id)
    )
    counts = dict(count_result.all())

    return [
        TemplateCategoryResponse(
            id=cat.id,
            name=cat.name,
            description=cat.description,
            display_order=cat.display_order,
            template_count=counts.get(cat.id, 0),
        )
        for cat in categories
    ]


# =============================================================================
# Templates CRUD
# =============================================================================

@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: CurrentUser,
    db: AsyncSessionDep,
    category_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    is_public: Optional[bool] = Query(None),
    is_system: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> TemplateListResponse:
    """
    List templates with filtering.

    Returns:
    - User's own templates
    - Public templates from other users
    - System templates (if requested)
    """
    # Base query - user's templates OR public templates OR system templates
    conditions = [
        Template.user_id == current_user.id,  # User's own
    ]

    if is_public is not False:
        conditions.append(and_(Template.is_public == True, Template.user_id != current_user.id))

    if is_system is not False:
        conditions.append(Template.is_system == True)

    query = select(Template).where(or_(*conditions))

    # Apply filters
    if category_id:
        query = query.where(Template.category_id == category_id)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                Template.title.ilike(search_pattern),
                Template.description.ilike(search_pattern),
            )
        )

    if is_public is not None:
        query = query.where(Template.is_public == is_public)

    if is_system is not None:
        query = query.where(Template.is_system == is_system)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query)

    # Apply pagination and ordering
    query = query.order_by(Template.updated_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    templates = result.scalars().all()

    return TemplateListResponse(
        items=[TemplateResponse.model_validate(t) for t in templates],
        total=total or 0,
    )


@router.post("", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template: TemplateCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> TemplateResponse:
    """Create a new template."""
    # Validate category exists if provided
    if template.category_id:
        result = await db.execute(
            select(TemplateCategory).where(TemplateCategory.id == template.category_id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Category not found")

    # Extract variables from content
    variables = template.variables or _extract_variables(template.content)

    new_template = Template(
        user_id=current_user.id,
        category_id=template.category_id,
        title=template.title,
        description=template.description,
        content=template.content,
        variables=variables,
        is_public=template.is_public or False,
        is_system=False,  # Users can't create system templates
    )

    db.add(new_template)
    await db.commit()
    await db.refresh(new_template)

    return TemplateResponse.model_validate(new_template)


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> TemplateResponse:
    """Get a single template by ID."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access: own template, public, or system
    if template.user_id != current_user.id and not template.is_public and not template.is_system:
        raise HTTPException(status_code=404, detail="Template not found")

    return TemplateResponse.model_validate(template)


@router.patch("/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    update: TemplateUpdate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> TemplateResponse:
    """Update a template."""
    result = await db.execute(
        select(Template).where(
            and_(
                Template.id == template_id,
                Template.user_id == current_user.id,
                Template.is_system == False,  # Can't edit system templates
            )
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or not editable")

    # Update fields
    update_data = update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(template, field, value)

    # Re-extract variables if content changed
    if "content" in update_data and "variables" not in update_data:
        template.variables = _extract_variables(template.content)

    template.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(template)

    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> None:
    """Delete a template."""
    result = await db.execute(
        select(Template).where(
            and_(
                Template.id == template_id,
                Template.user_id == current_user.id,
                Template.is_system == False,  # Can't delete system templates
            )
        )
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found or not deletable")

    await db.delete(template)
    await db.commit()


@router.post("/{template_id}/duplicate", response_model=TemplateResponse)
async def duplicate_template(
    template_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> TemplateResponse:
    """Duplicate a template to user's own templates."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access
    if original.user_id != current_user.id and not original.is_public and not original.is_system:
        raise HTTPException(status_code=404, detail="Template not found")

    # Create copy
    new_template = Template(
        user_id=current_user.id,
        category_id=original.category_id,
        title=f"{original.title} (Copy)",
        description=original.description,
        content=original.content,
        variables=original.variables,
        is_public=False,  # Copies are private by default
        is_system=False,
    )

    db.add(new_template)

    # Increment usage count on original
    original.usage_count += 1

    await db.commit()
    await db.refresh(new_template)

    return TemplateResponse.model_validate(new_template)


@router.post("/{template_id}/render", response_model=TemplateRenderResponse)
async def render_template(
    template_id: UUID,
    request: TemplateRenderRequest,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> TemplateRenderResponse:
    """Render a template with provided variables."""
    result = await db.execute(
        select(Template).where(Template.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # Check access
    if template.user_id != current_user.id and not template.is_public and not template.is_system:
        raise HTTPException(status_code=404, detail="Template not found")

    # Render template
    rendered = _render_template(template.content, request.variables)

    # Increment usage count
    template.usage_count += 1
    await db.commit()

    return TemplateRenderResponse(rendered_content=rendered)


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_variables(content: str) -> list:
    """
    Extract variables from template content.
    Variables are in format: {{variable_name}} or {{variable_name:type}}
    """
    pattern = r'\{\{(\w+)(?::(\w+))?\}\}'
    matches = re.findall(pattern, content)

    variables = []
    seen = set()

    for name, var_type in matches:
        if name not in seen:
            seen.add(name)
            variables.append({
                "name": name,
                "type": var_type or "text",
                "required": True,
            })

    return variables


def _render_template(content: str, variables: dict) -> str:
    """
    Render template by replacing variables with provided values.
    """
    result = content

    for key, value in variables.items():
        # Replace both {{key}} and {{key:type}} patterns
        result = re.sub(
            rf'\{{\{{{key}(?::\w+)?\}}\}}',
            str(value),
            result
        )

    return result
