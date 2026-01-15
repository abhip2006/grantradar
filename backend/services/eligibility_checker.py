"""Eligibility checking service using OpenAI."""

import openai
import json
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.core.config import settings
from backend.models import User, Grant, LabProfile, ChatSession, ChatMessage
from backend.schemas.eligibility import (
    EligibilityStatus,
    EligibilityCriterion,
    EligibilityCheckResponse,
    EligibilityFollowUpResponse,
)

logger = structlog.get_logger(__name__)


class EligibilityChecker:
    """Service to check researcher eligibility for grants using AI."""

    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.openai_api_key)

    async def check_eligibility(
        self,
        db: AsyncSession,
        user: User,
        grant_id: UUID,
        additional_context: Optional[str] = None,
    ) -> EligibilityCheckResponse:
        """Check if a researcher is eligible for a specific grant."""

        # Fetch grant details
        grant = await db.get(Grant, grant_id)
        if not grant:
            raise ValueError(f"Grant {grant_id} not found")

        # Fetch user's lab profile
        profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        # Build researcher context
        researcher_context = self._build_researcher_context(user, profile, additional_context)

        # Build grant context
        grant_context = self._build_grant_context(grant)

        # Create prompt for OpenAI
        prompt = self._build_eligibility_prompt(researcher_context, grant_context)

        # Call OpenAI
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse response
        result = self._parse_eligibility_response(response.choices[0].message.content, grant)

        # Create chat session for follow-up questions
        session = ChatSession(
            user_id=user.id,
            title=f"Eligibility: {grant.title[:50]}",
            session_type="eligibility",
            context_grant_id=grant_id,
            metadata_={"grant_title": grant.title, "initial_status": result.overall_status.value},
        )
        db.add(session)
        # Flush to ensure session.id is assigned before creating messages
        await db.flush()

        # Save initial exchange
        user_msg = ChatMessage(session_id=session.id, role="user", content=f"Check my eligibility for: {grant.title}")
        assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=result.summary)
        db.add_all([user_msg, assistant_msg])
        await db.commit()
        await db.refresh(session)

        result.session_id = session.id
        return result

    def _build_researcher_context(
        self, user: User, profile: Optional[LabProfile], additional_context: Optional[str]
    ) -> str:
        """Build context string about the researcher."""
        parts = [f"Researcher: {user.name or user.email}"]

        if profile:
            if profile.department:
                parts.append(f"Department: {profile.department}")
            if profile.institution:
                parts.append(f"Institution: {profile.institution}")
            if profile.research_areas:
                parts.append(f"Research Areas: {', '.join(profile.research_areas)}")
            if profile.career_stage:
                parts.append(f"Career Stage: {profile.career_stage}")
            if profile.orcid:
                parts.append(f"Has ORCID: {profile.orcid}")
            if profile.publications:
                pub_count = profile.publications.get("count", 0) if isinstance(profile.publications, dict) else 0
                if pub_count:
                    parts.append(f"Publications: {pub_count}")
            if profile.past_grants:
                parts.append(f"Previous Funding: {json.dumps(profile.past_grants)}")

        if additional_context:
            parts.append(f"Additional Info: {additional_context}")

        return "\n".join(parts)

    def _build_grant_context(self, grant: Grant) -> str:
        """Build context string about the grant."""
        parts = [
            f"Grant Title: {grant.title}",
            f"Funder: {grant.agency or 'Unknown'}",
        ]

        if grant.source:
            parts.append(f"Source: {grant.source}")
        if grant.description:
            parts.append(f"Description: {grant.description[:1000]}")
        if grant.eligibility:
            eligibility_str = (
                json.dumps(grant.eligibility) if isinstance(grant.eligibility, dict) else str(grant.eligibility)
            )
            parts.append(f"Eligibility Requirements: {eligibility_str}")
        if grant.amount_min or grant.amount_max:
            parts.append(f"Funding: ${grant.amount_min or 0:,} - ${grant.amount_max or 0:,}")
        if grant.deadline:
            parts.append(f"Deadline: {grant.deadline.strftime('%Y-%m-%d')}")
        if grant.categories:
            parts.append(f"Categories: {', '.join(grant.categories)}")

        return "\n".join(parts)

    def _build_eligibility_prompt(self, researcher_context: str, grant_context: str) -> str:
        """Build the prompt for eligibility checking."""
        return f"""You are an expert grant eligibility advisor. Analyze whether this researcher is eligible for the given grant opportunity.

RESEARCHER PROFILE:
{researcher_context}

GRANT OPPORTUNITY:
{grant_context}

Analyze the eligibility and provide your assessment in the following JSON format:
{{
    "overall_status": "eligible" | "not_eligible" | "partial" | "unknown",
    "overall_confidence": 0.0-1.0,
    "criteria": [
        {{
            "criterion": "Career stage requirement",
            "met": true/false,
            "explanation": "Brief explanation",
            "confidence": 0.0-1.0
        }}
    ],
    "summary": "2-3 sentence summary of eligibility",
    "recommendations": ["List of specific steps to strengthen application or meet requirements"],
    "missing_info": ["List of information that would help determine eligibility more accurately"]
}}

Focus on:
1. Career stage requirements (PI status, years since degree)
2. Institutional requirements
3. Citizenship/visa requirements if mentioned
4. Previous funding limitations
5. Research area alignment
6. Any specific mechanism requirements (R01, R21, K-series, etc.)

Be honest about uncertainty - use "unknown" status if key information is missing."""

    def _parse_eligibility_response(self, response_text: str, grant: Grant) -> EligibilityCheckResponse:
        """Parse Claude's response into structured format."""
        try:
            # Extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            json_str = response_text[json_start:json_end]
            data = json.loads(json_str)

            criteria = [EligibilityCriterion(**c) for c in data.get("criteria", [])]

            return EligibilityCheckResponse(
                grant_id=grant.id,
                grant_title=grant.title,
                overall_status=EligibilityStatus(data.get("overall_status", "unknown")),
                overall_confidence=data.get("overall_confidence", 0.5),
                criteria=criteria,
                summary=data.get("summary", "Unable to determine eligibility."),
                recommendations=data.get("recommendations", []),
                missing_info=data.get("missing_info", []),
                checked_at=datetime.now(timezone.utc),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Failed to parse eligibility response", error=str(e))
            return EligibilityCheckResponse(
                grant_id=grant.id,
                grant_title=grant.title,
                overall_status=EligibilityStatus.UNKNOWN,
                overall_confidence=0.0,
                criteria=[],
                summary="Unable to parse eligibility analysis. Please try again.",
                recommendations=[],
                missing_info=["Full eligibility analysis unavailable"],
                checked_at=datetime.now(timezone.utc),
            )

    async def follow_up(
        self,
        db: AsyncSession,
        user: User,
        session_id: UUID,
        message: str,
    ) -> EligibilityFollowUpResponse:
        """Handle follow-up questions in eligibility conversation."""

        # Fetch session with messages
        session = await db.get(ChatSession, session_id)
        if not session or session.user_id != user.id:
            raise ValueError("Session not found")

        # Get conversation history
        messages_result = await db.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at)
        )
        history = messages_result.scalars().all()

        # Build conversation for Claude
        claude_messages = []
        for msg in history:
            claude_messages.append({"role": msg.role if msg.role != "system" else "user", "content": msg.content})
        claude_messages.append({"role": "user", "content": message})

        # Get grant context if available
        grant = None
        if session.context_grant_id:
            grant = await db.get(Grant, session.context_grant_id)

        system_prompt = f"""You are an expert grant eligibility advisor helping a researcher understand their eligibility for a grant.

Grant: {grant.title if grant else "Unknown"}
Funder: {grant.agency if grant else "Unknown"}

Continue the conversation naturally, answering questions about eligibility, requirements, and how to strengthen their application.
If they provide new information about themselves, update your eligibility assessment accordingly."""

        # Call OpenAI
        messages = [{"role": "system", "content": system_prompt}] + claude_messages
        response = self.client.chat.completions.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            messages=messages,
        )

        response_text = response.choices[0].message.content

        # Save messages
        user_msg = ChatMessage(session_id=session_id, role="user", content=message)
        assistant_msg = ChatMessage(session_id=session_id, role="assistant", content=response_text)
        db.add_all([user_msg, assistant_msg])
        await db.commit()

        return EligibilityFollowUpResponse(
            session_id=session_id,
            response=response_text,
        )
