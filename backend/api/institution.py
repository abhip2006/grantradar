"""Institution API endpoints for multi-user portfolio views and institutional dashboard."""
import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.services.institution import InstitutionService
from backend.schemas.institution import (
    InstitutionCreate,
    InstitutionUpdate,
    InstitutionResponse,
    InstitutionsListResponse,
    InstitutionMemberCreate,
    InstitutionMemberUpdate,
    InstitutionMemberResponse,
    InstitutionMembersListResponse,
    InstitutionMemberPermissions,
    InstitutionSettings,
    PortfolioAggregation,
    InstitutionMetricsResponse,
    DepartmentListResponse,
    DepartmentStats,
    InstitutionDeadlinesResponse,
    DeadlineSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/institution",
    tags=["Institution"],
)


# =============================================================================
# Institution CRUD Endpoints
# =============================================================================


@router.post(
    "",
    response_model=InstitutionResponse,
    status_code=201,
    summary="Create institution",
    description="Create a new institution. Only admins can create institutions.",
)
async def create_institution(
    data: InstitutionCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionResponse:
    """
    Create a new institution.

    The creating user will automatically become the first admin of the institution.
    """
    service = InstitutionService(db)
    institution = await service.create_institution(
        data=data,
        created_by=current_user.id,
    )

    logger.info(f"Institution created: id={institution['id']}, name={institution['name']}, by={current_user.id}")

    settings = None
    if institution.get("settings"):
        settings = InstitutionSettings(**institution["settings"])

    return InstitutionResponse(
        id=institution["id"],
        name=institution["name"],
        type=institution["type"],
        domain=institution.get("domain"),
        description=institution.get("description"),
        logo_url=institution.get("logo_url"),
        website=institution.get("website"),
        address=institution.get("address"),
        settings=settings,
        created_by=institution.get("created_by"),
        created_at=institution["created_at"],
        updated_at=institution["updated_at"],
        member_count=institution.get("member_count", 1),
    )


@router.get(
    "/my-institutions",
    response_model=InstitutionsListResponse,
    summary="Get my institutions",
    description="Get all institutions the current user belongs to.",
)
async def get_my_institutions(
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionsListResponse:
    """
    Get all institutions the current user is a member of.
    """
    service = InstitutionService(db)
    institutions = await service.get_user_institutions(user_id=current_user.id)

    responses = []
    for inst in institutions:
        responses.append(InstitutionResponse(
            id=inst["id"],
            name=inst["name"],
            type=inst["type"],
            domain=inst.get("domain"),
            description=None,
            logo_url=inst.get("logo_url"),
            website=None,
            address=None,
            settings=None,
            created_by=None,
            created_at=None,
            updated_at=None,
            member_count=None,
        ))

    return InstitutionsListResponse(
        institutions=responses,
        total=len(responses),
    )


@router.get(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Get institution details",
    description="Get detailed information about an institution.",
)
async def get_institution(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionResponse:
    """
    Get institution details by ID.

    User must be a member of the institution to view details.
    """
    service = InstitutionService(db)

    # This will verify membership internally
    institution = await service.get_institution(institution_id)

    settings = None
    if institution.get("settings"):
        settings = InstitutionSettings(**institution["settings"])

    return InstitutionResponse(
        id=institution["id"],
        name=institution["name"],
        type=institution["type"],
        domain=institution.get("domain"),
        description=institution.get("description"),
        logo_url=institution.get("logo_url"),
        website=institution.get("website"),
        address=institution.get("address"),
        settings=settings,
        created_by=institution.get("created_by"),
        created_at=institution["created_at"],
        updated_at=institution["updated_at"],
        member_count=institution.get("member_count"),
    )


@router.patch(
    "/{institution_id}",
    response_model=InstitutionResponse,
    summary="Update institution",
    description="Update institution settings and details. Admin only.",
)
async def update_institution(
    institution_id: UUID,
    data: InstitutionUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionResponse:
    """
    Update an institution's details.

    Only admins of the institution can update it.
    """
    service = InstitutionService(db)
    institution = await service.update_institution(
        institution_id=institution_id,
        data=data,
        user_id=current_user.id,
    )

    logger.info(f"Institution updated: id={institution_id}, by={current_user.id}")

    settings = None
    if institution.get("settings"):
        settings = InstitutionSettings(**institution["settings"])

    return InstitutionResponse(
        id=institution["id"],
        name=institution["name"],
        type=institution["type"],
        domain=institution.get("domain"),
        description=institution.get("description"),
        logo_url=institution.get("logo_url"),
        website=institution.get("website"),
        address=institution.get("address"),
        settings=settings,
        created_by=institution.get("created_by"),
        created_at=institution["created_at"],
        updated_at=institution["updated_at"],
        member_count=institution.get("member_count"),
    )


@router.delete(
    "/{institution_id}",
    status_code=204,
    summary="Delete institution",
    description="Delete an institution. Admin only.",
)
async def delete_institution(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Delete an institution.

    Only admins can delete an institution. This will also remove all members.
    """
    service = InstitutionService(db)
    await service.delete_institution(
        institution_id=institution_id,
        user_id=current_user.id,
    )

    logger.info(f"Institution deleted: id={institution_id}, by={current_user.id}")


# =============================================================================
# Member Endpoints
# =============================================================================


@router.get(
    "/{institution_id}/members",
    response_model=InstitutionMembersListResponse,
    summary="List institution members",
    description="Get all members of an institution with optional filtering.",
)
async def list_members(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    department: Optional[str] = Query(None, description="Filter by department"),
    role: Optional[str] = Query(None, description="Filter by role"),
) -> InstitutionMembersListResponse:
    """
    List all members of an institution.

    User must be a member of the institution to view the member list.
    """
    service = InstitutionService(db)
    members, total, by_department, by_role = await service.list_members(
        institution_id=institution_id,
        user_id=current_user.id,
        department=department,
        role=role,
    )

    member_responses = []
    for m in members:
        permissions = None
        if m.get("permissions"):
            permissions = InstitutionMemberPermissions(**m["permissions"])

        member_responses.append(InstitutionMemberResponse(
            id=m["id"],
            institution_id=m["institution_id"],
            user_id=m["user_id"],
            role=m["role"],
            department=m.get("department"),
            title=m.get("title"),
            permissions=permissions,
            added_at=m["added_at"],
            added_by=m.get("added_by"),
            updated_at=m["updated_at"],
            user_name=m.get("user_name"),
            user_email=m.get("user_email"),
        ))

    return InstitutionMembersListResponse(
        members=member_responses,
        total=total,
        by_department=by_department,
        by_role=by_role,
    )


@router.post(
    "/{institution_id}/members",
    response_model=InstitutionMemberResponse,
    status_code=201,
    summary="Add institution member",
    description="Add a member to the institution.",
)
async def add_member(
    institution_id: UUID,
    data: InstitutionMemberCreate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionMemberResponse:
    """
    Add a new member to an institution.

    Only admins and managers with member management permission can add members.
    """
    service = InstitutionService(db)
    member = await service.add_member(
        institution_id=institution_id,
        data=data,
        added_by=current_user.id,
    )

    logger.info(f"Member added to institution: institution={institution_id}, user={member['user_id']}, by={current_user.id}")

    permissions = None
    if member.get("permissions"):
        permissions = InstitutionMemberPermissions(**member["permissions"])

    return InstitutionMemberResponse(
        id=member["id"],
        institution_id=member["institution_id"],
        user_id=member["user_id"],
        role=member["role"],
        department=member.get("department"),
        title=member.get("title"),
        permissions=permissions,
        added_at=member["added_at"],
        added_by=member.get("added_by"),
        updated_at=member["updated_at"],
        user_name=member.get("user_name"),
        user_email=member.get("user_email"),
    )


@router.patch(
    "/{institution_id}/members/{member_id}",
    response_model=InstitutionMemberResponse,
    summary="Update institution member",
    description="Update a member's role, department, or permissions.",
)
async def update_member(
    institution_id: UUID,
    member_id: UUID,
    data: InstitutionMemberUpdate,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionMemberResponse:
    """
    Update a member's role or details.

    Only admins and managers with member management permission can update members.
    """
    service = InstitutionService(db)
    member = await service.update_member(
        institution_id=institution_id,
        member_id=member_id,
        data=data,
        actor_id=current_user.id,
    )

    logger.info(f"Member updated: institution={institution_id}, member={member_id}, by={current_user.id}")

    permissions = None
    if member.get("permissions"):
        permissions = InstitutionMemberPermissions(**member["permissions"])

    return InstitutionMemberResponse(
        id=member["id"],
        institution_id=member["institution_id"],
        user_id=member["user_id"],
        role=member["role"],
        department=member.get("department"),
        title=member.get("title"),
        permissions=permissions,
        added_at=member["added_at"],
        added_by=member.get("added_by"),
        updated_at=member["updated_at"],
        user_name=member.get("user_name"),
        user_email=member.get("user_email"),
    )


@router.delete(
    "/{institution_id}/members/{user_id}",
    status_code=204,
    summary="Remove institution member",
    description="Remove a member from the institution.",
)
async def remove_member(
    institution_id: UUID,
    user_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> None:
    """
    Remove a member from an institution.

    Only admins and managers with member management permission can remove members.
    Cannot remove the last admin.
    """
    service = InstitutionService(db)
    await service.remove_member(
        institution_id=institution_id,
        user_id=user_id,
        actor_id=current_user.id,
    )

    logger.info(f"Member removed from institution: institution={institution_id}, user={user_id}, by={current_user.id}")


# =============================================================================
# Portfolio Endpoints
# =============================================================================


@router.get(
    "/{institution_id}/portfolio",
    response_model=PortfolioAggregation,
    summary="Get institution portfolio",
    description="Get aggregated portfolio view across all institution members.",
)
async def get_portfolio(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    department: Optional[str] = Query(None, description="Filter by department"),
) -> PortfolioAggregation:
    """
    Get aggregated portfolio view.

    Shows all grants being tracked across institution members with
    breakdown by stage, department, and upcoming deadlines.
    """
    service = InstitutionService(db)
    portfolio = await service.get_portfolio(
        institution_id=institution_id,
        user_id=current_user.id,
        department=department,
    )

    return portfolio


# =============================================================================
# Metrics Endpoints
# =============================================================================


@router.get(
    "/{institution_id}/metrics",
    response_model=InstitutionMetricsResponse,
    summary="Get institution metrics",
    description="Get institution-wide metrics and success rate benchmarks.",
)
async def get_metrics(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> InstitutionMetricsResponse:
    """
    Get institution-wide metrics.

    Includes success rates, pipeline metrics, and trends.
    """
    service = InstitutionService(db)
    metrics = await service.get_metrics(
        institution_id=institution_id,
        user_id=current_user.id,
    )

    return InstitutionMetricsResponse(**metrics)


# =============================================================================
# Department Endpoints
# =============================================================================


@router.get(
    "/{institution_id}/departments",
    response_model=DepartmentListResponse,
    summary="List departments with stats",
    description="Get all departments in the institution with their statistics.",
)
async def list_departments(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> DepartmentListResponse:
    """
    List all departments with their statistics.

    Shows member count, grants tracked, success rates, and funding for each department.
    """
    service = InstitutionService(db)
    departments, total = await service.get_departments(
        institution_id=institution_id,
        user_id=current_user.id,
    )

    return DepartmentListResponse(
        departments=departments,
        total_departments=total,
    )


# =============================================================================
# Deadline Endpoints
# =============================================================================


@router.get(
    "/{institution_id}/deadlines",
    response_model=InstitutionDeadlinesResponse,
    summary="Get upcoming deadlines",
    description="Get all upcoming deadlines across institution members.",
)
async def get_deadlines(
    institution_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    days_ahead: int = Query(90, ge=1, le=365, description="Days ahead to look for deadlines"),
    department: Optional[str] = Query(None, description="Filter by department"),
) -> InstitutionDeadlinesResponse:
    """
    Get all upcoming deadlines across institution members.

    Returns deadlines sorted by due date with summary counts.
    """
    service = InstitutionService(db)
    deadlines, stats = await service.get_deadlines(
        institution_id=institution_id,
        user_id=current_user.id,
        days_ahead=days_ahead,
        department=department,
    )

    return InstitutionDeadlinesResponse(
        deadlines=deadlines,
        total=stats["total"],
        overdue_count=stats["overdue_count"],
        due_this_week=stats["due_this_week"],
        due_this_month=stats["due_this_month"],
    )
