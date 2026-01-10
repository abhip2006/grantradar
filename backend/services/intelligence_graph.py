"""
Intelligence Graph Service
Functions for querying funded projects, mechanisms, and competition data.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import (
    CompetitionSnapshot,
    FundedProject,
    Grant,
    GrantMechanism,
)


@dataclass
class MechanismStats:
    """Statistics for a grant mechanism."""

    code: str
    name: str
    funding_agency: Optional[str]
    category: Optional[str]
    success_rate_overall: Optional[float]
    success_rate_new: Optional[float]
    success_rate_renewal: Optional[float]
    competition_level: Optional[str]
    typical_budget_min: Optional[int]
    typical_budget_max: Optional[int]
    funded_projects_count: int
    avg_award_amount: Optional[float]


@dataclass
class CompetitionMetrics:
    """Competition metrics for a grant."""

    grant_id: UUID
    mechanism_code: Optional[str]
    competition_score: Optional[float]
    estimated_applicants: Optional[int]
    similar_grants_count: Optional[int]
    success_rate: Optional[float]
    competition_level: Optional[str]
    factors: list[str]


@dataclass
class FundedProjectSummary:
    """Summary of a funded project."""

    id: UUID
    external_id: str
    title: str
    mechanism: Optional[str]
    pi_name: Optional[str]
    pi_institution: Optional[str]
    award_amount: Optional[int]
    fiscal_year: Optional[int]
    is_new: Optional[bool]


# =============================================================================
# Mechanism Functions
# =============================================================================


async def get_all_mechanisms(
    db: AsyncSession,
    funding_agency: Optional[str] = None,
    category: Optional[str] = None,
) -> list[GrantMechanism]:
    """
    Get all grant mechanisms with optional filtering.

    Args:
        db: Database session
        funding_agency: Filter by funding agency (e.g., 'NIH', 'NSF')
        category: Filter by category (e.g., 'research', 'career', 'training')

    Returns:
        List of GrantMechanism objects
    """
    query = select(GrantMechanism)

    conditions = []
    if funding_agency:
        conditions.append(GrantMechanism.funding_agency == funding_agency)
    if category:
        conditions.append(GrantMechanism.category == category)

    if conditions:
        query = query.where(and_(*conditions))

    query = query.order_by(GrantMechanism.code)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_mechanism_by_code(
    db: AsyncSession,
    code: str,
) -> Optional[GrantMechanism]:
    """
    Get a grant mechanism by its code.

    Args:
        db: Database session
        code: Mechanism code (e.g., 'R01', 'K01')

    Returns:
        GrantMechanism object or None
    """
    result = await db.execute(select(GrantMechanism).where(GrantMechanism.code == code.upper()))
    return result.scalar_one_or_none()


async def get_mechanism_stats(
    db: AsyncSession,
    code: str,
) -> Optional[MechanismStats]:
    """
    Get statistics for a grant mechanism including funded project data.

    Args:
        db: Database session
        code: Mechanism code (e.g., 'R01', 'K01')

    Returns:
        MechanismStats object or None
    """
    mechanism = await get_mechanism_by_code(db, code)
    if not mechanism:
        return None

    # Get funded projects count and average award
    result = await db.execute(
        select(
            func.count(FundedProject.id).label("count"),
            func.avg(FundedProject.award_amount).label("avg_award"),
        ).where(FundedProject.mechanism == code.upper())
    )
    row = result.first()
    funded_count = row.count if row else 0
    avg_award = row.avg_award if row else None

    return MechanismStats(
        code=mechanism.code,
        name=mechanism.name,
        funding_agency=mechanism.funding_agency,
        category=mechanism.category,
        success_rate_overall=mechanism.success_rate_overall,
        success_rate_new=mechanism.success_rate_new,
        success_rate_renewal=mechanism.success_rate_renewal,
        competition_level=mechanism.competition_level,
        typical_budget_min=mechanism.typical_budget_min,
        typical_budget_max=mechanism.typical_budget_max,
        funded_projects_count=funded_count,
        avg_award_amount=float(avg_award) if avg_award else None,
    )


# =============================================================================
# Funded Projects Functions
# =============================================================================


async def get_funded_projects_by_mechanism(
    db: AsyncSession,
    mechanism: str,
    fiscal_year: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
) -> list[FundedProject]:
    """
    Get funded projects by mechanism code.

    Args:
        db: Database session
        mechanism: Mechanism code (e.g., 'R01', 'K01')
        fiscal_year: Optional fiscal year filter
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of FundedProject objects
    """
    query = select(FundedProject).where(FundedProject.mechanism == mechanism.upper())

    if fiscal_year:
        query = query.where(FundedProject.fiscal_year == fiscal_year)

    query = query.order_by(FundedProject.award_date.desc()).limit(limit).offset(offset)

    result = await db.execute(query)
    return list(result.scalars().all())


async def get_funded_projects_by_institute(
    db: AsyncSession,
    funding_institute: str,
    limit: int = 100,
    offset: int = 0,
) -> list[FundedProject]:
    """
    Get funded projects by funding institute.

    Args:
        db: Database session
        funding_institute: Institute code (e.g., 'NCI', 'NHLBI')
        limit: Maximum number of results
        offset: Pagination offset

    Returns:
        List of FundedProject objects
    """
    query = (
        select(FundedProject)
        .where(FundedProject.funding_institute == funding_institute.upper())
        .order_by(FundedProject.award_date.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    return list(result.scalars().all())


async def count_funded_projects(
    db: AsyncSession,
    mechanism: Optional[str] = None,
    funding_institute: Optional[str] = None,
    fiscal_year: Optional[int] = None,
) -> int:
    """
    Count funded projects with optional filters.

    Args:
        db: Database session
        mechanism: Optional mechanism code filter
        funding_institute: Optional institute filter
        fiscal_year: Optional fiscal year filter

    Returns:
        Count of matching projects
    """
    query = select(func.count(FundedProject.id))

    conditions = []
    if mechanism:
        conditions.append(FundedProject.mechanism == mechanism.upper())
    if funding_institute:
        conditions.append(FundedProject.funding_institute == funding_institute.upper())
    if fiscal_year:
        conditions.append(FundedProject.fiscal_year == fiscal_year)

    if conditions:
        query = query.where(and_(*conditions))

    result = await db.execute(query)
    return result.scalar() or 0


async def get_funded_project_summaries(
    db: AsyncSession,
    mechanism: str,
    limit: int = 20,
) -> list[FundedProjectSummary]:
    """
    Get summaries of funded projects for a mechanism.

    Args:
        db: Database session
        mechanism: Mechanism code
        limit: Maximum number of results

    Returns:
        List of FundedProjectSummary objects
    """
    projects = await get_funded_projects_by_mechanism(db, mechanism, limit=limit)

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


# =============================================================================
# Competition Functions
# =============================================================================


async def get_competition_data_for_grant(
    db: AsyncSession,
    grant_id: UUID,
) -> Optional[CompetitionMetrics]:
    """
    Get competition data for a specific grant.

    Args:
        db: Database session
        grant_id: Grant UUID

    Returns:
        CompetitionMetrics object or None
    """
    # Get the grant
    grant_result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        return None

    # Get the latest competition snapshot
    snapshot_result = await db.execute(
        select(CompetitionSnapshot)
        .where(CompetitionSnapshot.grant_id == grant_id)
        .order_by(CompetitionSnapshot.snapshot_date.desc())
        .limit(1)
    )
    snapshot = snapshot_result.scalar_one_or_none()

    # Extract mechanism from grant title/description
    mechanism_code = extract_mechanism_from_grant(grant)
    mechanism = None
    if mechanism_code:
        mechanism = await get_mechanism_by_code(db, mechanism_code)

    # Build factors list
    factors = []
    if mechanism:
        if mechanism.success_rate_overall:
            factors.append(f"Historical success rate: {mechanism.success_rate_overall:.1%}")
        if mechanism.competition_level:
            factors.append(f"Competition level: {mechanism.competition_level}")
        if mechanism.estimated_applicants_per_cycle:
            factors.append(f"Est. applicants/cycle: {mechanism.estimated_applicants_per_cycle}")

    if snapshot:
        if snapshot.similar_grants_count:
            factors.append(f"Similar open grants: {snapshot.similar_grants_count}")
        if snapshot.factors:
            factors.extend(snapshot.factors.get("additional_factors", []))

    return CompetitionMetrics(
        grant_id=grant_id,
        mechanism_code=mechanism_code,
        competition_score=snapshot.competition_score if snapshot else None,
        estimated_applicants=snapshot.estimated_applicants
        if snapshot
        else (mechanism.estimated_applicants_per_cycle if mechanism else None),
        similar_grants_count=snapshot.similar_grants_count if snapshot else None,
        success_rate=mechanism.success_rate_overall if mechanism else None,
        competition_level=mechanism.competition_level if mechanism else None,
        factors=factors,
    )


async def calculate_competition_score(
    db: AsyncSession,
    grant: Grant,
) -> float:
    """
    Calculate a competition score for a grant.

    Score ranges from 0.0 (low competition) to 1.0 (high competition).

    Args:
        db: Database session
        grant: Grant object

    Returns:
        Competition score (0.0 to 1.0)
    """
    base_score = 0.5  # Default medium competition

    # Extract mechanism
    mechanism_code = extract_mechanism_from_grant(grant)
    if mechanism_code:
        mechanism = await get_mechanism_by_code(db, mechanism_code)
        if mechanism and mechanism.success_rate_overall:
            # Invert success rate: lower success = higher competition
            base_score = 1.0 - mechanism.success_rate_overall

    # Adjust for deadline proximity (closer deadline = more competition)
    if grant.deadline:
        now = datetime.now(timezone.utc)
        days_until_deadline = (grant.deadline - now).days
        if days_until_deadline < 30:
            base_score = min(1.0, base_score + 0.1)  # Imminent deadlines
        elif days_until_deadline < 60:
            base_score = min(1.0, base_score + 0.05)

    # Adjust for funding amount (larger awards = more competition)
    if grant.amount_max:
        if grant.amount_max > 1000000:
            base_score = min(1.0, base_score + 0.1)
        elif grant.amount_max > 500000:
            base_score = min(1.0, base_score + 0.05)

    # Count similar open grants
    similar_count = await count_similar_open_grants(db, grant)
    if similar_count < 3:
        base_score = max(0.0, base_score - 0.1)  # Less competition
    elif similar_count > 10:
        base_score = min(1.0, base_score + 0.1)  # More competition

    return round(base_score, 2)


async def count_similar_open_grants(
    db: AsyncSession,
    grant: Grant,
) -> int:
    """
    Count similar open grants to a given grant.

    Args:
        db: Database session
        grant: Grant object

    Returns:
        Count of similar open grants
    """
    now = datetime.now(timezone.utc)

    # Build conditions for similar grants
    conditions = [
        Grant.id != grant.id,  # Exclude self
        Grant.deadline >= now,  # Must be open
    ]

    # Same agency
    if grant.agency:
        conditions.append(Grant.agency == grant.agency)

    # Similar amount range (within 50%)
    if grant.amount_max:
        conditions.append(Grant.amount_max >= grant.amount_max * 0.5)
        conditions.append(Grant.amount_max <= grant.amount_max * 1.5)

    query = select(func.count(Grant.id)).where(and_(*conditions))
    result = await db.execute(query)
    return result.scalar() or 0


async def create_competition_snapshot(
    db: AsyncSession,
    grant_id: UUID,
) -> Optional[CompetitionSnapshot]:
    """
    Create a new competition snapshot for a grant.

    Args:
        db: Database session
        grant_id: Grant UUID

    Returns:
        Created CompetitionSnapshot or None
    """
    # Get the grant
    grant_result = await db.execute(select(Grant).where(Grant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        return None

    # Calculate competition score
    competition_score = await calculate_competition_score(db, grant)

    # Get mechanism
    mechanism_code = extract_mechanism_from_grant(grant)
    mechanism = None
    mechanism_id = None
    if mechanism_code:
        mechanism = await get_mechanism_by_code(db, mechanism_code)
        mechanism_id = mechanism.id if mechanism else None

    # Count similar grants
    similar_count = await count_similar_open_grants(db, grant)

    # Build factors
    factors: dict[str, Any] = {
        "mechanism": mechanism_code,
        "similar_grants": similar_count,
        "additional_factors": [],
    }

    if mechanism:
        factors["success_rate"] = mechanism.success_rate_overall
        factors["competition_level"] = mechanism.competition_level

    # Create snapshot
    snapshot = CompetitionSnapshot(
        grant_id=grant_id,
        mechanism_id=mechanism_id,
        snapshot_date=datetime.now(timezone.utc),
        estimated_applicants=(mechanism.estimated_applicants_per_cycle if mechanism else None),
        similar_grants_count=similar_count,
        competition_score=competition_score,
        factors=factors,
    )

    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    return snapshot


# =============================================================================
# Helper Functions
# =============================================================================


def extract_mechanism_from_grant(grant: Grant) -> Optional[str]:
    """
    Extract grant mechanism code from grant title or description.

    Args:
        grant: Grant object

    Returns:
        Mechanism code or None
    """
    # Common NIH mechanisms
    mechanisms = [
        "R01",
        "R21",
        "R03",
        "R15",
        "R35",
        "U01",
        "U54",
        "K01",
        "K08",
        "K23",
        "K99",
        "K22",
        "F31",
        "F32",
        "T32",
        "P01",
        "P30",
        "P50",
        "R41",
        "R42",
        "R43",
        "R44",
    ]

    text = f"{grant.title or ''} {grant.description or ''}".upper()

    for mech in mechanisms:
        if mech in text or f"({mech})" in text:
            return mech

    return None


async def get_mechanism_success_rate(
    db: AsyncSession,
    mechanism_code: str,
) -> Optional[float]:
    """
    Get the success rate for a mechanism.

    Args:
        db: Database session
        mechanism_code: Mechanism code

    Returns:
        Success rate (0.0 to 1.0) or None
    """
    mechanism = await get_mechanism_by_code(db, mechanism_code)
    return mechanism.success_rate_overall if mechanism else None


async def get_top_funded_institutes(
    db: AsyncSession,
    mechanism: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """
    Get top institutes by funded project count for a mechanism.

    Args:
        db: Database session
        mechanism: Mechanism code
        limit: Maximum number of results

    Returns:
        List of dicts with institute info
    """
    query = (
        select(
            FundedProject.pi_institution,
            func.count(FundedProject.id).label("count"),
            func.sum(FundedProject.award_amount).label("total_funding"),
        )
        .where(FundedProject.mechanism == mechanism.upper())
        .where(FundedProject.pi_institution.is_not(None))
        .group_by(FundedProject.pi_institution)
        .order_by(func.count(FundedProject.id).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "institution": row.pi_institution,
            "funded_count": row.count,
            "total_funding": row.total_funding,
        }
        for row in rows
    ]
