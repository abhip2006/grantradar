"""
Grant Matching Engine
Matches grants to user profiles using vector similarity and LLM re-ranking.
"""

import json
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import anthropic
import redis
import structlog
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.core.events import MatchComputedEvent, PriorityLevel

from .models import (
    BatchMatchRequest,
    BatchMatchResponse,
    FinalMatch,
    GrantData,
    MatchResult,
    ProfileMatch,
    UserProfile,
)

logger = structlog.get_logger().bind(agent="matcher")


class GrantMatcher:
    """
    Grant matching engine.

    Implements two-phase matching:
    1. Vector similarity search using pgvector (top 50 candidates)
    2. LLM re-ranking using Claude (top 20 for detailed evaluation)

    Final score: 40% vector similarity + 60% LLM match score
    """

    # Redis stream names
    VALIDATED_GRANTS_STREAM = "grants:validated"
    MATCHES_STREAM = "matches:computed"
    CONSUMER_GROUP = "matching_engine"
    CONSUMER_NAME = "matcher"

    # Matching thresholds
    VECTOR_SIMILARITY_THRESHOLD = 0.6
    TOP_CANDIDATES_LIMIT = 50
    LLM_RERANK_LIMIT = 20
    FINAL_MATCH_THRESHOLD = 70  # Score > 70 gets published

    # Batch processing
    LLM_BATCH_SIZE = 5  # Profiles per LLM call

    def __init__(self, db_engine: Engine):
        """
        Initialize matcher.

        Args:
            db_engine: SQLAlchemy engine for database operations.
        """
        self.db_engine = db_engine
        self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._redis_client: Optional[redis.Redis] = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy-loaded Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
            )
        return self._redis_client

    def _ensure_consumer_group(self) -> None:
        """Ensure Redis consumer group exists."""
        try:
            self.redis_client.xgroup_create(
                self.VALIDATED_GRANTS_STREAM,
                self.CONSUMER_GROUP,
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    def fetch_grant_data(self, grant_id: UUID, session: Session) -> Optional[GrantData]:
        """
        Fetch grant data from database.

        Args:
            grant_id: Grant identifier.
            session: Database session.

        Returns:
            GrantData if found, None otherwise.
        """
        query = text("""
            SELECT
                id as grant_id,
                title,
                description,
                agency,
                amount_min,
                amount_max,
                deadline,
                eligibility,
                categories,
                embedding
            FROM grants
            WHERE id = :grant_id
        """)

        result = session.execute(query, {"grant_id": str(grant_id)}).fetchone()

        if not result:
            logger.warning("grant_not_found", grant_id=str(grant_id))
            return None

        # Extract keywords from categories if available
        keywords = []
        if result.categories:
            keywords = result.categories

        # Parse eligibility criteria
        eligibility_criteria = []
        if result.eligibility:
            elig = result.eligibility
            if isinstance(elig, dict) and elig.get("applicant_types"):
                eligibility_criteria = elig["applicant_types"]

        return GrantData(
            grant_id=grant_id,
            title=result.title,
            description=result.description or "",
            funding_agency=result.agency,
            funding_amount=result.amount_max or result.amount_min,
            deadline=result.deadline,
            eligibility_criteria=eligibility_criteria,
            categories=result.categories or [],
            keywords=keywords,
            embedding=result.embedding,
        )

    def find_similar_profiles(self, grant_embedding: list[float], session: Session) -> list[ProfileMatch]:
        """
        Find user profiles similar to grant using pgvector.

        Uses cosine similarity to find top 50 matches above threshold.

        Args:
            grant_embedding: Grant embedding vector.
            session: Database session.

        Returns:
            List of ProfileMatch with similarity scores.
        """
        # Convert embedding to pgvector format
        embedding_str = "[" + ",".join(map(str, grant_embedding)) + "]"

        query = text("""
            SELECT
                lp.user_id,
                1 - (lp.profile_embedding <=> :grant_embedding::vector) AS similarity,
                lp.research_areas,
                lp.methods,
                lp.past_grants,
                lp.institution,
                lp.department,
                lp.keywords
            FROM lab_profiles lp
            WHERE lp.profile_embedding IS NOT NULL
              AND 1 - (lp.profile_embedding <=> :grant_embedding::vector) > :threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """)

        results = session.execute(
            query,
            {
                "grant_embedding": embedding_str,
                "threshold": self.VECTOR_SIMILARITY_THRESHOLD,
                "limit": self.TOP_CANDIDATES_LIMIT,
            },
        ).fetchall()

        matches = []
        for row in results:
            profile = UserProfile(
                user_id=UUID(row.user_id),
                research_areas=row.research_areas or [],
                methods=row.methods or [],
                past_grants=row.past_grants or [],
                institution=row.institution,
                department=row.department,
                keywords=row.keywords or [],
            )
            matches.append(
                ProfileMatch(
                    user_id=profile.user_id,
                    vector_similarity=float(row.similarity),
                    profile=profile,
                )
            )

        logger.info(
            "vector_search_complete",
            candidates_found=len(matches),
            threshold=self.VECTOR_SIMILARITY_THRESHOLD,
        )

        return matches

    def _build_llm_prompt(self, grant: GrantData, profiles: list[ProfileMatch]) -> str:
        """
        Build LLM prompt for batch match evaluation.

        Args:
            grant: Grant data.
            profiles: List of profiles to evaluate.

        Returns:
            Formatted prompt string.
        """
        profiles_text = ""
        for i, pm in enumerate(profiles, 1):
            profiles_text += f"\n--- Profile {i} (User ID: {pm.user_id}) ---\n"
            profiles_text += pm.profile.to_embedding_text()
            profiles_text += f"\nVector Similarity: {pm.vector_similarity:.3f}\n"

        return f"""You are evaluating grant-researcher matches for a grant intelligence platform.

GRANT INFORMATION:
{grant.to_matching_text()}

RESEARCHER PROFILES TO EVALUATE:
{profiles_text}

For each profile, evaluate the fit between the researcher and this grant opportunity.

Return a JSON array with one object per profile, in the same order as provided:
[
  {{
    "user_id": "<user_id>",
    "match_score": <0-100>,
    "reasoning": "<detailed explanation>",
    "key_strengths": ["<strength1>", "<strength2>", ...],
    "concerns": ["<concern1>", "<concern2>", ...],
    "predicted_success": <0-100>
  }},
  ...
]

Scoring Guidelines:
- 90-100: Exceptional fit - researcher's expertise directly aligns with grant focus
- 70-89: Strong fit - significant overlap in research areas and methods
- 50-69: Moderate fit - some relevant experience but gaps exist
- 30-49: Weak fit - limited alignment, would require significant adaptation
- 0-29: Poor fit - minimal relevance to researcher's expertise

Consider:
1. Research area alignment
2. Methodological expertise match
3. Prior grant experience relevance
4. Institutional fit and resources
5. Eligibility criteria match

Return ONLY the JSON array, no additional text."""

    def evaluate_matches_batch(self, request: BatchMatchRequest) -> BatchMatchResponse:
        """
        Evaluate multiple profile matches using Claude.

        Args:
            request: Batch match request with grant and profiles.

        Returns:
            BatchMatchResponse with results for all profiles.
        """
        start_time = time.time()

        prompt = self._build_llm_prompt(request.grant, request.profiles)

        try:
            response = self.anthropic_client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[
                    {"role": "user", "content": prompt},
                ],
            )

            # Parse response
            response_text = response.content[0].text
            results_json = json.loads(response_text)

            results = []
            for item in results_json:
                user_id = UUID(item["user_id"])
                match_result = MatchResult(
                    match_score=item["match_score"],
                    reasoning=item["reasoning"],
                    key_strengths=item.get("key_strengths", []),
                    concerns=item.get("concerns", []),
                    predicted_success=item["predicted_success"],
                )
                results.append((user_id, match_result))

            processing_time = (time.time() - start_time) * 1000

            return BatchMatchResponse(
                grant_id=request.grant.grant_id,
                results=results,
                processing_time_ms=processing_time,
            )

        except json.JSONDecodeError as e:
            logger.error(
                "llm_response_parse_error",
                grant_id=str(request.grant.grant_id),
                error=str(e),
            )
            raise
        except anthropic.APIError as e:
            logger.error(
                "llm_api_error",
                grant_id=str(request.grant.grant_id),
                error=str(e),
            )
            raise

    def _compute_priority_level(self, match_score: float, deadline: Optional[datetime]) -> PriorityLevel:
        """
        Compute priority level based on score and deadline.

        Args:
            match_score: Final match score (0-100).
            deadline: Grant deadline.

        Returns:
            PriorityLevel enum value.
        """
        now = datetime.now(timezone.utc)
        days_until_deadline = None

        if deadline:
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            delta = deadline - now
            days_until_deadline = delta.days

        # Critical: High score + urgent deadline
        if match_score >= 90 and days_until_deadline is not None:
            if days_until_deadline <= 7:
                return PriorityLevel.CRITICAL

        # High: Good score or moderate deadline
        if match_score >= 80:
            return PriorityLevel.HIGH
        if days_until_deadline is not None and days_until_deadline <= 30:
            return PriorityLevel.HIGH

        # Medium: Decent match
        if match_score >= 70:
            return PriorityLevel.MEDIUM

        return PriorityLevel.LOW

    def store_match(self, match: FinalMatch, session: Session) -> None:
        """
        Store match in database.

        Args:
            match: Final match to store.
            session: Database session.
        """
        query = text("""
            INSERT INTO matches (
                id,
                grant_id,
                user_id,
                match_score,
                vector_similarity,
                llm_match_score,
                reasoning,
                key_strengths,
                concerns,
                predicted_success,
                created_at
            ) VALUES (
                :id,
                :grant_id,
                :user_id,
                :match_score,
                :vector_similarity,
                :llm_match_score,
                :reasoning,
                :key_strengths,
                :concerns,
                :predicted_success,
                :created_at
            )
            ON CONFLICT (grant_id, user_id) DO UPDATE SET
                match_score = EXCLUDED.match_score,
                vector_similarity = EXCLUDED.vector_similarity,
                llm_match_score = EXCLUDED.llm_match_score,
                reasoning = EXCLUDED.reasoning,
                key_strengths = EXCLUDED.key_strengths,
                concerns = EXCLUDED.concerns,
                predicted_success = EXCLUDED.predicted_success,
                created_at = EXCLUDED.created_at
        """)

        session.execute(
            query,
            {
                "id": str(match.match_id),
                "grant_id": str(match.grant_id),
                "user_id": str(match.user_id),
                "match_score": match.final_score,
                "vector_similarity": match.vector_similarity,
                "llm_match_score": match.llm_match_score,
                "reasoning": match.reasoning,
                "key_strengths": match.key_strengths,
                "concerns": match.concerns,
                "predicted_success": match.predicted_success,
                "created_at": match.created_at,
            },
        )

    def publish_match(
        self,
        match: FinalMatch,
        grant: GrantData,
    ) -> str:
        """
        Publish match to Redis stream for downstream processing.

        Args:
            match: Final match to publish.
            grant: Grant data for priority calculation.

        Returns:
            Redis stream message ID.
        """
        priority = self._compute_priority_level(match.final_score, grant.deadline)

        event = MatchComputedEvent(
            event_id=uuid4(),
            match_id=match.match_id,
            grant_id=match.grant_id,
            user_id=match.user_id,
            match_score=match.final_score / 100,  # Normalize to 0-1
            priority_level=priority,
            matching_criteria=match.key_strengths,
            explanation=match.reasoning,
            grant_deadline=grant.deadline,
        )

        message = {"data": event.model_dump_json()}
        message_id = self.redis_client.xadd(self.MATCHES_STREAM, message)

        logger.info(
            "match_published",
            match_id=str(match.match_id),
            user_id=str(match.user_id),
            score=match.final_score,
            priority=priority.value,
            message_id=message_id,
        )

        return message_id

    def process_grant(self, grant_id: UUID) -> dict[str, Any]:
        """
        Process a grant for matching with all user profiles.

        Main entry point for grant matching workflow.

        Args:
            grant_id: Grant identifier.

        Returns:
            Statistics about the matching operation.
        """
        start_time = time.time()
        stats = {
            "grant_id": str(grant_id),
            "candidates_found": 0,
            "llm_evaluated": 0,
            "matches_stored": 0,
            "matches_published": 0,
            "processing_time_seconds": 0,
        }

        with Session(self.db_engine) as session:
            # Fetch grant data
            grant = self.fetch_grant_data(grant_id, session)
            if not grant:
                logger.error("grant_not_found", grant_id=str(grant_id))
                return stats

            if not grant.embedding:
                logger.error("grant_missing_embedding", grant_id=str(grant_id))
                return stats

            # Phase 1: Vector similarity search
            candidates = self.find_similar_profiles(grant.embedding, session)
            stats["candidates_found"] = len(candidates)

            if not candidates:
                logger.info(
                    "no_matching_candidates",
                    grant_id=str(grant_id),
                )
                return stats

            # Take top 20 for LLM re-ranking
            top_candidates = candidates[: self.LLM_RERANK_LIMIT]

            # Phase 2: LLM re-ranking in batches
            all_results: dict[UUID, MatchResult] = {}

            for i in range(0, len(top_candidates), self.LLM_BATCH_SIZE):
                batch = top_candidates[i : i + self.LLM_BATCH_SIZE]
                request = BatchMatchRequest(grant=grant, profiles=batch)

                try:
                    response = self.evaluate_matches_batch(request)
                    for user_id, result in response.results:
                        all_results[user_id] = result
                except Exception as e:
                    logger.error(
                        "batch_evaluation_failed",
                        grant_id=str(grant_id),
                        batch_index=i,
                        error=str(e),
                    )
                    continue

            stats["llm_evaluated"] = len(all_results)

            # Phase 3: Compute final scores and store/publish matches
            for candidate in top_candidates:
                if candidate.user_id not in all_results:
                    continue

                llm_result = all_results[candidate.user_id]

                # Compute weighted final score
                final_score = FinalMatch.compute_final_score(
                    candidate.vector_similarity,
                    llm_result.match_score,
                )

                match = FinalMatch(
                    match_id=uuid4(),
                    grant_id=grant_id,
                    user_id=candidate.user_id,
                    vector_similarity=candidate.vector_similarity,
                    llm_match_score=llm_result.match_score,
                    final_score=final_score,
                    reasoning=llm_result.reasoning,
                    key_strengths=llm_result.key_strengths,
                    concerns=llm_result.concerns,
                    predicted_success=llm_result.predicted_success,
                    created_at=datetime.now(timezone.utc),
                )

                # Store match
                self.store_match(match, session)
                stats["matches_stored"] += 1

                # Publish if score > threshold
                if final_score > self.FINAL_MATCH_THRESHOLD:
                    self.publish_match(match, grant)
                    stats["matches_published"] += 1

            session.commit()

        stats["processing_time_seconds"] = time.time() - start_time

        logger.info(
            "grant_matching_complete",
            **stats,
        )

        return stats

    def consume_validated_grants(self, block_ms: int = 5000) -> None:
        """
        Consume grants from validated stream and process matches.

        Long-running consumer loop for Celery worker.

        Args:
            block_ms: Milliseconds to block waiting for messages.
        """
        self._ensure_consumer_group()

        logger.info("starting_grant_consumer")

        while True:
            try:
                messages = self.redis_client.xreadgroup(
                    self.CONSUMER_GROUP,
                    self.CONSUMER_NAME,
                    {self.VALIDATED_GRANTS_STREAM: ">"},
                    count=1,
                    block=block_ms,
                )

                if not messages:
                    continue

                for stream_name, stream_messages in messages:
                    for message_id, message_data in stream_messages:
                        try:
                            data = json.loads(message_data.get("data", "{}"))
                            grant_id = UUID(data.get("grant_id"))

                            logger.info(
                                "processing_validated_grant",
                                grant_id=str(grant_id),
                                message_id=message_id,
                            )

                            self.process_grant(grant_id)

                            # Acknowledge message
                            self.redis_client.xack(
                                self.VALIDATED_GRANTS_STREAM,
                                self.CONSUMER_GROUP,
                                message_id,
                            )

                        except Exception as e:
                            logger.error(
                                "message_processing_failed",
                                message_id=message_id,
                                error=str(e),
                            )

            except Exception as e:
                logger.error("consumer_error", error=str(e))
                time.sleep(5)  # Back off on errors

    def close(self) -> None:
        """Clean up resources."""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None


