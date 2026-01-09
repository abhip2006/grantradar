"""
Intelligence Graph API Endpoints
Grant mechanism data, funded projects, and competition metrics.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.models import CompetitionSnapshot, FundedProject, Grant, GrantMechanism
from backend.schemas.intelligence import (
    CompetitionData,
    CompetitionSnapshotResponse,
    FundedProjectSummary,
    MechanismDetail,
    MechanismListResponse,
    MechanismSummary,
    TopInstitute,
)
from backend.services.intelligence_graph import (
    count_funded_projects,
    create_competition_snapshot,
    get_all_mechanisms,
    get_competition_data_for_grant,
    get_funded_project_summaries,
    get_mechanism_by_code,
    get_mechanism_stats,
    get_top_funded_institutes,
)

router = APIRouter(prefix="/api/intelligence", tags=["Intelligence"])


# =============================================================================
# Mechanism Endpoints
# =============================================================================


@router.get(
    "/mechanisms",
    response_model=MechanismListResponse,
    summary="List all grant mechanisms",
    description="Get a list of all grant mechanisms with success rates and competition data.",
)
async def list_mechanisms(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    funding_agency: Optional[str] = Query(
        None, description="Filter by funding agency (e.g., NIH, NSF)"
    ),
    category: Optional[str] = Query(
        None, description="Filter by category (e.g., research, career, training)"
    ),
) -> MechanismListResponse:
    """
    Get all grant mechanisms with optional filtering.

    Returns mechanism codes, success rates, and competition levels.
    """
    mechanisms = await get_all_mechanisms(
        db,
        funding_agency=funding_agency,
        category=category,
    )

    summaries = [
        MechanismSummary(
            id=m.id,
            code=m.code,
            name=m.name,
            funding_agency=m.funding_agency,
            category=m.category,
            success_rate_overall=m.success_rate_overall,
            competition_level=m.competition_level,
        )
        for m in mechanisms
    ]

    return MechanismListResponse(
        mechanisms=summaries,
        total=len(summaries),
    )


@router.get(
    "/mechanisms/{code}",
    response_model=MechanismDetail,
    summary="Get mechanism details",
    description="Get detailed information about a specific grant mechanism.",
)
async def get_mechanism(
    code: str,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> MechanismDetail:
    """
    Get detailed information about a grant mechanism by code.

    Includes success rates, typical budgets, review criteria, and tips.
    """
    stats = await get_mechanism_stats(db, code)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mechanism '{code}' not found",
        )

    mechanism = await get_mechanism_by_code(db, code)
    if not mechanism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mechanism '{code}' not found",
        )

    # Convert tips from JSONB to list if needed
    tips_list = None
    if mechanism.tips:
        if isinstance(mechanism.tips, list):
            tips_list = mechanism.tips
        elif isinstance(mechanism.tips, dict) and "tips" in mechanism.tips:
            tips_list = mechanism.tips["tips"]

    return MechanismDetail(
        id=mechanism.id,
        code=mechanism.code,
        name=mechanism.name,
        description=mechanism.description,
        funding_agency=mechanism.funding_agency,
        category=mechanism.category,
        typical_duration_months=mechanism.typical_duration_months,
        typical_budget_min=mechanism.typical_budget_min,
        typical_budget_max=mechanism.typical_budget_max,
        success_rate_overall=mechanism.success_rate_overall,
        success_rate_new=mechanism.success_rate_new,
        success_rate_renewal=mechanism.success_rate_renewal,
        success_rate_resubmission=mechanism.success_rate_resubmission,
        avg_review_score_funded=mechanism.avg_review_score_funded,
        competition_level=mechanism.competition_level,
        estimated_applicants_per_cycle=mechanism.estimated_applicants_per_cycle,
        review_criteria=mechanism.review_criteria,
        eligibility_notes=mechanism.eligibility_notes,
        tips=tips_list,
        last_updated=mechanism.last_updated,
        funded_projects_count=stats.funded_projects_count,
        avg_award_amount=stats.avg_award_amount,
    )


@router.get(
    "/mechanisms/{code}/funded-projects",
    response_model=list[FundedProjectSummary],
    summary="Get funded projects for mechanism",
    description="Get a list of funded projects for a specific grant mechanism.",
)
async def get_mechanism_funded_projects(
    code: str,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(20, ge=1, le=100, description="Maximum results to return"),
) -> list[FundedProjectSummary]:
    """
    Get funded projects for a specific grant mechanism.

    Returns recent funded projects with PI and institution information.
    """
    # Verify mechanism exists
    mechanism = await get_mechanism_by_code(db, code)
    if not mechanism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mechanism '{code}' not found",
        )

    summaries = await get_funded_project_summaries(db, code, limit=limit)

    return [
        FundedProjectSummary(
            id=s.id,
            external_id=s.external_id,
            title=s.title,
            mechanism=s.mechanism,
            pi_name=s.pi_name,
            pi_institution=s.pi_institution,
            award_amount=s.award_amount,
            fiscal_year=s.fiscal_year,
            is_new=s.is_new,
        )
        for s in summaries
    ]


@router.get(
    "/mechanisms/{code}/top-institutions",
    response_model=list[TopInstitute],
    summary="Get top institutions for mechanism",
    description="Get institutions with the most funded projects for a mechanism.",
)
async def get_mechanism_top_institutions(
    code: str,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50, description="Maximum results to return"),
) -> list[TopInstitute]:
    """
    Get top institutions by funded project count for a mechanism.

    Useful for understanding which institutions have the most success.
    """
    # Verify mechanism exists
    mechanism = await get_mechanism_by_code(db, code)
    if not mechanism:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Mechanism '{code}' not found",
        )

    institutes = await get_top_funded_institutes(db, code, limit=limit)

    return [
        TopInstitute(
            institution=inst["institution"],
            funded_count=inst["funded_count"],
            total_funding=inst["total_funding"],
        )
        for inst in institutes
    ]


# =============================================================================
# Competition Endpoints
# =============================================================================


@router.get(
    "/competition/{grant_id}",
    response_model=CompetitionData,
    summary="Get competition data for a grant",
    description="Get competition metrics and analysis for a specific grant.",
)
async def get_grant_competition(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> CompetitionData:
    """
    Get competition data for a specific grant.

    Includes success rate, competition level, and contributing factors.
    """
    # Verify grant exists
    grant_result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found",
        )

    competition = await get_competition_data_for_grant(db, grant_id)
    if not competition:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competition data not available",
        )

    # Get mechanism details if available
    mechanism_summary = None
    if competition.mechanism_code:
        mechanism = await get_mechanism_by_code(db, competition.mechanism_code)
        if mechanism:
            mechanism_summary = MechanismSummary(
                id=mechanism.id,
                code=mechanism.code,
                name=mechanism.name,
                funding_agency=mechanism.funding_agency,
                category=mechanism.category,
                success_rate_overall=mechanism.success_rate_overall,
                competition_level=mechanism.competition_level,
            )

    return CompetitionData(
        grant_id=competition.grant_id,
        mechanism_code=competition.mechanism_code,
        competition_score=competition.competition_score,
        estimated_applicants=competition.estimated_applicants,
        similar_grants_count=competition.similar_grants_count,
        success_rate=competition.success_rate,
        competition_level=competition.competition_level,
        factors=competition.factors,
        mechanism=mechanism_summary,
    )


@router.post(
    "/competition/{grant_id}/snapshot",
    response_model=CompetitionSnapshotResponse,
    summary="Create competition snapshot",
    description="Create a new competition snapshot for a grant.",
)
async def create_grant_competition_snapshot(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> CompetitionSnapshotResponse:
    """
    Create a new competition snapshot for a grant.

    Calculates current competition metrics and stores them for tracking.
    """
    # Verify grant exists
    grant_result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found",
        )

    snapshot = await create_competition_snapshot(db, grant_id)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create competition snapshot",
        )

    return CompetitionSnapshotResponse(
        id=snapshot.id,
        grant_id=snapshot.grant_id,
        mechanism_id=snapshot.mechanism_id,
        snapshot_date=snapshot.snapshot_date,
        estimated_applicants=snapshot.estimated_applicants,
        similar_grants_count=snapshot.similar_grants_count,
        competition_score=snapshot.competition_score,
        factors=snapshot.factors,
        created_at=snapshot.created_at,
    )


@router.get(
    "/competition/{grant_id}/history",
    response_model=list[CompetitionSnapshotResponse],
    summary="Get competition snapshot history",
    description="Get historical competition snapshots for a grant.",
)
async def get_grant_competition_history(
    grant_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
    limit: int = Query(10, ge=1, le=50, description="Maximum snapshots to return"),
) -> list[CompetitionSnapshotResponse]:
    """
    Get historical competition snapshots for a grant.

    Shows how competition has changed over time.
    """
    # Verify grant exists
    grant_result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Grant not found",
        )

    # Get snapshots
    snapshot_result = await db.execute(
        select(CompetitionSnapshot)
        .where(CompetitionSnapshot.grant_id == grant_id)
        .order_by(CompetitionSnapshot.snapshot_date.desc())
        .limit(limit)
    )
    snapshots = snapshot_result.scalars().all()

    return [
        CompetitionSnapshotResponse(
            id=s.id,
            grant_id=s.grant_id,
            mechanism_id=s.mechanism_id,
            snapshot_date=s.snapshot_date,
            estimated_applicants=s.estimated_applicants,
            similar_grants_count=s.similar_grants_count,
            competition_score=s.competition_score,
            factors=s.factors,
            created_at=s.created_at,
        )
        for s in snapshots
    ]


# =============================================================================
# Funded Projects Endpoints
# =============================================================================


@router.get(
    "/funded-projects",
    response_model=list[FundedProjectSummary],
    summary="Search funded projects",
    description="Search funded projects with various filters.",
)
async def search_funded_projects(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    mechanism: Optional[str] = Query(None, description="Filter by mechanism code"),
    funding_institute: Optional[str] = Query(
        None, description="Filter by funding institute (e.g., NCI, NHLBI)"
    ),
    fiscal_year: Optional[int] = Query(None, description="Filter by fiscal year"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
) -> list[FundedProjectSummary]:
    """
    Search funded projects with optional filters.

    Returns funded project summaries matching the criteria.
    """
    query = select(FundedProject)

    if mechanism:
        query = query.where(FundedProject.mechanism == mechanism.upper())
    if funding_institute:
        query = query.where(FundedProject.funding_institute == funding_institute.upper())
    if fiscal_year:
        query = query.where(FundedProject.fiscal_year == fiscal_year)

    query = (
        query.order_by(FundedProject.award_date.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    projects = result.scalars().all()

    return [
        FundedProjectSummary(
            id=p.id,
            external_id=p.external_id,
            title=p.title,
            mechanism=p.mechanism,
            pi_name=p.pi_name,
            pi_institution=p.pi_institution,
            award_amount=p.award_amount,
            fiscal_year=p.fiscal_year,
            is_new=p.is_new,
        )
        for p in projects
    ]


@router.get(
    "/funded-projects/count",
    summary="Count funded projects",
    description="Get count of funded projects matching filters.",
)
async def count_funded_projects_endpoint(
    db: AsyncSessionDep,
    current_user: CurrentUser,
    mechanism: Optional[str] = Query(None, description="Filter by mechanism code"),
    funding_institute: Optional[str] = Query(
        None, description="Filter by funding institute"
    ),
    fiscal_year: Optional[int] = Query(None, description="Filter by fiscal year"),
) -> dict[str, int]:
    """
    Count funded projects matching filters.
    """
    count = await count_funded_projects(
        db,
        mechanism=mechanism,
        funding_institute=funding_institute,
        fiscal_year=fiscal_year,
    )

    return {"count": count}
