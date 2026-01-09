"""
Compliance Engine API Endpoints

Endpoints for managing compliance requirements, tasks, and templates.
Helps researchers stay compliant with funder requirements after grants are awarded.
"""
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Query, status
from sqlalchemy import text

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.core.exceptions import NotFoundError, ValidationError
from backend.schemas.common import PaginationInfo
from backend.schemas.compliance_engine import (
    ComplianceChecklist,
    ComplianceTaskComplete,
    ComplianceTaskCreate,
    ComplianceTaskList,
    ComplianceTaskResponse,
    ComplianceTaskStatus,
    ComplianceTaskUpdate,
    ComplianceTemplateList,
    ComplianceTemplateResponse,
    FunderRequirementCreate,
    FunderRequirementList,
    FunderRequirementResponse,
    GenerateComplianceTasksRequest,
    GenerateComplianceTasksResponse,
    RequirementType,
    UpcomingDeadline,
    UpcomingDeadlinesList,
)
from backend.services.compliance_engine import ComplianceEngineService

router = APIRouter(prefix="/api/compliance-engine", tags=["Compliance Engine"])


# =============================================================================
# Funder Requirements Endpoints
# =============================================================================


@router.get(
    "/requirements",
    response_model=FunderRequirementList,
    summary="List all funder requirements",
    description="Get all compliance requirements from all funders with optional filtering.",
)
async def list_requirements(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: Optional[str] = Query(None, description="Filter by funder name"),
    requirement_type: Optional[RequirementType] = Query(None, description="Filter by requirement type"),
    is_active: bool = Query(True, description="Filter by active status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
) -> FunderRequirementList:
    """
    List all funder compliance requirements.

    Filter by funder name, requirement type, and active status.
    """
    service = ComplianceEngineService(db)

    requirements, total = await service.get_all_requirements(
        funder_name=funder,
        requirement_type=requirement_type.value if requirement_type else None,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    return FunderRequirementList(
        data=[FunderRequirementResponse(**r) for r in requirements],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + len(requirements)) < total,
        ),
    )


@router.get(
    "/requirements/{funder}",
    response_model=List[FunderRequirementResponse],
    summary="Get requirements for a funder",
    description="Get all compliance requirements for a specific funder.",
)
async def get_funder_requirements(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: str,
    mechanism: Optional[str] = Query(None, description="Filter by grant mechanism"),
) -> List[FunderRequirementResponse]:
    """
    Get all compliance requirements for a specific funder.

    Optionally filter by grant mechanism (e.g., R01, R21 for NIH).
    """
    service = ComplianceEngineService(db)
    requirements = await service.get_requirements_for_funder(funder, mechanism)

    if not requirements:
        raise NotFoundError("Requirements for funder", funder)

    return [FunderRequirementResponse(**r) for r in requirements]


@router.post(
    "/requirements",
    response_model=FunderRequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create funder requirement",
    description="Create a new funder compliance requirement (admin only).",
)
async def create_requirement(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: FunderRequirementCreate,
) -> FunderRequirementResponse:
    """
    Create a new funder compliance requirement.

    Note: In production, this should be restricted to admin users.
    """
    service = ComplianceEngineService(db)
    requirement = await service.create_requirement(data.model_dump())
    return FunderRequirementResponse(**requirement)


# =============================================================================
# Compliance Tasks Endpoints
# =============================================================================


@router.get(
    "/tasks",
    response_model=ComplianceTaskList,
    summary="Get user's compliance tasks",
    description="Get all compliance tasks for the current user.",
)
async def get_compliance_tasks(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    status_filter: Optional[ComplianceTaskStatus] = Query(
        None, alias="status", description="Filter by task status"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
) -> ComplianceTaskList:
    """
    Get all compliance tasks for the current user.

    Optionally filter by task status (pending, in_progress, completed, overdue).
    """
    service = ComplianceEngineService(db)

    tasks, total = await service.get_user_tasks(
        user_id=current_user.id,
        status=status_filter.value if status_filter else None,
        limit=limit,
        offset=offset,
    )

    return ComplianceTaskList(
        data=[ComplianceTaskResponse(**t) for t in tasks],
        pagination=PaginationInfo(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + len(tasks)) < total,
        ),
    )


