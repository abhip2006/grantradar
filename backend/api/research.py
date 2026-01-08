"""Deep research API endpoints."""
from uuid import UUID
from typing import List
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
import structlog

from backend.api.deps import AsyncSessionDep, CurrentUser
from backend.database import AsyncSessionLocal
from backend.models import ResearchSession
from backend.schemas.research import (
    ResearchStatus,
    ResearchSessionCreate,
    ResearchSessionResponse,
    ResearchSessionListItem,
    ResearchQuickSearch,
    ResearchGrantResult,
)
from backend.services.deep_research import DeepResearchService

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

research_service = DeepResearchService()


@router.post("/sessions", response_model=ResearchSessionResponse)
async def create_research_session(
    request: ResearchSessionCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResearchSessionResponse:
    """
    Start a new deep research session.

    The research runs asynchronously. Poll the session endpoint for results.
    """
    session = await research_service.create_session(
        db=db, user=current_user, query=request.query
    )

    # Run research in background
    async def run_research():
        async with AsyncSessionLocal() as new_db:
            try:
                await research_service.run_research(new_db, session.id)
            except Exception as e:
                logger.error("Background research failed", error=str(e))

    background_tasks.add_task(run_research)

    return ResearchSessionResponse(
        id=session.id,
        user_id=session.user_id,
        query=session.query,
        status=ResearchStatus(session.status),
        results=None,
        insights=None,
        grants_found=None,
        processing_time_ms=None,
        created_at=session.created_at,
        completed_at=None,
    )


@router.get("/sessions", response_model=List[ResearchSessionListItem])
async def list_research_sessions(
    limit: int = 20,
    db: AsyncSessionDep = None,
    current_user: CurrentUser = None,
) -> List[ResearchSessionListItem]:
    """List user's research sessions."""
    sessions = await research_service.get_sessions(db, current_user.id, limit)
    return [
        ResearchSessionListItem(
            id=s.id,
            query=s.query,
            status=ResearchStatus(s.status),
            grants_found=s.grants_found,
            created_at=s.created_at,
            completed_at=s.completed_at,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=ResearchSessionResponse)
async def get_research_session(
    session_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> ResearchSessionResponse:
    """Get a research session with results."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    results = None
    if session.results:
        results = [ResearchGrantResult(**r) for r in session.results]

    return ResearchSessionResponse(
        id=session.id,
        user_id=session.user_id,
        query=session.query,
        status=ResearchStatus(session.status),
        results=results,
        insights=session.insights,
        grants_found=session.grants_found,
        processing_time_ms=session.processing_time_ms,
        created_at=session.created_at,
        completed_at=session.completed_at,
    )


@router.post("/quick-search", response_model=List[ResearchGrantResult])
async def quick_search(
    request: ResearchQuickSearch,
    db: AsyncSessionDep,
    current_user: CurrentUser,
) -> List[ResearchGrantResult]:
    """
    Quick synchronous search for grants.

    Faster than full research but less thorough.
    Good for browsing and exploration.
    """
    return await research_service.quick_search(
        db=db,
        user=current_user,
        query=request.query,
        max_results=request.max_results,
    )


@router.delete("/sessions/{session_id}")
async def delete_research_session(
    session_id: UUID,
    db: AsyncSessionDep,
    current_user: CurrentUser,
):
    """Delete a research session."""
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    await db.delete(session)
    await db.commit()
    return {"message": "Session deleted"}
