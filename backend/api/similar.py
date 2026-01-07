"""
Similar Grants API Endpoints
Find grants similar to a given grant using algorithmic similarity.
"""
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.api.deps import AsyncSessionDep
from backend.services.similarity import find_similar_grants


router = APIRouter(prefix="/api/grants", tags=["Similar Grants"])


class SimilarGrantResponse(BaseModel):
    """Schema for a similar grant in the response."""

    id: UUID = Field(..., description="Grant ID")
    source: str = Field(..., description="Data source (nih, nsf, grants_gov)")
    external_id: str = Field(..., description="External identifier")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(None, description="Grant description")
    agency: Optional[str] = Field(None, description="Funding agency")
    amount_min: Optional[int] = Field(None, description="Minimum funding amount")
    amount_max: Optional[int] = Field(None, description="Maximum funding amount")
    deadline: Optional[str] = Field(None, description="Application deadline")
    posted_at: Optional[str] = Field(None, description="Posted date")
    url: Optional[str] = Field(None, description="Grant URL")
    categories: Optional[list[str]] = Field(None, description="Grant categories")
    similarity_score: int = Field(..., description="Similarity score (0-100)")
    similarity_reasons: list[str] = Field(..., description="Reasons for similarity")

    class Config:
        from_attributes = True


class SimilarGrantsResponse(BaseModel):
    """Schema for the similar grants list response."""

    similar_grants: list[SimilarGrantResponse] = Field(..., description="List of similar grants")
    source_grant_id: UUID = Field(..., description="ID of the source grant")
    total: int = Field(..., description="Total number of similar grants found")


@router.get(
    "/{grant_id}/similar",
    response_model=SimilarGrantsResponse,
    summary="Find similar grants",
    description="Find grants similar to the given grant based on categories, agency, funding, and keywords."
)
async def get_similar_grants(
    grant_id: UUID,
    db: AsyncSessionDep,
    limit: int = Query(default=10, ge=1, le=50, description="Maximum number of results"),
    min_score: int = Query(default=20, ge=0, le=100, description="Minimum similarity score (0-100)"),
) -> SimilarGrantsResponse:
    """
    Find grants similar to the specified grant.

    Similarity is calculated based on:
    - Category/focus area overlap (40% weight)
    - Agency matching (25% weight)
    - Funding range proximity (20% weight)
    - Title keyword similarity (15% weight)

    Returns a list of similar grants with similarity scores and reasons.
    """
    # Find similar grants
    results = await find_similar_grants(
        db=db,
        grant_id=grant_id,
        limit=limit,
        min_score=min_score,
    )

    if not results:
        # Check if the source grant exists
        from sqlalchemy import select
        from backend.models import Grant

        check_result = await db.execute(
            select(Grant.id).where(Grant.id == grant_id)
        )
        if not check_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Grant not found"
            )

    # Convert to response models
    similar_grants = []
    for result in results:
        grant = result.grant
        similar_grants.append(
            SimilarGrantResponse(
                id=grant.id,
                source=grant.source,
                external_id=grant.external_id,
                title=grant.title,
                description=grant.description[:500] if grant.description else None,
                agency=grant.agency,
                amount_min=grant.amount_min,
                amount_max=grant.amount_max,
                deadline=grant.deadline.isoformat() if grant.deadline else None,
                posted_at=grant.posted_at.isoformat() if grant.posted_at else None,
                url=grant.url,
                categories=grant.categories,
                similarity_score=result.similarity_score,
                similarity_reasons=result.similarity_reasons,
            )
        )

    return SimilarGrantsResponse(
        similar_grants=similar_grants,
        source_grant_id=grant_id,
        total=len(similar_grants),
    )