@router.get(
    "/tasks/upcoming",
    response_model=UpcomingDeadlinesList,
    summary="Get upcoming compliance deadlines",
    description="Get upcoming compliance deadlines for the current user.",
)
async def get_upcoming_tasks(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    days: int = Query(30, ge=1, le=365, description="Days to look ahead"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
) -> UpcomingDeadlinesList:
    """
    Get upcoming compliance deadlines for the current user.

    Returns tasks due within the specified number of days.
    """
    service = ComplianceEngineService(db)
    tasks = await service.get_upcoming_tasks(
        user_id=current_user.id,
        days_ahead=days,
        limit=limit,
    )

    deadlines = [
        UpcomingDeadline(
            task_id=t["task_id"],
            title=t["title"],
            due_date=t["due_date"],
            days_until_due=t["days_until_due"] or 0,
            status=ComplianceTaskStatus(t["status"]),
            grant_title=t.get("grant_title"),
            funder_name=t.get("funder_name"),
            requirement_type=RequirementType(t["requirement_type"]) if t.get("requirement_type") else None,
        )
        for t in tasks
    ]

    return UpcomingDeadlinesList(
        data=deadlines,
        total=len(deadlines),
    )


@router.post(
    "/tasks",
    response_model=ComplianceTaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create compliance task",
    description="Create a new compliance task manually.",
)
async def create_task(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: ComplianceTaskCreate,
) -> ComplianceTaskResponse:
    """
    Create a new compliance task manually.

    Use this to add custom compliance tasks not auto-generated from requirements.
    """
    service = ComplianceEngineService(db)
    task = await service.create_task(current_user.id, data.model_dump())
    return ComplianceTaskResponse(**task)


@router.post(
    "/tasks/{task_id}/complete",
    response_model=ComplianceTaskResponse,
    summary="Mark task complete",
    description="Mark a compliance task as completed.",
)
async def complete_task(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    task_id: UUID,
    data: Optional[ComplianceTaskComplete] = None,
) -> ComplianceTaskResponse:
    """
    Mark a compliance task as completed.

    Optionally add completion notes.
    """
    service = ComplianceEngineService(db)
    task = await service.complete_task(
        task_id=task_id,
        user_id=current_user.id,
        notes=data.notes if data else None,
    )

    if not task:
        raise NotFoundError("Compliance task")

    return ComplianceTaskResponse(**task)


@router.patch(
    "/tasks/{task_id}",
    response_model=ComplianceTaskResponse,
    summary="Update task status",
    description="Update a compliance task's status.",
)
async def update_task_status(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    task_id: UUID,
    data: ComplianceTaskUpdate,
) -> ComplianceTaskResponse:
    """
    Update a compliance task's status or details.
    """
    if data.status is None:
        raise ValidationError("Status is required for update")

    service = ComplianceEngineService(db)
    task = await service.update_task_status(
        task_id=task_id,
        user_id=current_user.id,
        status=data.status.value,
    )

    if not task:
        raise NotFoundError("Compliance task")

    return ComplianceTaskResponse(**task)


# =============================================================================
# Compliance Checklist Endpoints
# =============================================================================


@router.get(
    "/checklist/{grant_id}",
    response_model=ComplianceChecklist,
    summary="Get compliance checklist",
    description="Get compliance checklist for a specific grant.",
)
async def get_compliance_checklist(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    grant_id: UUID,
) -> ComplianceChecklist:
    """
    Get compliance checklist for a specific grant.

    Returns all compliance requirements for the grant's funder
    along with task status for each requirement.
    """
    service = ComplianceEngineService(db)
    checklist = await service.get_compliance_checklist(
        user_id=current_user.id,
        grant_id=grant_id,
    )

    if "error" in checklist:
        raise NotFoundError("Grant")

    return ComplianceChecklist(**checklist)


# =============================================================================
# Compliance Templates Endpoints
# =============================================================================


@router.get(
    "/templates/{funder}",
    response_model=List[ComplianceTemplateResponse],
    summary="Get compliance templates",
    description="Get compliance templates for a specific funder.",
)
async def get_compliance_templates(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funder: str,
    mechanism: Optional[str] = Query(None, description="Filter by grant mechanism"),
) -> List[ComplianceTemplateResponse]:
    """
    Get compliance templates for a specific funder.

    Templates include document structures for progress reports,
    financial reports, and data management plans.
    """
    service = ComplianceEngineService(db)
    templates = await service.get_templates_for_funder(funder, mechanism)

    return [ComplianceTemplateResponse(**t) for t in templates]


# =============================================================================
# Generate Tasks Endpoint
# =============================================================================


@router.post(
    "/generate-tasks",
    response_model=GenerateComplianceTasksResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate compliance tasks",
    description="Auto-generate compliance tasks when a grant is awarded.",
)
async def generate_compliance_tasks(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    data: GenerateComplianceTasksRequest,
) -> GenerateComplianceTasksResponse:
    """
    Auto-generate compliance tasks when a grant is awarded.

    This creates all relevant compliance tasks based on the funder's
    requirements and the award date. Tasks are scheduled based on
    requirement frequency (one-time, quarterly, annual, final).
    """
    service = ComplianceEngineService(db)

    tasks = await service.generate_compliance_tasks(
        user_id=current_user.id,
        application_id=data.application_id,
        award_date=data.award_date,
        funder_name=data.funder_name,
        mechanism=data.mechanism,
    )

    # Convert to response format
    task_responses = []
    for task in tasks:
        # Fetch full task data
        result = await db.execute(
            text("""
                SELECT
                    *,
                    CASE WHEN status != 'completed' AND due_date < NOW() THEN true ELSE false END as is_overdue,
                    EXTRACT(DAY FROM due_date - NOW())::integer as days_until_due
                FROM compliance_tasks WHERE id = :id
            """),
            {"id": task["id"]}
        )
        row = result.fetchone()
        if row:
            task_responses.append(ComplianceTaskResponse(**dict(row._mapping)))

    return GenerateComplianceTasksResponse(
        tasks_created=len(tasks),
        tasks=task_responses,
    )


# =============================================================================
# Utility Endpoints
# =============================================================================


@router.get(
    "/funders",
    response_model=List[str],
    summary="List available funders",
    description="Get list of funders with compliance requirements.",
)
async def list_funders(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> List[str]:
    """
    Get list of all funders that have compliance requirements defined.
    """
    result = await db.execute(
        text("""
            SELECT DISTINCT funder_name
            FROM funder_requirements
            WHERE is_active = true
            ORDER BY funder_name
        """)
    )
    return [row[0] for row in result.fetchall()]


@router.get(
    "/stats",
    summary="Get compliance statistics",
    description="Get compliance task statistics for the current user.",
)
async def get_compliance_stats(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> dict:
    """
    Get compliance statistics for the current user.

    Returns counts of tasks by status and upcoming deadlines.
    """
    result = await db.execute(
        text("""
            SELECT
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                COUNT(*) FILTER (WHERE status = 'in_progress') as in_progress_count,
                COUNT(*) FILTER (WHERE status = 'completed') as completed_count,
                COUNT(*) FILTER (WHERE status = 'overdue') as overdue_count,
                COUNT(*) FILTER (WHERE status NOT IN ('completed') AND due_date BETWEEN NOW() AND NOW() + INTERVAL '7 days') as due_this_week,
                COUNT(*) FILTER (WHERE status NOT IN ('completed') AND due_date BETWEEN NOW() AND NOW() + INTERVAL '30 days') as due_this_month,
                COUNT(*) as total
            FROM compliance_tasks
            WHERE user_id = :user_id
        """),
        {"user_id": current_user.id}
    )

    row = result.fetchone()

    return {
        "pending": row[0] or 0,
        "in_progress": row[1] or 0,
        "completed": row[2] or 0,
        "overdue": row[3] or 0,
        "due_this_week": row[4] or 0,
        "due_this_month": row[5] or 0,
        "total": row[6] or 0,
    }
