"""Chat API endpoints for RAG-powered Q&A."""
from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import get_db
from backend.api.deps import get_current_user
from backend.models import User, ChatSession
from backend.schemas.chat import (
    ChatSessionCreate,
    ChatSessionResponse,
    ChatSessionListItem,
    ChatMessageCreate,
    ChatMessageResponse,
)
from backend.services.rag_chat import RAGChatService

router = APIRouter(prefix="/api/chat", tags=["chat"])

chat_service = RAGChatService()


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    """Create a new chat session."""
    session = await chat_service.create_session(
        db=db,
        user=current_user,
        title=request.title,
        session_type=request.session_type.value,
        context_grant_id=request.context_grant_id,
    )
    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        session_type=session.session_type,
        context_grant_id=session.context_grant_id,
        messages=[],
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("/sessions", response_model=List[ChatSessionListItem])
async def list_chat_sessions(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[ChatSessionListItem]:
    """List user's chat sessions."""
    sessions = await chat_service.get_sessions(db, current_user.id, limit)
    return [ChatSessionListItem(**s) for s in sessions]


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatSessionResponse:
    """Get a chat session with all messages."""
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    messages = await chat_service.get_session_messages(db, current_user.id, session_id)

    return ChatSessionResponse(
        id=session.id,
        title=session.title,
        session_type=session.session_type,
        context_grant_id=session.context_grant_id,
        messages=messages,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_chat_message(
    session_id: UUID,
    request: ChatMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ChatMessageResponse:
    """Send a message in a chat session and get AI response."""
    try:
        return await chat_service.send_message(
            db=db,
            user=current_user,
            session_id=session_id,
            content=request.content,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat error: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a chat session."""
    deleted = await chat_service.delete_session(db, current_user.id, session_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    return {"message": "Session deleted"}
