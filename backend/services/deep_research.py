"""Deep research service for intelligent grant discovery."""

import openai
from datetime import datetime, timezone
from typing import Optional, List, AsyncIterator
from uuid import UUID
import time
import json
import asyncio
import structlog

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from backend.core.config import settings
from backend.models import User, Grant, LabProfile, ResearchSession
from backend.schemas.research import (
    ResearchStatus,
    ResearchGrantResult,
    ResearchSessionResponse,
    ResearchPhase,
)

logger = structlog.get_logger(__name__)


class DeepResearchService:
    """Service for intelligent grant discovery and research."""

    def __init__(self):
        self.openai = openai.OpenAI(api_key=settings.openai_api_key)

    async def create_session(self, db: AsyncSession, user: User, query: str) -> ResearchSession:
        """Create a new research session."""
        session = ResearchSession(
            user_id=user.id,
            query=query,
            status="pending",
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return session

    async def run_research(self, db: AsyncSession, session_id: UUID) -> ResearchSessionResponse:
        """Execute deep research for a session."""
        start_time = time.time()

        session = await db.get(ResearchSession, session_id)
        if not session:
            raise ValueError("Session not found")

        # Update status to processing
        session.status = "processing"
        await db.commit()

        try:
            # Get user profile for personalization
            profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == session.user_id))
            profile = profile_result.scalar_one_or_none()

            await db.get(User, session.user_id)

            # Step 1: Analyze and expand the query with Claude
            expanded_query = await self._expand_query(session.query, profile)

            # Step 2: Generate embedding for semantic search
            embedding = await self._generate_embedding(expanded_query)

            # Step 3: Search grants using vector similarity
            grants = await self._search_grants(db, embedding, profile)

            # Step 4: Score and rank results with Claude
            scored_results = await self._score_results(session.query, grants, profile)

            # Step 5: Generate insights
            insights = await self._generate_insights(session.query, scored_results, profile)

            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)

            # Update session with results
            session.status = "completed"
            session.results = [r.model_dump(mode="json") for r in scored_results]
            session.insights = insights
            session.grants_found = len(scored_results)
            session.processing_time_ms = processing_time
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(session)

            return ResearchSessionResponse(
                id=session.id,
                user_id=session.user_id,
                query=session.query,
                status=ResearchStatus(session.status),
                results=scored_results,
                insights=insights,
                grants_found=len(scored_results),
                processing_time_ms=processing_time,
                created_at=session.created_at,
                completed_at=session.completed_at,
            )

        except Exception as e:
            logger.error("Research failed", session_id=str(session_id), error=str(e))
            session.status = "failed"
            session.insights = f"Research failed: {str(e)}"
            await db.commit()
            raise

    async def run_research_with_progress(self, db: AsyncSession, session_id: UUID) -> AsyncIterator[dict]:
        """
        Execute deep research for a session with progress streaming.

        Yields SSE-formatted events for real-time progress updates.
        """
        start_time = time.time()

        session = await db.get(ResearchSession, session_id)
        if not session:
            yield {"event": "error", "data": {"error": "Session not found", "phase": ResearchPhase.PENDING.value}}
            return

        # Update status to processing
        session.status = "processing"
        await db.commit()

        try:
            # Emit initial status
            yield {"event": "status", "data": {"phase": ResearchPhase.PENDING.value, "message": "Starting research..."}}
            yield {"event": "progress", "data": {"percent": 5, "message": "Initializing research session"}}

            # Get user profile for personalization
            profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == session.user_id))
            profile = profile_result.scalar_one_or_none()
            await db.get(User, session.user_id)

            # Step 1: Analyze and expand the query with Claude
            yield {
                "event": "status",
                "data": {
                    "phase": ResearchPhase.EXPANDING_QUERY.value,
                    "message": "Analyzing and expanding your query...",
                },
            }
            yield {"event": "progress", "data": {"percent": 15, "message": "Expanding query with related terms"}}

            expanded_query = await self._expand_query(session.query, profile)

            # Step 2: Generate embedding for semantic search
            yield {
                "event": "status",
                "data": {
                    "phase": ResearchPhase.GENERATING_EMBEDDING.value,
                    "message": "Generating semantic embeddings...",
                },
            }
            yield {"event": "progress", "data": {"percent": 25, "message": "Creating search vectors"}}

            embedding = await self._generate_embedding(expanded_query)

            # Step 3: Search grants using vector similarity
            yield {
                "event": "status",
                "data": {"phase": ResearchPhase.SEARCHING.value, "message": "Searching grant database..."},
            }
            yield {"event": "progress", "data": {"percent": 40, "message": "Performing semantic search"}}

            grants = await self._search_grants(db, embedding, profile)

            # Emit found grants incrementally
            yield {"event": "progress", "data": {"percent": 50, "message": f"Found {len(grants)} potential matches"}}

            # Emit grants as they are found (in batches for efficiency)
            for i, grant in enumerate(grants[:10]):  # Stream first 10 immediately
                yield {
                    "event": "grant_found",
                    "data": {
                        "grant": {
                            "id": str(grant.id),
                            "title": grant.title,
                            "funder": grant.agency or "Unknown",
                            "mechanism": None,
                            "description": (grant.description or "")[:300],
                            "deadline": grant.deadline.isoformat() if grant.deadline else None,
                            "amount_min": grant.amount_min,
                            "amount_max": grant.amount_max,
                            "relevance_score": 0.5,  # Preliminary score
                            "match_reasons": ["Semantic match to your query"],
                        }
                    },
                }
                # Small delay to avoid overwhelming the client
                if i % 3 == 2:
                    await asyncio.sleep(0.05)

            # Step 4: Score and rank results with Claude
            yield {
                "event": "status",
                "data": {"phase": ResearchPhase.SCORING.value, "message": "AI is scoring and ranking results..."},
            }
            yield {"event": "progress", "data": {"percent": 65, "message": "Analyzing relevance with AI"}}

            scored_results = await self._score_results(session.query, grants, profile)

            yield {
                "event": "progress",
                "data": {"percent": 80, "message": f"Scored {len(scored_results)} relevant grants"},
            }

            # Step 5: Generate insights
            yield {
                "event": "status",
                "data": {
                    "phase": ResearchPhase.GENERATING_INSIGHTS.value,
                    "message": "Generating strategic insights...",
                },
            }
            yield {"event": "progress", "data": {"percent": 90, "message": "Creating recommendations"}}

            insights = await self._generate_insights(session.query, scored_results, profile)

            # Emit insights
            yield {"event": "insights", "data": {"insights": insights}}

            # Calculate processing time
            processing_time = int((time.time() - start_time) * 1000)

            # Update session with results
            session.status = "completed"
            session.results = [r.model_dump(mode="json") for r in scored_results]
            session.insights = insights
            session.grants_found = len(scored_results)
            session.processing_time_ms = processing_time
            session.completed_at = datetime.now(timezone.utc)
            await db.commit()

            # Emit completion
            yield {"event": "status", "data": {"phase": ResearchPhase.COMPLETED.value, "message": "Research complete!"}}
            yield {"event": "progress", "data": {"percent": 100, "message": "Research completed successfully"}}
            yield {
                "event": "complete",
                "data": {"grants_found": len(scored_results), "processing_time_ms": processing_time},
            }

        except Exception as e:
            logger.error("Research failed", session_id=str(session_id), error=str(e))
            session.status = "failed"
            session.insights = f"Research failed: {str(e)}"
            await db.commit()

            yield {
                "event": "status",
                "data": {"phase": ResearchPhase.FAILED.value, "message": f"Research failed: {str(e)}"},
            }
            yield {"event": "error", "data": {"error": str(e), "phase": ResearchPhase.FAILED.value}}

    async def _expand_query(self, query: str, profile: Optional[LabProfile]) -> str:
        """Expand query with related terms using Claude."""
        profile_context = ""
        if profile:
            profile_context = f"""
Researcher's background:
- Research areas: {", ".join(profile.research_areas or [])}
- Institution: {profile.institution or "Unknown"}
- Career stage: {profile.career_stage or "Unknown"}
"""

        prompt = f"""You are a grant search expert. Expand this research query with relevant funding-related terms and synonyms.

Original query: "{query}"
{profile_context}

Provide an expanded search query that captures:
1. Related research areas and methodologies
2. Relevant funding mechanisms (R01, R21, K-series, etc.)
3. Common grant terminology
4. Potential funding agencies

Return ONLY the expanded query text, no explanations. Keep it under 300 words."""

        try:
            response = self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.warning("Query expansion failed", error=str(e))
            return query

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for semantic search."""
        response = self.openai.embeddings.create(
            model=settings.embedding_model,
            input=text[:8000],  # Truncate to model limit
        )
        return response.data[0].embedding

    async def _search_grants(
        self,
        db: AsyncSession,
        embedding: List[float],
        profile: Optional[LabProfile],
    ) -> List[Grant]:
        """Search grants using vector similarity."""
        # Convert embedding list to pgvector format string
        embedding_str = "[" + ",".join(map(str, embedding)) + "]"

        # Use pgvector for semantic search
        query = text("""
            SELECT id, title, description, agency, amount_min, amount_max,
                   deadline, url, eligibility,
                   1 - (embedding <=> CAST(:embedding AS vector)) as similarity
            FROM grants
            WHERE embedding IS NOT NULL
              AND (deadline IS NULL OR deadline > NOW())
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT 50
        """)

        result = await db.execute(query, {"embedding": embedding_str})
        rows = result.fetchall()

        grants = []
        for row in rows:
            if row.similarity > 0.3:  # Minimum relevance threshold
                grant = await db.get(Grant, row.id)
                if grant:
                    grants.append(grant)

        return grants

    async def _score_results(
        self,
        original_query: str,
        grants: List[Grant],
        profile: Optional[LabProfile],
    ) -> List[ResearchGrantResult]:
        """Score and rank results using Claude."""
        if not grants:
            return []

        # Build grants context for Claude
        grants_text = ""
        for i, g in enumerate(grants[:20]):  # Limit for token management
            grants_text += f"""
{i + 1}. {g.title}
   Agency: {g.agency or "Unknown"}
   Deadline: {g.deadline.strftime("%Y-%m-%d") if g.deadline else "Open"}
   Amount: ${g.amount_min or 0:,} - ${g.amount_max or 0:,}
   Description: {(g.description or "")[:200]}
   Eligibility: {str(g.eligibility or "")[:100]}
