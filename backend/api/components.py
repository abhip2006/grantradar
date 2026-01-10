"""
Document Component Library API Endpoints
CRUD operations for reusable document components and version control.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import and_, func, or_, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError
from backend.models import GrantApplication
from backend.models.components import ComponentUsage, DocumentComponent, DocumentVersion
from backend.schemas.components import (
    CategoryCount,
    CategoryListResponse,
    ComponentCreate,
    ComponentListResponse,
    ComponentResponse,
    ComponentUpdate,
    ComponentUsageCreate,
    ComponentUsageListResponse,
    ComponentUsageResponse,
    VersionCreate,
    VersionListResponse,
    VersionResponse,
)
from backend.schemas.common import PaginationInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/components", tags=["Components"])


# =============================================================================
# Helper Functions
# =============================================================================


def _build_component_response(component: DocumentComponent, usage_count: int = 0) -> ComponentResponse:
    """Build a ComponentResponse from a DocumentComponent model."""
    return ComponentResponse(
        id=component.id,
        user_id=component.user_id,
        category=component.category,
        name=component.name,
        description=component.description,
        content=component.content,
        metadata=component.metadata_,
        tags=component.tags,
        version=component.version,
        is_current=component.is_current,
        parent_id=component.parent_id,
        is_archived=component.is_archived,
        usage_count=usage_count,
        created_at=component.created_at,
        updated_at=component.updated_at,
    )


def _build_version_response(version: DocumentVersion, creator_name: Optional[str] = None) -> VersionResponse:
    """Build a VersionResponse from a DocumentVersion model."""
    return VersionResponse(
        id=version.id,
        kanban_card_id=version.kanban_card_id,
        section=version.section,
        version_number=version.version_number,
        content=version.content,
        snapshot_name=version.snapshot_name,
        change_summary=version.change_summary,
        file_path=version.file_path,
        file_size=version.file_size,
        file_type=version.file_type,
        created_by=version.created_by,
        created_by_name=creator_name,
        created_at=version.created_at,
    )


# =============================================================================
# Component Categories
# =============================================================================

CATEGORY_DESCRIPTIONS = {
    "facilities": "Laboratory and research facility descriptions",
    "equipment": "Equipment lists and specifications",
    "biosketch": "Biographical sketches and CVs",
    "boilerplate": "Standard text sections (human subjects, vertebrate animals, etc.)",
    "institution": "Institutional descriptions and capabilities",
    "other": "Other reusable content",
}


@router.get("/categories", response_model=CategoryListResponse)
async def list_categories(
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> CategoryListResponse:
    """
    Get all component categories with counts.

    Returns the list of available categories with the number of
    components the user has in each category.
    """
    # Get counts per category for user's components
    count_result = await db.execute(
        select(DocumentComponent.category, func.count(DocumentComponent.id))
        .where(
            and_(
                DocumentComponent.user_id == current_user.id,
                DocumentComponent.is_current,
                not DocumentComponent.is_archived,
            )
        )
        .group_by(DocumentComponent.category)
    )
    counts = dict(count_result.all())

    # Build response with all categories
    categories = [
        CategoryCount(
            category=cat,
            count=counts.get(cat, 0),
            description=desc,
        )
        for cat, desc in CATEGORY_DESCRIPTIONS.items()
    ]

    return CategoryListResponse(categories=categories)


# =============================================================================
# Component CRUD
# =============================================================================


@router.get("", response_model=ComponentListResponse)
async def list_components(
    current_user: CurrentUser,
    db: AsyncSessionDep,
    category: Optional[str] = Query(None, description="Filter by category"),
    search: Optional[str] = Query(None, max_length=100, description="Search in name and description"),
    tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    include_archived: bool = Query(False, description="Include archived components"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ComponentListResponse:
    """
    List user's document components with filtering.

    Returns paginated list of components owned by the current user.
    Uses a single optimized query with window function for total count
    and left join for usage counts to avoid N+1 queries.
    """
    # Create a subquery for usage counts per component
    usage_count_subq = (
        select(ComponentUsage.component_id, func.count(ComponentUsage.id).label("usage_count"))
        .group_by(ComponentUsage.component_id)
        .subquery()
    )

    # Build the main query with total count as a window function
    main_query = (
        select(
            DocumentComponent,
            func.coalesce(usage_count_subq.c.usage_count, 0).label("usage_count"),
            func.count(DocumentComponent.id).over().label("total_count"),
        )
        .outerjoin(usage_count_subq, DocumentComponent.id == usage_count_subq.c.component_id)
        .where(
            and_(
                DocumentComponent.user_id == current_user.id,
                DocumentComponent.is_current,
            )
        )
    )

    # Apply the same filters
    if not include_archived:
        main_query = main_query.where(not DocumentComponent.is_archived)

    if category:
        main_query = main_query.where(DocumentComponent.category == category)

    if search:
        search_pattern = f"%{search}%"
        main_query = main_query.where(
            or_(
                DocumentComponent.name.ilike(search_pattern),
                DocumentComponent.description.ilike(search_pattern),
            )
        )

    if tags:
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_list:
            for tag in tag_list:
                main_query = main_query.where(DocumentComponent.tags.contains([tag]))

    # Apply pagination and ordering
    main_query = main_query.order_by(DocumentComponent.updated_at.desc()).offset(offset).limit(limit)

    result = await db.execute(main_query)
    rows = result.all()

    # Extract total count from first row (if any), otherwise 0
    total = rows[0].total_count if rows else 0
    has_more = (offset + len(rows)) < total

    return ComponentListResponse(
        data=[_build_component_response(row[0], row.usage_count) for row in rows],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )


@router.post("", response_model=ComponentResponse, status_code=status.HTTP_201_CREATED)
async def create_component(
    component: ComponentCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentResponse:
    """Create a new document component."""
    new_component = DocumentComponent(
        user_id=current_user.id,
        category=component.category.value,
        name=component.name,
        description=component.description,
        content=component.content,
        metadata_=component.metadata,
        tags=component.tags,
        version=1,
        is_current=True,
        is_archived=False,
    )

    db.add(new_component)
    await db.commit()
    await db.refresh(new_component)

    logger.info(f"Created component {new_component.id} for user {current_user.id}")

    return _build_component_response(new_component, 0)


@router.get("/{component_id}", response_model=ComponentResponse)
async def get_component(
    component_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentResponse:
    """Get a single component by ID."""
    result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
            )
        )
    )
    component = result.scalar_one_or_none()

    if not component:
        raise NotFoundError("Component")

    # Get usage count
    usage_count_result = await db.execute(
        select(func.count(ComponentUsage.id)).where(ComponentUsage.component_id == component_id)
    )
    usage_count = usage_count_result.scalar() or 0

    return _build_component_response(component, usage_count)


@router.put("/{component_id}", response_model=ComponentResponse)
async def update_component(
    component_id: UUID,
    update: ComponentUpdate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentResponse:
    """
    Update a component (creates a new version).

    When content changes, a new version is created and the old version
    is marked as not current. For metadata-only changes, the component
    is updated in place.
    """
    result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
                DocumentComponent.is_current,
            )
        )
    )
    component = result.scalar_one_or_none()

    if not component:
        raise NotFoundError("Component")

    update_data = update.model_dump(exclude_unset=True)

    # Check if content is changing (requires new version)
    content_changed = "content" in update_data and update_data["content"] != component.content

    if content_changed:
        # Mark old version as not current
        component.is_current = False

        # Create new version
        new_component = DocumentComponent(
            user_id=current_user.id,
            category=update_data.get("category", component.category).value
            if isinstance(update_data.get("category"), type)
            else update_data.get("category", component.category),
            name=update_data.get("name", component.name),
            description=update_data.get("description", component.description),
            content=update_data["content"],
            metadata_=update_data.get("metadata", component.metadata_),
            tags=update_data.get("tags", component.tags),
            version=component.version + 1,
            is_current=True,
            parent_id=component.id,
            is_archived=False,
        )
        db.add(new_component)
        await db.commit()
        await db.refresh(new_component)

        logger.info(f"Created new version {new_component.version} for component {component_id}")

        return _build_component_response(new_component, 0)
    else:
        # Update in place (no content change)
        for field, value in update_data.items():
            if field == "category" and hasattr(value, "value"):
                value = value.value
            if field == "metadata":
                setattr(component, "metadata_", value)
            else:
                setattr(component, field, value)

        component.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(component)

        # Get usage count
        usage_count_result = await db.execute(
            select(func.count(ComponentUsage.id)).where(ComponentUsage.component_id == component_id)
        )
        usage_count = usage_count_result.scalar() or 0

        return _build_component_response(component, usage_count)


@router.delete("/{component_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_component(
    component_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
    permanent: bool = Query(False, description="Permanently delete instead of archive"),
) -> None:
    """
    Delete (archive) a component.

    By default, components are soft-deleted (archived). Use permanent=true
    to permanently delete the component and all its versions.
    """
    result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
            )
        )
    )
    component = result.scalar_one_or_none()

    if not component:
        raise NotFoundError("Component")

    if permanent:
        # Delete all versions in the chain
        await db.delete(component)
        logger.info(f"Permanently deleted component {component_id}")
    else:
        # Soft delete (archive)
        component.is_archived = True
        component.updated_at = datetime.now(timezone.utc)
        logger.info(f"Archived component {component_id}")

    await db.commit()


@router.post("/{component_id}/duplicate", response_model=ComponentResponse)
async def duplicate_component(
    component_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentResponse:
    """Duplicate a component to create a new independent copy."""
    result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
            )
        )
    )
    original = result.scalar_one_or_none()

    if not original:
        raise NotFoundError("Component")

    # Create copy
    new_component = DocumentComponent(
        user_id=current_user.id,
        category=original.category,
        name=f"{original.name} (Copy)",
        description=original.description,
        content=original.content,
        metadata_=original.metadata_,
        tags=original.tags,
        version=1,
        is_current=True,
        parent_id=None,  # New independent component
        is_archived=False,
    )

    db.add(new_component)
    await db.commit()
    await db.refresh(new_component)

    logger.info(f"Duplicated component {component_id} to {new_component.id}")

    return _build_component_response(new_component, 0)


# =============================================================================
# Component Usage in Applications
# =============================================================================


@router.post("/{component_id}/use/{card_id}", response_model=ComponentUsageResponse)
async def use_component_in_application(
    component_id: UUID,
    card_id: UUID,
    usage: ComponentUsageCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentUsageResponse:
    """
    Record usage of a component in a grant application.

    This endpoint tracks when a component is inserted into an application,
    enabling usage analytics and component-application relationship tracking.
    """
    # Verify component exists and belongs to user
    component_result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
                DocumentComponent.is_current,
                not DocumentComponent.is_archived,
            )
        )
    )
    component = component_result.scalar_one_or_none()

    if not component:
        raise NotFoundError("Component")

    # Verify kanban card exists and belongs to user
    card_result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    card = card_result.scalar_one_or_none()

    if not card:
        raise NotFoundError("Application")

    # Create usage record
    new_usage = ComponentUsage(
        component_id=component_id,
        kanban_card_id=card_id,
        section=usage.section,
        inserted_by=current_user.id,
    )

    db.add(new_usage)
    await db.commit()
    await db.refresh(new_usage)

    logger.info(f"Recorded usage of component {component_id} in application {card_id}")

    return ComponentUsageResponse(
        id=new_usage.id,
        component_id=new_usage.component_id,
        kanban_card_id=new_usage.kanban_card_id,
        section=new_usage.section,
        inserted_by=new_usage.inserted_by,
        used_at=new_usage.used_at,
        component_name=component.name,
        component_category=component.category,
    )


@router.get("/{component_id}/usages", response_model=ComponentUsageListResponse)
async def get_component_usages(
    component_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> ComponentUsageListResponse:
    """Get all applications where a component has been used."""
    # Verify component belongs to user
    component_result = await db.execute(
        select(DocumentComponent).where(
            and_(
                DocumentComponent.id == component_id,
                DocumentComponent.user_id == current_user.id,
            )
        )
    )
    component = component_result.scalar_one_or_none()

    if not component:
        raise NotFoundError("Component")

    # Get usages
    query = (
        select(ComponentUsage)
        .where(ComponentUsage.component_id == component_id)
        .order_by(ComponentUsage.used_at.desc())
    )

    # Get total count
    count_result = await db.execute(
        select(func.count(ComponentUsage.id)).where(ComponentUsage.component_id == component_id)
    )
    total = count_result.scalar() or 0

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    usages = result.scalars().all()

    has_more = (offset + len(usages)) < total

    return ComponentUsageListResponse(
        data=[
            ComponentUsageResponse(
                id=u.id,
                component_id=u.component_id,
                kanban_card_id=u.kanban_card_id,
                section=u.section,
                inserted_by=u.inserted_by,
                used_at=u.used_at,
                component_name=component.name,
                component_category=component.category,
            )
            for u in usages
        ],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )


# =============================================================================
# Document Versions
# =============================================================================

# Create a separate router for version endpoints under kanban
versions_router = APIRouter(prefix="/api/kanban", tags=["Kanban Versions"])


@versions_router.get("/{card_id}/versions", response_model=VersionListResponse)
async def get_document_versions(
    card_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
    section: Optional[str] = Query(None, description="Filter by section"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> VersionListResponse:
    """
    Get document version history for an application.

    Returns all version snapshots for the specified application,
    optionally filtered by section.
    """
    # Verify card belongs to user
    card_result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    card = card_result.scalar_one_or_none()

    if not card:
        raise NotFoundError("Application")

    # Build query
    query = select(DocumentVersion).where(DocumentVersion.kanban_card_id == card_id)

    if section:
        query = query.where(DocumentVersion.section == section)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination and ordering
    query = query.order_by(DocumentVersion.section, DocumentVersion.version_number.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    versions = result.scalars().all()

    has_more = (offset + len(versions)) < total

    return VersionListResponse(
        data=[_build_version_response(v) for v in versions],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=has_more,
        ),
    )


@versions_router.post("/{card_id}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version_snapshot(
    card_id: UUID,
    version_data: VersionCreate,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> VersionResponse:
    """
    Create a new version snapshot for an application document.

    Creates a numbered version snapshot that can be referenced later
    for comparison or restoration.
    """
    # Verify card belongs to user
    card_result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    card = card_result.scalar_one_or_none()

    if not card:
        raise NotFoundError("Application")

    # Get the next version number for this card/section combination
    max_version_result = await db.execute(
        select(func.coalesce(func.max(DocumentVersion.version_number), 0)).where(
            and_(
                DocumentVersion.kanban_card_id == card_id,
                DocumentVersion.section == version_data.section,
            )
        )
    )
    max_version = max_version_result.scalar() or 0
    next_version = max_version + 1

    # Create version
    new_version = DocumentVersion(
        kanban_card_id=card_id,
        section=version_data.section,
        version_number=next_version,
        content=version_data.content,
        snapshot_name=version_data.snapshot_name,
        change_summary=version_data.change_summary,
        created_by=current_user.id,
    )

    db.add(new_version)
    await db.commit()
    await db.refresh(new_version)

    logger.info(f"Created version {next_version} for card {card_id}, section '{version_data.section}'")

    return _build_version_response(new_version, current_user.name)


@versions_router.get("/{card_id}/versions/{version_id}", response_model=VersionResponse)
async def get_version(
    card_id: UUID,
    version_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> VersionResponse:
    """Get a specific version by ID."""
    # Verify card belongs to user
    card_result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    card = card_result.scalar_one_or_none()

    if not card:
        raise NotFoundError("Application")

    # Get version
    version_result = await db.execute(
        select(DocumentVersion).where(
            and_(
                DocumentVersion.id == version_id,
                DocumentVersion.kanban_card_id == card_id,
            )
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise NotFoundError("Version")

    return _build_version_response(version)


# =============================================================================
# Application Component Usage Endpoint
# =============================================================================


@versions_router.get("/{card_id}/components", response_model=ComponentUsageListResponse)
async def get_application_components(
    card_id: UUID,
    current_user: CurrentUser,
    db: AsyncSessionDep,
) -> ComponentUsageListResponse:
    """Get all components used in a specific application."""
    # Verify card belongs to user
    card_result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == card_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    card = card_result.scalar_one_or_none()

    if not card:
        raise NotFoundError("Application")

    # Get component usages with component details
    result = await db.execute(
        select(ComponentUsage, DocumentComponent)
        .join(DocumentComponent, ComponentUsage.component_id == DocumentComponent.id)
        .where(ComponentUsage.kanban_card_id == card_id)
        .order_by(ComponentUsage.used_at.desc())
    )
    rows = result.all()

    usages = [
        ComponentUsageResponse(
            id=usage.id,
            component_id=usage.component_id,
            kanban_card_id=usage.kanban_card_id,
            section=usage.section,
            inserted_by=usage.inserted_by,
            used_at=usage.used_at,
            component_name=component.name,
            component_category=component.category,
        )
        for usage, component in rows
    ]

    return ComponentUsageListResponse(
        data=usages,
        pagination=PaginationInfo(
            total=len(usages),
            offset=0,
            limit=len(usages),
            has_more=False,
        ),
    )
