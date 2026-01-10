"""
Grant Insights API endpoints with Server-Sent Events (SSE) streaming.
"""

import json
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.services.grant_insights import get_insights_service

router = APIRouter(prefix="/api/insights", tags=["insights"])


@router.get("/grant/{grant_id}/stream")
async def stream_grant_insights(
    grant_id: UUID,
    insight_type: Literal["eligibility", "writing_tips", "both"] = "both",
    db: AsyncSessionDep = None,
    current_user: CurrentUser = None,
) -> StreamingResponse:
    """
    Stream AI-generated insights for a grant using Server-Sent Events (SSE).

    This endpoint streams eligibility analysis and/or writing tips for a specific grant,
    personalized based on the user's profile.

    **Event Types:**
    - `eligibility_start`: Eligibility analysis is beginning
    - `eligibility_chunk`: A chunk of eligibility analysis content
    - `eligibility_end`: Eligibility analysis is complete
    - `writing_start`: Writing tips generation is beginning
    - `writing_chunk`: A chunk of writing tips content
    - `writing_end`: Writing tips generation is complete
    - `error`: An error occurred

    **Parameters:**
    - `grant_id`: UUID of the grant to analyze
    - `insight_type`: Type of insights to generate (eligibility, writing_tips, or both)

    **Returns:**
    Server-Sent Events stream with text/event-stream content type.
    """
    service = get_insights_service()

    async def generate_sse():
        """Generate SSE formatted events."""
        try:
            async for event in service.stream_insights(
                db=db,
                user=current_user,
                grant_id=grant_id,
                insight_type=insight_type,
            ):
                event_type = event.get("event", "message")
                event_data = event.get("data", {})

                # Format as SSE
                yield f"event: {event_type}\n"
                yield f"data: {json.dumps(event_data)}\n\n"

        except Exception as e:
            # Send error event
            yield "event: error\n"
            yield f"data: {json.dumps({'message': str(e)})}\n\n"

    return StreamingResponse(
        generate_sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@router.get("/grant/{grant_id}/check")
async def check_insights_availability(
    grant_id: UUID,
    db: AsyncSessionDep = None,
    current_user: CurrentUser = None,
) -> dict:
    """
    Check if insights can be generated for a grant.

    Returns information about the grant and user profile completeness.
    """
    from sqlalchemy import select
    from backend.models import Grant, LabProfile

    # Check if grant exists
    grant = await db.get(Grant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    # Check user profile
    profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == current_user.id))
    profile = profile_result.scalar_one_or_none()

    profile_completeness = 0
    profile_fields = []

    if profile:
        if profile.research_areas:
            profile_completeness += 20
            profile_fields.append("research_areas")
        if profile.institution:
            profile_completeness += 15
            profile_fields.append("institution")
        if profile.career_stage:
            profile_completeness += 15
            profile_fields.append("career_stage")
        if profile.past_grants:
            profile_completeness += 25
            profile_fields.append("past_grants")
        if profile.publications:
            profile_completeness += 15
            profile_fields.append("publications")
        if profile.methods:
            profile_completeness += 10
            profile_fields.append("methods")

    return {
        "grant_id": str(grant_id),
        "grant_title": grant.title,
        "has_eligibility_criteria": bool(grant.eligibility),
        "has_description": bool(grant.description),
        "profile_completeness": profile_completeness,
        "profile_fields_present": profile_fields,
        "can_generate_insights": True,  # Always allow, but quality depends on data
        "recommendations": _get_profile_recommendations(profile_completeness, profile_fields),
    }


def _get_profile_recommendations(completeness: int, fields: list) -> list[str]:
    """Get recommendations for improving profile for better insights."""
    recommendations = []

    if "research_areas" not in fields:
        recommendations.append("Add your research areas for better topic alignment analysis")
    if "institution" not in fields:
        recommendations.append("Add your institution for eligibility checking")
    if "career_stage" not in fields:
        recommendations.append("Specify your career stage (early career, mid-career, senior)")
    if "past_grants" not in fields:
        recommendations.append("Add past grant information for funding history analysis")
    if "publications" not in fields:
        recommendations.append("Link your publications for credibility assessment")

    if completeness >= 80:
        recommendations = ["Your profile is well-suited for detailed insights!"]
    elif completeness >= 50:
        recommendations.insert(0, "Good profile data available. Complete more fields for richer insights.")

    return recommendations
