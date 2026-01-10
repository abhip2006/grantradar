"""Chat with proposal schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from uuid import UUID
from typing import Optional, List
from enum import Enum


class ChatSessionType(str, Enum):
    PROPOSAL = "proposal_chat"
    ELIGIBILITY = "eligibility"
    RESEARCH = "research"


class ChatSource(BaseModel):
    """A source citation from RAG."""

    document_type: str  # 'grant', 'foa', 'guideline', 'profile'
    document_id: Optional[str] = None
    title: str
    excerpt: str
    relevance_score: float


class ChatMessageCreate(BaseModel):
    """Create a new chat message."""

    content: str = Field(..., min_length=1, max_length=4000)


class ChatMessageResponse(BaseModel):
    """Chat message response."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    sources: Optional[List[ChatSource]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""

    title: Optional[str] = None
    session_type: ChatSessionType = ChatSessionType.PROPOSAL
    context_grant_id: Optional[UUID] = None


class ChatSessionResponse(BaseModel):
    """Chat session response."""

    id: UUID
    title: str
    session_type: str
    context_grant_id: Optional[UUID] = None
    messages: List[ChatMessageResponse] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatSessionListItem(BaseModel):
    """Summary of a chat session for listing."""

    id: UUID
    title: str
    session_type: str
    message_count: int
    last_message_at: Optional[datetime]
    created_at: datetime
