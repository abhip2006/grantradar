"""
Grant Comparison API Endpoint
Compare multiple grants side-by-side.
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.api.deps import AsyncSessionDep, OptionalUser
from backend.models import Grant, Match

router = APIRouter(prefix="/api/grants", tags=["Grants"])


class CompareRequest(BaseModel):
    """Request body for comparing grants."""

    grant_ids: list[str] = Field(
        ..., min_length=2, max_length=4, description="List of grant IDs to compare (2-4 grants)"
    )


class ComparisonGrant(BaseModel):
    """Schema for grant comparison response."""

    id: UUID = Field(..., description="Grant ID")
    title: str = Field(..., description="Grant title")
    agency: Optional[str] = Field(None, description="Funding agency")
    source: str = Field(..., description="Grant source")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    deadline: Optional[str] = Field(None, description="Application deadline")
    url: Optional[str] = Field(None, description="Grant URL")
    categories: Optional[list[str]] = Field(None, description="Grant categories/focus areas")
    eligibility: Optional[dict] = Field(None, description="Eligibility criteria")
    description: Optional[str] = Field(None, description="Grant description")
    match_score: Optional[float] = Field(None, description="Match score for current user (0-1)")

    class Config:
        from_attributes = True


class CompareResponse(BaseModel):
    """Response for grant comparison."""

    grants: list[ComparisonGrant] = Field(..., description="List of grants to compare")
    comparison_id: Optional[str] = Field(None, description="ID to save/share this comparison")


@router.post(
    "/compare",
    response_model=CompareResponse,
    summary="Compare multiple grants",
    description="Get normalized grant details for side-by-side comparison.",
)
async def compare_grants(
    request: CompareRequest,
    db: AsyncSessionDep,
    current_user: OptionalUser,
) -> CompareResponse:
    """
    Compare multiple grants side-by-side.

    Accepts 2-4 grant IDs and returns normalized grant details
    suitable for comparison table display.

    If authenticated, includes match scores for the current user.
    """
    # Validate and parse grant IDs
    try:
        grant_uuids = [UUID(gid) for gid in request.grant_ids]
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid grant ID format")

    # Fetch grants
    result = await db.execute(select(Grant).where(Grant.id.in_(grant_uuids)))
    grants = result.scalars().all()

    if len(grants) != len(grant_uuids):
        found_ids = {str(g.id) for g in grants}
        missing_ids = [gid for gid in request.grant_ids if gid not in found_ids]
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Grants not found: {', '.join(missing_ids)}")

    # Get match scores if user is authenticated
    match_scores = {}
    if current_user:
        match_result = await db.execute(
            select(Match).where(Match.grant_id.in_(grant_uuids), Match.user_id == current_user.id)
        )
        matches = match_result.scalars().all()
        match_scores = {str(m.grant_id): m.match_score for m in matches}

    # Build comparison response preserving requested order
    grant_map = {str(g.id): g for g in grants}
    comparison_grants = []

    for gid in request.grant_ids:
        grant = grant_map[gid]
        comparison_grants.append(
            ComparisonGrant(
                id=grant.id,
                title=grant.title,
                agency=grant.agency,
                source=grant.source,
                amount_min=grant.amount_min,
                amount_max=grant.amount_max,
                deadline=grant.deadline.isoformat() if grant.deadline else None,
                url=grant.url,
                categories=grant.categories,
                eligibility=grant.eligibility,
                description=grant.description,
                match_score=match_scores.get(gid),
            )
        )

    return CompareResponse(
        grants=comparison_grants,
        comparison_id=None,  # Could generate a shareable ID here in future
    )