---"""

        profile_context = ""
        if profile:
            profile_context = f"""
Researcher profile:
- Research areas: {", ".join(profile.research_areas or [])}
- Career stage: {profile.career_stage or "Unknown"}
- Institution: {profile.institution or "Unknown"}
"""

        prompt = f"""You are a grant matching expert. Score these grants for relevance to the research query.

Research Query: "{original_query}"
{profile_context}

Grants to score:
{grants_text}

For each grant, provide a JSON array with objects containing:
- index: the grant number (1-based)
- relevance_score: 0.0-1.0 score for how well it matches the query
- match_reasons: array of 2-3 specific reasons it's relevant

Return ONLY the JSON array, no other text. Example:
[{{"index": 1, "relevance_score": 0.85, "match_reasons": ["Strong alignment with cancer research", "Supports early-career investigators"]}}]"""

        try:
            response = self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=2000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Parse OpenAI's response
            response_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            json_start = response_text.find("[")
            json_end = response_text.rfind("]") + 1
            scores_data = json.loads(response_text[json_start:json_end])

            # Build scored results
            results = []
            for score_item in scores_data:
                idx = score_item["index"] - 1
                if 0 <= idx < len(grants):
                    grant = grants[idx]
                    results.append(
                        ResearchGrantResult(
                            id=grant.id,
                            title=grant.title,
                            funder=grant.agency or "Unknown",
                            mechanism=None,  # Extract from grant if available
                            description=(grant.description or "")[:500],
                            deadline=grant.deadline,
                            amount_min=grant.amount_min,
                            amount_max=grant.amount_max,
                            relevance_score=score_item["relevance_score"],
                            match_reasons=score_item["match_reasons"],
                        )
                    )

            # Sort by relevance score
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            return results[:20]  # Top 20 results

        except Exception as e:
            logger.error("Scoring failed", error=str(e))
            # Return unsorted results with default scores
            return [
                ResearchGrantResult(
                    id=g.id,
                    title=g.title,
                    funder=g.agency or "Unknown",
                    mechanism=None,
                    description=(g.description or "")[:500],
                    deadline=g.deadline,
                    amount_min=g.amount_min,
                    amount_max=g.amount_max,
                    relevance_score=0.5,
                    match_reasons=["Semantic match to your query"],
                )
                for g in grants[:20]
            ]

    async def _generate_insights(
        self,
        query: str,
        results: List[ResearchGrantResult],
        profile: Optional[LabProfile],
    ) -> str:
        """Generate actionable insights from research results."""
        if not results:
            return "No matching grants found. Consider broadening your search terms or exploring different funding agencies."

        # Summarize results for Claude
        results_summary = "\n".join([f"- {r.title} ({r.funder}, score: {r.relevance_score:.0%})" for r in results[:10]])

        funders = list(set(r.funder for r in results))

        prompt = f"""You are a grant strategy advisor. Based on these research results, provide 3-4 actionable insights.

