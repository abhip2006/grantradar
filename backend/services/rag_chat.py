"""RAG chat service for document Q&A."""

import openai
from datetime import datetime, timezone
from typing import Optional, List, AsyncGenerator
from uuid import UUID
import json
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, func

from backend.core.config import settings
from backend.models import User, Grant, ChatSession, ChatMessage, LabProfile
from backend.schemas.chat import ChatSource, ChatMessageResponse

logger = structlog.get_logger(__name__)


class StreamEvent:
    """Represents an SSE event for streaming responses."""

    def __init__(self, event: str, data: dict):
        self.event = event
        self.data = data

    def to_sse(self) -> str:
        """Convert to SSE format string."""
        return f"event: {self.event}\ndata: {json.dumps(self.data)}\n\n"


class RAGChatService:
    """Service for RAG-powered chat with grant documents."""

    def __init__(self):
        self.openai = openai.OpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model

    async def create_session(
        self,
        db: AsyncSession,
        user: User,
        title: Optional[str] = None,
        session_type: str = "proposal_chat",
        context_grant_id: Optional[UUID] = None,
    ) -> ChatSession:
        """Create a new chat session."""
        # Generate title if not provided
        if not title:
            if context_grant_id:
                grant = await db.get(Grant, context_grant_id)
                title = f"Chat: {grant.title[:40]}..." if grant else "New Chat"
            else:
                title = f"Chat - {datetime.now().strftime('%b %d, %H:%M')}"

        session = ChatSession(
            user_id=user.id,
            title=title,
            session_type=session_type,
            context_grant_id=context_grant_id,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def send_message(
        self,
        db: AsyncSession,
        user: User,
        session_id: UUID,
        content: str,
    ) -> ChatMessageResponse:
        """Process a user message and generate AI response with RAG."""

        # Verify session ownership
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise ValueError("Session not found")

        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(user_msg)
        await db.flush()

        # Get conversation history
        history = await self._get_conversation_history(db, session_id)

        # Retrieve relevant documents using RAG
        sources, context = await self._retrieve_context(db, user, content, session)

        # Build system prompt with context
        system_prompt = self._build_system_prompt(session, context, user)

        # Generate response with Claude
        response_text = await self._generate_response(system_prompt, history, content)

        # Save assistant message
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=response_text,
            sources=[s.model_dump() for s in sources] if sources else None,
        )
        db.add(assistant_msg)

        # Update session's updated_at timestamp
        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(assistant_msg)

        return ChatMessageResponse(
            id=assistant_msg.id,
            session_id=session_id,
            role="assistant",
            content=response_text,
            sources=sources,
            created_at=assistant_msg.created_at,
        )

    async def stream_message(
        self,
        db: AsyncSession,
        user: User,
        session_id: UUID,
        content: str,
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a user message and stream the AI response with RAG.

        Yields SSE events:
        - message_start: Indicates streaming has begun
        - message_chunk: Contains content chunks as they arrive
        - message_end: Indicates streaming is complete
        - sources: Contains the retrieved sources
        """

        # Verify session ownership
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise ValueError("Session not found")

        # Save user message
        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=content,
        )
        db.add(user_msg)
        await db.flush()

        # Get conversation history
        history = await self._get_conversation_history(db, session_id)

        # Retrieve relevant documents using RAG
        sources, context = await self._retrieve_context(db, user, content, session)

        # Build system prompt with context
        system_prompt = self._build_system_prompt(session, context, user)

        # Yield message_start event
        yield StreamEvent("message_start", {})

        # Stream response using OpenAI
        full_response = ""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": content})

        try:
            stream = self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=messages,
                stream=True,
            )
            for chunk in stream:
                if chunk.choices[0].delta.content:
                    text_chunk = chunk.choices[0].delta.content
                    full_response += text_chunk
                    yield StreamEvent("message_chunk", {"content": text_chunk})
        except Exception as e:
            logger.error("OpenAI streaming API error", error=str(e))
            error_message = "I apologize, but I encountered an error processing your request. Please try again."
            full_response = error_message
            yield StreamEvent("message_chunk", {"content": error_message})

        # Yield message_end event
        yield StreamEvent("message_end", {})

        # Yield sources event
        yield StreamEvent("sources", {"sources": [s.model_dump() for s in sources] if sources else []})

        # Save assistant message to database
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=full_response,
            sources=[s.model_dump() for s in sources] if sources else None,
        )
        db.add(assistant_msg)

        # Update session's updated_at timestamp
        session.updated_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(assistant_msg)

    async def _get_conversation_history(self, db: AsyncSession, session_id: UUID) -> List[dict]:
        """Get conversation history for context."""
        result = await db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at)
            .limit(20)  # Limit history for token management
        )
        messages = result.scalars().all()

        return [{"role": msg.role, "content": msg.content} for msg in messages if msg.role in ("user", "assistant")]

    async def _retrieve_context(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        session: ChatSession,
    ) -> tuple[List[ChatSource], str]:
        """Retrieve relevant context using vector similarity search."""
        sources = []
        context_parts = []
        similar_grants = []

        # Try vector similarity search with savepoint to isolate potential failures
        try:
            # Generate embedding for query
            embedding_response = self.openai.embeddings.create(
                model=self.embedding_model,
                input=query,
            )
            query_embedding = embedding_response.data[0].embedding

            # Search grants using pgvector inside a savepoint
            # This allows us to rollback just this query if it fails
            # without affecting the rest of the transaction
            async with db.begin_nested():
                # Convert embedding list to pgvector format string
                embedding_str = "[" + ",".join(map(str, query_embedding)) + "]"
                grants_query = text("""
                    SELECT id, title, description, agency, eligibility, categories,
                           amount_min, amount_max, deadline,
                           1 - (embedding <=> CAST(:embedding AS vector)) as similarity
                    FROM grants
                    WHERE embedding IS NOT NULL
                    ORDER BY embedding <=> CAST(:embedding AS vector)
                    LIMIT 5
                """)

                result = await db.execute(grants_query, {"embedding": embedding_str})
                similar_grants = result.fetchall()
        except Exception as e:
            logger.warning("Vector search failed, continuing without RAG context", error=str(e))
            similar_grants = []

        # Process similar grants (no DB access needed here)
        for grant_row in similar_grants:
            if grant_row.similarity > 0.5:  # Relevance threshold
                excerpt = (grant_row.description or "")[:500]

                # Format eligibility as text if it's a dict
                eligibility_text = ""
                if grant_row.eligibility:
                    if isinstance(grant_row.eligibility, dict):
                        eligibility_text = json.dumps(grant_row.eligibility, indent=2)[:300]
                    else:
                        eligibility_text = str(grant_row.eligibility)[:300]

                if eligibility_text:
                    excerpt += f"\n\nEligibility: {eligibility_text}"

                sources.append(
                    ChatSource(
                        document_type="grant",
                        document_id=str(grant_row.id),
                        title=grant_row.title,
                        excerpt=excerpt,
                        relevance_score=float(grant_row.similarity),
                    )
                )

                context_parts.append(f"""
Grant: {grant_row.title}
Agency: {grant_row.agency or "Unknown"}
Categories: {", ".join(grant_row.categories) if grant_row.categories else "N/A"}
Description: {grant_row.description or "No description"}
Eligibility: {eligibility_text or "Not specified"}
Amount: ${grant_row.amount_min or 0:,} - ${grant_row.amount_max or 0:,}
Deadline: {grant_row.deadline or "Not specified"}
---""")

        # If session has a context grant, always include it
        # Use savepoint to isolate potential DB failures
        if session.context_grant_id:
            try:
                async with db.begin_nested():
                    context_grant = await db.get(Grant, session.context_grant_id)
                if context_grant:
                    eligibility_text = ""
                    if context_grant.eligibility:
                        if isinstance(context_grant.eligibility, dict):
                            eligibility_text = json.dumps(context_grant.eligibility, indent=2)
                        else:
                            eligibility_text = str(context_grant.eligibility)

                    context_parts.insert(
                        0,
                        f"""
FOCUSED GRANT (User's primary interest):
Title: {context_grant.title}
Agency: {context_grant.agency}
Categories: {", ".join(context_grant.categories) if context_grant.categories else "N/A"}
Description: {context_grant.description}
Eligibility: {eligibility_text or "Not specified"}
Deadline: {context_grant.deadline}
Award Amount: ${context_grant.amount_min or 0:,} - ${context_grant.amount_max or 0:,}
---""",
                    )
            except Exception as e:
                logger.warning("Failed to fetch context grant", error=str(e))

        # Get user's lab profile for context
        # Use savepoint to isolate potential DB failures
        try:
            async with db.begin_nested():
                profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == user.id))
                profile = profile_result.scalar_one_or_none()
            if profile:
                context_parts.append(f"""
RESEARCHER PROFILE:
Research Areas: {", ".join(profile.research_areas or [])}
Institution: {profile.institution or "Unknown"}
Career Stage: {profile.career_stage or "Unknown"}
---""")
        except Exception as e:
            logger.warning("Failed to fetch user profile", error=str(e))

        context = "\n".join(context_parts) if context_parts else ""
        return sources[:5], context  # Limit sources

    def _build_system_prompt(self, session: ChatSession, context: str, user: User) -> str:
        """Build system prompt with RAG context."""
        base_prompt = f"""You are GrantRadar AI, an expert grant writing and funding advisor. You help researchers find and apply for grants.

User: {user.name or user.email}
Session Type: {session.session_type}

Your capabilities:
- Answer questions about grant opportunities and requirements
- Explain eligibility criteria and application processes
- Provide writing advice for grant proposals
- Compare different funding opportunities
- Suggest strategies for strengthening applications

Guidelines:
- Be concise but thorough
- Cite specific information from the context when available
- If you don't know something, say so
- Provide actionable advice when possible
- Use plain language, avoid jargon"""

        if context:
            base_prompt += f"""

RELEVANT CONTEXT FROM KNOWLEDGE BASE:
{context}

Use this context to answer the user's question. Reference specific grants or requirements when relevant."""

        return base_prompt

    async def _generate_response(self, system_prompt: str, history: List[dict], user_message: str) -> str:
        """Generate response using OpenAI."""
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=messages,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error("OpenAI API error", error=str(e))
            return "I apologize, but I encountered an error processing your request. Please try again."

    async def get_sessions(self, db: AsyncSession, user_id: UUID, limit: int = 50) -> List[dict]:
        """Get user's chat sessions."""
        result = await db.execute(
            select(ChatSession)
            .where(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
        )
        sessions = result.scalars().all()

        session_list = []
        for s in sessions:
            # Get message count and last message time
            msg_result = await db.execute(
                select(func.count(ChatMessage.id), func.max(ChatMessage.created_at)).where(
                    ChatMessage.session_id == s.id
                )
            )
            count, last_msg = msg_result.one()

            session_list.append(
                {
                    "id": s.id,
                    "title": s.title,
                    "session_type": s.session_type,
                    "message_count": count or 0,
                    "last_message_at": last_msg,
                    "created_at": s.created_at,
                }
            )

        return session_list

    async def get_session_messages(
        self, db: AsyncSession, user_id: UUID, session_id: UUID
    ) -> List[ChatMessageResponse]:
        """Get all messages in a session."""
        # Verify ownership
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            raise ValueError("Session not found")

        result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()

        return [
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                sources=[ChatSource(**s) for s in m.sources] if m.sources else None,
                created_at=m.created_at,
            )
            for m in messages
        ]

    async def delete_session(self, db: AsyncSession, user_id: UUID, session_id: UUID) -> bool:
        """Delete a chat session."""
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user_id:
            return False

        await db.delete(session)
        await db.commit()
        return True
