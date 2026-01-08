"""Eligibility check API endpoints."""
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models import User, ChatSession
from backend.schemas.eligibility import (
    EligibilityCheckRequest,
    EligibilityCheckResponse,
    EligibilityFollowUpRequest,
    EligibilityFollowUpResponse,
)
from backend.services.eligibility_checker import EligibilityChecker

router = APIRouter(prefix="/api/eligibility", tags=["eligibility"])

eligibility_checker = EligibilityChecker()


@router.post("/check", response_model=EligibilityCheckResponse)
async def check_eligibility(
    request: EligibilityCheckRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EligibilityCheckResponse:
    """
    Check researcher eligibility for a specific grant.

    Uses AI to analyze the researcher's profile against grant requirements.
    Returns detailed eligibility assessment with recommendations.
    """
    try:
        return await eligibility_checker.check_eligibility(
            db=db,
            user=current_user,
            grant_id=request.grant_id,
            additional_context=request.additional_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility check failed: {str(e)}"
        )


@router.post("/follow-up", response_model=EligibilityFollowUpResponse)
async def eligibility_follow_up(
    request: EligibilityFollowUpRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EligibilityFollowUpResponse:
    """
    Continue eligibility conversation with follow-up question.

    Allows asking additional questions about eligibility or
    providing more information to refine the assessment.
    """
    try:
        return await eligibility_checker.follow_up(
            db=db,
            user=current_user,
            session_id=request.session_id,
            message=request.message,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Follow-up failed: {str(e)}"
        )


@router.get("/sessions", response_model=list)
async def list_eligibility_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List user's eligibility check sessions."""
    from sqlalchemy import select

    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .where(ChatSession.session_type == "eligibility")
        .order_by(ChatSession.created_at.desc())
        .limit(50)
    )
    sessions = result.scalars().all()

    return [
        {
            "id": str(s.id),
            "title": s.title,
            "grant_id": str(s.context_grant_id) if s.context_grant_id else None,
            "metadata": s.metadata_,
            "created_at": s.created_at.isoformat(),
        }
        for s in sessions
    ]