Research query: "{query}"
Found {len(results)} relevant grants

Top results:
{results_summary}

Funders represented: {", ".join(funders[:5])}

Provide insights about:
1. Most promising opportunities
2. Timing/deadline patterns
3. Funding agency trends
4. Strategic recommendations

Keep response under 200 words. Be specific and actionable."""

        try:
            response = self.openai.chat.completions.create(
                model=settings.llm_model,
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error("Insights generation failed", error=str(e))
            return f"Found {len(results)} relevant grants across {len(funders)} funders."

    async def quick_search(
        self,
        db: AsyncSession,
        user: User,
        query: str,
        max_results: int = 10,
    ) -> List[ResearchGrantResult]:
        """Quick synchronous search without full research pipeline."""
        # Get profile
        profile_result = await db.execute(select(LabProfile).where(LabProfile.user_id == user.id))
        profile = profile_result.scalar_one_or_none()

        # Generate embedding
        embedding = await self._generate_embedding(query)

        # Search grants
        grants = await self._search_grants(db, embedding, profile)

        # Simple scoring without Claude (faster)
        return [
            ResearchGrantResult(
                id=g.id,
                title=g.title,
                funder=g.agency or "Unknown",
                mechanism=None,
                description=(g.description or "")[:300],
                deadline=g.deadline,
                amount_min=g.amount_min,
                amount_max=g.amount_max,
                relevance_score=0.7,  # Placeholder
                match_reasons=["Semantic match to your search"],
            )
            for g in grants[:max_results]
        ]

    async def get_sessions(self, db: AsyncSession, user_id: UUID, limit: int = 20) -> List[ResearchSession]:
        """Get user's research sessions."""
        result = await db.execute(
            select(ResearchSession)
            .where(ResearchSession.user_id == user_id)
            .order_by(ResearchSession.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()
