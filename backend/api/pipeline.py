"""
Pipeline API Endpoints
Track grant applications through stages: Researching -> Writing -> Submitted -> Awarded/Rejected
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import ApplicationStage, Grant, GrantApplication
from backend.schemas.pipeline import (
    ApplicationStageEnum,
    GrantSummary,
    PipelineItemCreate,
    PipelineItemMove,
    PipelineItemResponse,
    PipelineItemUpdate,
    PipelineResponse,
    PipelineStageGroup,
    PipelineStats,
)

router = APIRouter(prefix="/api/pipeline", tags=["Pipeline"])


def compute_days_until(target_date: Optional[datetime]) -> Optional[int]:
    """Compute days until a target date (negative if past)."""
    if not target_date:
        return None
    now = datetime.now(timezone.utc)
    # Make target_date timezone-aware if needed
    if target_date.tzinfo is None:
        target_date = target_date.replace(tzinfo=timezone.utc)
    delta = target_date - now
    return delta.days


def application_to_response(app: GrantApplication) -> PipelineItemResponse:
    """Convert a GrantApplication model to a response schema."""
    grant_summary = GrantSummary(
        id=app.grant.id,
        title=app.grant.title,
        agency=app.grant.agency,
        deadline=app.grant.deadline,
        amount_min=app.grant.amount_min,
        amount_max=app.grant.amount_max,
        url=app.grant.url,
    )

    return PipelineItemResponse(
        id=app.id,
        user_id=app.user_id,
        grant_id=app.grant_id,
        match_id=app.match_id,
        stage=ApplicationStageEnum(app.stage.value),
        notes=app.notes,
        target_date=app.target_date,
        created_at=app.created_at,
        updated_at=app.updated_at,
        grant=grant_summary,
        days_until_deadline=compute_days_until(app.grant.deadline),
        days_until_target=compute_days_until(app.target_date),
    )


@router.get(
    "",
    response_model=PipelineResponse,
    summary="Get pipeline",
    description="Get all pipeline items grouped by stage.",
)
async def get_pipeline(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineResponse:
    """
    Get all grant applications in the user's pipeline grouped by stage.

    Returns items organized into stage columns for Kanban display.
    """
    # Fetch all pipeline items with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
        .order_by(GrantApplication.updated_at.desc())
    )
    applications = result.unique().scalars().all()

    # Group by stage
    stage_groups: dict[ApplicationStageEnum, list[PipelineItemResponse]] = {stage: [] for stage in ApplicationStageEnum}

    for app in applications:
        response = application_to_response(app)
        stage_groups[response.stage].append(response)

    # Build response
    stages = [
        PipelineStageGroup(
            stage=stage,
            items=items,
            count=len(items),
        )
        for stage, items in stage_groups.items()
    ]

    return PipelineResponse(
        stages=stages,
        total=len(applications),
    )


@router.get(
    "/stats",
    response_model=PipelineStats,
    summary="Get pipeline stats",
    description="Get statistics about the pipeline.",
)
async def get_pipeline_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineStats:
    """
    Get summary statistics for the user's pipeline.
    """
    # Fetch all pipeline items with grant data
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.user_id == current_user.id)
    )
    applications = result.unique().scalars().all()

    # Count by stage
    by_stage: dict[str, int] = {stage.value: 0 for stage in ApplicationStageEnum}
    upcoming_deadlines = 0
    past_deadlines = 0
    now = datetime.now(timezone.utc)

    for app in applications:
        by_stage[app.stage.value] += 1

        if app.grant.deadline:
            deadline = app.grant.deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)

            days_until = (deadline - now).days

            if days_until < 0:
                past_deadlines += 1
            elif days_until <= 14:
                upcoming_deadlines += 1

    return PipelineStats(
        total=len(applications),
        by_stage=by_stage,
        upcoming_deadlines=upcoming_deadlines,
        past_deadlines=past_deadlines,
    )


@router.post(
    "",
    response_model=PipelineItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add to pipeline",
    description="Add a grant to the application pipeline.",
)
async def add_to_pipeline(
    item: PipelineItemCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineItemResponse:
    """
    Add a grant to the user's application pipeline.

    Starts in the specified stage (default: researching).
    """
    # Check if grant exists
    grant_result = await db.execute(select(Grant).where(Grant.id == item.grant_id))
    grant = grant_result.scalar_one_or_none()

    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found",
        )

    # Check if already in pipeline
    existing = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.user_id == current_user.id,
                GrantApplication.grant_id == item.grant_id,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Grant is already in your pipeline",
        )

    # Create pipeline item
    application = GrantApplication(
        user_id=current_user.id,
        grant_id=item.grant_id,
        match_id=item.match_id,
        stage=ApplicationStage(item.stage.value),
        notes=item.notes,
        target_date=item.target_date,
    )

    db.add(application)
    await db.flush()
    await db.refresh(application)

    # Load grant relationship
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(GrantApplication.id == application.id)
    )
    application = result.unique().scalar_one()

    return application_to_response(application)


@router.get(
    "/{item_id}",
    response_model=PipelineItemResponse,
    summary="Get pipeline item",
    description="Get details of a specific pipeline item.",
)
async def get_pipeline_item(
    item_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineItemResponse:
    """
    Get a specific pipeline item by ID.
    """
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.id == item_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.unique().scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline item not found",
        )

    return application_to_response(application)


@router.put(
    "/{item_id}",
    response_model=PipelineItemResponse,
    summary="Update pipeline item",
    description="Update a pipeline item's stage, notes, or target date.",
)
async def update_pipeline_item(
    item_id: UUID,
    update: PipelineItemUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineItemResponse:
    """
    Update a pipeline item.

    Can update stage, notes, and target date.
    """
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.id == item_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.unique().scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline item not found",
        )

    # Update fields
    if update.stage is not None:
        application.stage = ApplicationStage(update.stage.value)

    if update.notes is not None:
        application.notes = update.notes

    if update.target_date is not None:
        application.target_date = update.target_date

    application.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(application)

    return application_to_response(application)


@router.put(
    "/{item_id}/move",
    response_model=PipelineItemResponse,
    summary="Move pipeline item",
    description="Move a pipeline item to a different stage.",
)
async def move_pipeline_item(
    item_id: UUID,
    move: PipelineItemMove,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> PipelineItemResponse:
    """
    Move a pipeline item to a different stage.

    Used for drag-and-drop Kanban functionality.
    """
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.id == item_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.unique().scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline item not found",
        )

    # Update stage
    application.stage = ApplicationStage(move.stage.value)
    application.updated_at = datetime.now(timezone.utc)

    await db.flush()
    await db.refresh(application)

    return application_to_response(application)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove from pipeline",
    description="Remove a grant from the pipeline.",
)
async def remove_from_pipeline(
    item_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Remove a grant from the user's pipeline.
    """
    result = await db.execute(
        select(GrantApplication).where(
            and_(
                GrantApplication.id == item_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.scalar_one_or_none()

    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline item not found",
        )

    await db.delete(application)
    await db.flush()


@router.get(
    "/grant/{grant_id}",
    response_model=Optional[PipelineItemResponse],
    summary="Get pipeline item by grant",
    description="Check if a grant is in the pipeline and get its details.",
)
async def get_pipeline_item_by_grant(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> Optional[PipelineItemResponse]:
    """
    Check if a grant is in the user's pipeline.

    Returns the pipeline item if found, or null if not in pipeline.
    """
    result = await db.execute(
        select(GrantApplication)
        .options(joinedload(GrantApplication.grant))
        .where(
            and_(
                GrantApplication.grant_id == grant_id,
                GrantApplication.user_id == current_user.id,
            )
        )
    )
    application = result.unique().scalar_one_or_none()

    if not application:
        return None

    return application_to_response(application)