# =============================================================================
# Celery Tasks
# =============================================================================


@celery_app.task(
    bind=True,
    queue="high",
    priority=7,
    soft_time_limit=120,
    time_limit=180,
)
def process_grant_matches(self, grant_id: str) -> dict[str, Any]:
    """
    Celery task to process grant matches.

    Args:
        grant_id: Grant identifier string.

    Returns:
        Matching statistics.
    """
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url)
    matcher = GrantMatcher(engine)

    try:
        return matcher.process_grant(UUID(grant_id))
    finally:
        matcher.close()
        engine.dispose()


@celery_app.task(
    bind=True,
    queue="high",
    priority=7,
)
def run_matching_consumer(self) -> None:
    """
    Celery task to run the matching consumer.

    Long-running task that consumes from grants:validated stream.
    """
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url)
    matcher = GrantMatcher(engine)

    try:
        matcher.consume_validated_grants()
    finally:
        matcher.close()
        engine.dispose()


# =============================================================================
# Standalone execution
# =============================================================================

if __name__ == "__main__":
    """Run matcher as standalone consumer."""
    from sqlalchemy import create_engine

    engine = create_engine(settings.database_url)
    matcher = GrantMatcher(engine)

    try:
        matcher.consume_validated_grants()
    except KeyboardInterrupt:
        logger.info("shutting_down")
    finally:
        matcher.close()
        engine.dispose()
