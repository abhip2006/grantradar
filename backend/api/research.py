"""Deep research API endpoints."""
import json
from uuid import UUID
from typing import List, AsyncGenerator
from fastapi import APIRouter, HTTPException, status, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
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


@router.get("/sessions/{session_id}/stream")
async def stream_research_session(
    session_id: UUID,
    request: Request,
    db: AsyncSessionDep,
    current_user: CurrentUser,
):
    """
    Stream research progress via Server-Sent Events (SSE).

    This endpoint provides real-time updates during research execution.
    Connect before starting research, or reconnect to a processing session.

    SSE Event Types:
    - status: {"phase": "searching|analyzing|generating_insights|...", "message": "..."}
    - grant_found: {"grant": {...}}
    - progress: {"percent": 0-100, "message": "..."}
    - insights: {"insights": "..."}
    - complete: {"grants_found": N, "processing_time_ms": N}
    - error: {"error": "...", "phase": "..."}
    """
    # Verify session ownership
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # If session is already completed or failed, return final status immediately
    if session.status in ("completed", "failed"):
        async def completed_stream() -> AsyncGenerator[str, None]:
            if session.status == "completed":
                yield f"event: status\ndata: {json.dumps({'phase': 'completed', 'message': 'Research already completed'})}\n\n"
                yield f"event: complete\ndata: {json.dumps({'grants_found': session.grants_found or 0, 'processing_time_ms': session.processing_time_ms or 0})}\n\n"
            else:
                yield f"event: status\ndata: {json.dumps({'phase': 'failed', 'message': session.insights or 'Research failed'})}\n\n"
                yield f"event: error\ndata: {json.dumps({'error': session.insights or 'Research failed', 'phase': 'failed'})}\n\n"

        return StreamingResponse(
            completed_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from research progress."""
        async with AsyncSessionLocal() as new_db:
            try:
                async for event in research_service.run_research_with_progress(new_db, session_id):
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info("Client disconnected from SSE stream", session_id=str(session_id))
                        break

                    # Format as SSE
                    event_type = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_type}\ndata: {event_data}\n\n"

            except Exception as e:
                logger.error("SSE stream error", session_id=str(session_id), error=str(e))
                yield f"event: error\ndata: {json.dumps({'error': str(e), 'phase': 'failed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.post("/sessions/{session_id}/start-stream")
async def start_research_with_stream(
    session_id: UUID,
    request: Request,
    db: AsyncSessionDep,
    current_user: CurrentUser,
):
    """
    Start research and stream progress via SSE.

    Alternative to the background task approach - runs research synchronously
    while streaming progress to the client. Useful when you want immediate
    feedback without needing to poll.

    The session must be in 'pending' status to start.
    """
    # Verify session ownership and status
    session = await db.get(ResearchSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if session.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Session is already {session.status}. Use GET /stream to reconnect."
        )

    async def event_generator() -> AsyncGenerator[str, None]:
        """Generate SSE events from research progress."""
        async with AsyncSessionLocal() as new_db:
            try:
                async for event in research_service.run_research_with_progress(new_db, session_id):
                    # Check if client disconnected
                    if await request.is_disconnected():
                        logger.info("Client disconnected from SSE stream", session_id=str(session_id))
                        break

                    # Format as SSE
                    event_type = event.get("event", "message")
                    event_data = json.dumps(event.get("data", {}))
                    yield f"event: {event_type}\ndata: {event_data}\n\n"

            except Exception as e:
                logger.error("SSE stream error", session_id=str(session_id), error=str(e))
                yield f"event: error\ndata: {json.dumps({'error': str(e), 'phase': 'failed'})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
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
