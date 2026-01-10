"""
AI-powered grant insights service with streaming support.
Generates eligibility analysis and writing tips for grant applications.
Uses Anthropic Claude for AI-powered analysis.
"""

import json
from typing import AsyncGenerator, Optional, Literal
from uuid import UUID

import anthropic
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models import User, Grant, Match, LabProfile

logger = structlog.get_logger(__name__)


class GrantInsightsService:
    """Service for generating AI-powered grant insights with streaming."""

    def __init__(self):
        if not settings.anthropic_api_key:
            logger.warning("ANTHROPIC_API_KEY not configured - AI insights will not work")
            self.client = None
        else:
            self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    async def stream_insights(
        self,
        db: AsyncSession,
        user: User,
        grant_id: UUID,
        insight_type: Literal["eligibility", "writing_tips", "both"] = "both",
    ) -> AsyncGenerator[dict, None]:
        """
        Stream AI-generated insights for a grant.

        Yields SSE-formatted events:
        - {"event": "eligibility_start", "data": {}}
        - {"event": "eligibility_chunk", "data": {"content": "..."}}
        - {"event": "eligibility_end", "data": {}}
        - {"event": "writing_start", "data": {}}
        - {"event": "writing_chunk", "data": {"content": "..."}}
        - {"event": "writing_end", "data": {}}
        - {"event": "error", "data": {"message": "..."}}
        """
        # Check if API client is configured
        if not self.client:
            yield {
                "event": "error",
                "data": {
                    "message": "AI insights are not available. Please configure your ANTHROPIC_API_KEY in the .env file."
                },
            }
            return

        # Fetch grant details
        grant = await db.get(Grant, grant_id)
        if not grant:
            yield {"event": "error", "data": {"message": f"Grant {grant_id} not found"}}
            return

        # Fetch user's lab profile
        profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        # Fetch match info if available
        match_result = await db.execute(select(Match).where(Match.grant_id == grant_id, Match.user_id == user.id))
        match = match_result.scalar_one_or_none()

        # Build context strings
        researcher_context = self._build_researcher_context(user, profile)
        grant_context = self._build_grant_context(grant, match)

        # Generate eligibility analysis
        if insight_type in ("eligibility", "both"):
            yield {"event": "eligibility_start", "data": {}}
            try:
                async for chunk in self._stream_eligibility_analysis(researcher_context, grant_context, grant):
                    yield {"event": "eligibility_chunk", "data": {"content": chunk}}
                yield {"event": "eligibility_end", "data": {}}
            except Exception as e:
                logger.error("Eligibility analysis failed", error=str(e))
                yield {"event": "error", "data": {"message": f"Eligibility analysis failed: {str(e)}"}}

        # Generate writing tips
        if insight_type in ("writing_tips", "both"):
            yield {"event": "writing_start", "data": {}}
            try:
                async for chunk in self._stream_writing_tips(researcher_context, grant_context, grant):
                    yield {"event": "writing_chunk", "data": {"content": chunk}}
                yield {"event": "writing_end", "data": {}}
            except Exception as e:
                logger.error("Writing tips generation failed", error=str(e))
                yield {"event": "error", "data": {"message": f"Writing tips failed: {str(e)}"}}

    async def _stream_eligibility_analysis(
        self,
        researcher_context: str,
        grant_context: str,
        grant: Grant,
    ) -> AsyncGenerator[str, None]:
        """Stream eligibility analysis using Anthropic Claude."""
        prompt = f"""You are an expert grant eligibility advisor. Analyze whether this researcher is eligible for the given grant opportunity.

RESEARCHER PROFILE:
{researcher_context}

GRANT OPPORTUNITY:
{grant_context}

Provide a detailed eligibility analysis with:

## Overall Assessment
Start with a clear verdict: **Eligible**, **Likely Eligible**, **Uncertain**, or **Not Eligible** along with your confidence level (High/Medium/Low).

## Requirements Check
Go through each major eligibility criterion systematically:
- Career stage requirements
- Institutional requirements
- Citizenship/visa requirements (if mentioned)
- Previous funding limitations
- Research area alignment
- Any specific mechanism requirements

For each, indicate if the requirement is **Met**, **Likely Met**, **Unknown**, or **Not Met**.

## Gaps Identified
List any missing qualifications, potential issues, or areas of concern.

## Action Items
Provide specific steps the researcher should take to:
1. Confirm their eligibility
2. Address any gaps
3. Strengthen their position

Be honest about uncertainty. If key information is missing, clearly state what additional details would help determine eligibility more accurately.

Use markdown formatting with headers, bullet points, and bold text for emphasis."""

        # Use Anthropic Claude streaming
        with self.client.messages.stream(
            model=settings.llm_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    async def _stream_writing_tips(
        self,
        researcher_context: str,
        grant_context: str,
        grant: Grant,
    ) -> AsyncGenerator[str, None]:
        """Stream writing tips using Anthropic Claude."""
        agency = grant.agency or "this funder"

        prompt = f"""You are an expert grant writing consultant with deep knowledge of {agency}'s funding priorities and preferences.

GRANT DETAILS:
{grant_context}

RESEARCHER PROFILE:
{researcher_context}

Provide actionable, specific writing tips for this grant application:

## Key Themes to Emphasize
Based on {agency}'s priorities and this grant's focus, identify 3-4 key themes the applicant should emphasize throughout their proposal.

## Research Alignment
How should the researcher position their work to align with this opportunity? What aspects of their background should they highlight?

## Methodology Suggestions
Tips for the technical/methodology section:
- Approaches that resonate with {agency}
- Level of detail expected
- Innovation vs. feasibility balance

## Broader Impacts
What broader impact areas are most relevant for this funder? How should the applicant frame their work's significance?

## Common Pitfalls to Avoid
What mistakes do applicants commonly make with {agency} or this type of grant? What should they be careful to avoid?

## Specific Recommendations
Based on the researcher's profile, provide 3-5 personalized recommendations that would strengthen this specific application.

Make all suggestions specific to this grant and researcher combination. Use markdown formatting with headers and bullet points."""

        # Use Anthropic Claude streaming
        with self.client.messages.stream(
            model=settings.llm_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text

    def _build_researcher_context(self, user: User, profile: Optional[LabProfile]) -> str:
        """Build context string about the researcher."""
        parts = [f"Name: {user.name or user.email}"]

        # Check for optional user attributes that may not exist
        organization_type = getattr(user, "organization_type", None)
        if organization_type:
            parts.append(f"Organization Type: {organization_type}")
        focus_areas = getattr(user, "focus_areas", None)
        if focus_areas:
            parts.append(f"Focus Areas: {', '.join(focus_areas)}")

        if profile:
            if profile.institution:
                parts.append(f"Institution: {profile.institution}")
            if profile.department:
                parts.append(f"Department: {profile.department}")
            if profile.research_areas:
                parts.append(f"Research Areas: {', '.join(profile.research_areas)}")
            if profile.methods:
                parts.append(f"Methods/Techniques: {', '.join(profile.methods)}")
            if profile.career_stage:
                parts.append(f"Career Stage: {profile.career_stage}")
            if profile.orcid:
                parts.append(f"ORCID: {profile.orcid}")
            if profile.publications:
                pub_info = profile.publications
                if isinstance(pub_info, dict):
                    pub_count = pub_info.get("count", 0)
                    if pub_count:
                        parts.append(f"Publications: {pub_count}")
                    h_index = pub_info.get("h_index")
                    if h_index:
                        parts.append(f"H-Index: {h_index}")
            if profile.past_grants:
                grants_info = profile.past_grants
                if isinstance(grants_info, list) and grants_info:
                    parts.append(f"Past Grants: {len(grants_info)} previous awards")
                    # Include brief summary of past grants
                    for g in grants_info[:3]:
                        if isinstance(g, dict):
                            title = g.get("title", "Unknown")
                            agency = g.get("agency", "")
                            parts.append(f"  - {title} ({agency})")
            if profile.keywords:
                parts.append(f"Keywords: {', '.join(profile.keywords[:10])}")

        if not profile:
            parts.append("Note: Limited profile information available. More details would improve analysis accuracy.")

        return "\n".join(parts)

    def _build_grant_context(self, grant: Grant, match: Optional[Match] = None) -> str:
        """Build context string about the grant."""
        parts = [
            f"Title: {grant.title}",
            f"Funder/Agency: {grant.agency or 'Unknown'}",
        ]

        if grant.source:
            parts.append(f"Source: {grant.source}")

        if grant.description:
            # Truncate very long descriptions
            desc = grant.description[:2000]
            if len(grant.description) > 2000:
                desc += "..."
            parts.append(f"Description: {desc}")

        if grant.eligibility:
            if isinstance(grant.eligibility, dict):
                eligibility_str = json.dumps(grant.eligibility, indent=2)
            else:
                eligibility_str = str(grant.eligibility)
            parts.append(f"Eligibility Requirements:\n{eligibility_str}")

        if grant.amount_min or grant.amount_max:
            amount_str = ""
            if grant.amount_min and grant.amount_max:
                amount_str = f"${grant.amount_min:,} - ${grant.amount_max:,}"
            elif grant.amount_max:
                amount_str = f"Up to ${grant.amount_max:,}"
            elif grant.amount_min:
                amount_str = f"At least ${grant.amount_min:,}"
            parts.append(f"Funding Amount: {amount_str}")

        if grant.deadline:
            parts.append(f"Deadline: {grant.deadline.strftime('%B %d, %Y')}")

        if grant.categories:
            parts.append(f"Categories: {', '.join(grant.categories)}")

        # Include match info if available
        if match:
            if match.match_score:
                parts.append(f"Match Score: {int(match.match_score * 100)}%")
            if match.reasoning:
                parts.append(f"Match Reasoning: {match.reasoning}")
            if match.key_strengths:
                parts.append(f"Key Strengths: {', '.join(match.key_strengths)}")
            if match.concerns:
                parts.append(f"Concerns: {', '.join(match.concerns)}")

        return "\n".join(parts)


# Singleton instance
_insights_service: Optional[GrantInsightsService] = None


def get_insights_service() -> GrantInsightsService:
    """Get or create the insights service singleton."""
    global _insights_service
    if _insights_service is None:
        _insights_service = GrantInsightsService()
    return _insights_service
