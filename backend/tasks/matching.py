"""
GrantRadar Matching Tasks
Celery tasks for computing and managing grant-to-researcher matches.
"""
import time
from typing import Any, Optional
from uuid import UUID

import redis
import structlog
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from agents.matching.matcher import GrantMatcher
from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import sync_engine

logger = structlog.get_logger().bind(module="matching_tasks")

# Redis stream names (matching GrantMatcher constants)
VALIDATED_GRANTS_STREAM = "grants:validated"
MATCHES_STREAM = "matches:computed"


# =============================================================================
# Task 1: Compute Grant Matches
# =============================================================================

@celery_app.task(
    bind=True,
    queue="high",
    priority=7,
    soft_time_limit=300,  # 5 minutes soft limit
    time_limit=360,  # 6 minutes hard limit
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def compute_grant_matches(self, grant_id: str) -> dict[str, Any]:
    """
    Compute matches between a grant and all user lab profiles.

    This task:
    1. Consumes from "grants:validated" stream
    2. Instantiates GrantMatcher from agents/matching/matcher.py
    3. Finds all users with lab profiles
    4. Computes match using GrantMatcher.compute_match()
    5. Creates Match records in database (score, reasoning, predicted_success)
    6. Publishes high matches (>70) to "matches:computed" stream

    Args:
        grant_id: UUID string of the grant to match.

    Returns:
        Dictionary with match statistics:
        - grant_id: Grant identifier
        - total_profiles: Number of profiles checked
        - matches_created: Number of matches stored
        - high_matches_published: Number of matches published to stream
        - average_score: Average match score
        - processing_time_seconds: Time taken to process

    Raises:
        ValueError: If grant_id is invalid or grant not found.
        SQLAlchemyError: If database operations fail.
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(
        "compute_grant_matches_started",
        task_id=task_id,
        grant_id=grant_id,
    )

    # Validate grant_id format
    try:
        grant_uuid = UUID(grant_id)
    except (ValueError, AttributeError) as e:
        logger.error(
            "invalid_grant_id",
            task_id=task_id,
            grant_id=grant_id,
            error=str(e),
        )
        raise ValueError(f"Invalid grant_id format: {grant_id}") from e

    # Initialize matcher
    matcher = GrantMatcher(db_engine=sync_engine)

    try:
        # Use the existing process_grant method from GrantMatcher
        # which handles the complete workflow:
        # - Fetches grant data
        # - Finds similar profiles via vector search
        # - Re-ranks using LLM
        # - Stores matches
        # - Publishes high matches to stream
        stats = matcher.process_grant(grant_uuid)

        # Enhance stats with task metadata
        stats["task_id"] = task_id
        stats["processing_time_seconds"] = time.time() - start_time

        logger.info(
            "compute_grant_matches_completed",
            task_id=task_id,
            grant_id=grant_id,
            candidates_found=stats.get("candidates_found", 0),
            matches_stored=stats.get("matches_stored", 0),
            matches_published=stats.get("matches_published", 0),
            duration_seconds=stats["processing_time_seconds"],
        )

        return stats

    except Exception as e:
        logger.error(
            "compute_grant_matches_failed",
            task_id=task_id,
            grant_id=grant_id,
            error=str(e),
            error_type=type(e).__name__,
            exc_info=True,
        )
        raise
    finally:
        # Clean up matcher resources
        matcher.close()


# =============================================================================
# Task 2: Process High Priority Match
# =============================================================================

@celery_app.task(
    bind=True,
    queue="critical",
    priority=10,
    soft_time_limit=60,  # 1 minute soft limit
    time_limit=90,  # 1.5 minutes hard limit
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def process_high_priority_match(self, match_id: str) -> dict[str, Any]:
    """
    Process matches with >90% score for immediate action.

    This task:
    1. Validates match score is >90%
    2. Updates match priority flags in database
    3. Triggers immediate alert delivery
    4. Logs high-priority match for analytics

    Args:
        match_id: UUID string of the match to process.

    Returns:
        Dictionary with processing results:
        - match_id: Match identifier
        - user_id: User who received the alert
        - grant_id: Grant identifier
        - match_score: Score that triggered high priority
        - alert_triggered: Whether alert was queued
        - processing_time_ms: Processing time in milliseconds

    Raises:
        ValueError: If match_id is invalid or match not found.
        SQLAlchemyError: If database operations fail.
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(
        "process_high_priority_match_started",
        task_id=task_id,
        match_id=match_id,
    )

    # Validate match_id format
    try:
        match_uuid = UUID(match_id)
    except (ValueError, AttributeError) as e:
        logger.error(
            "invalid_match_id",
            task_id=task_id,
            match_id=match_id,
            error=str(e),
        )
        raise ValueError(f"Invalid match_id format: {match_id}") from e

    with Session(sync_engine) as session:
        try:
            # Fetch match details with related grant and user info
            query = text("""
                SELECT
                    m.id,
                    m.user_id,
                    m.grant_id,
                    m.match_score,
                    m.reasoning,
                    m.predicted_success,
                    g.title as grant_title,
                    g.deadline,
                    g.agency,
                    u.email as user_email,
                    u.phone as user_phone,
                    u.name as user_name
                FROM matches m
                JOIN grants g ON m.grant_id = g.id
                JOIN users u ON m.user_id = u.id
                WHERE m.id = :match_id
            """)

            result = session.execute(query, {"match_id": str(match_uuid)}).fetchone()

            if not result:
                logger.warning(
                    "match_not_found",
                    task_id=task_id,
                    match_id=match_id,
                )
                raise ValueError(f"Match not found: {match_id}")

            match_score = result.match_score
            user_id = result.user_id
            grant_id = result.grant_id
            user_email = result.user_email

            # Verify this is actually a high priority match (>90%)
            if match_score <= 0.90:
                logger.warning(
                    "match_score_too_low_for_high_priority",
                    task_id=task_id,
                    match_id=match_id,
                    match_score=match_score,
                )
                return {
                    "match_id": match_id,
                    "user_id": str(user_id),
                    "grant_id": str(grant_id),
                    "match_score": match_score,
                    "alert_triggered": False,
                    "reason": "Score below 90% threshold",
                    "processing_time_ms": (time.time() - start_time) * 1000,
                }

            # Update match with high priority flag
            # Add metadata to track high-priority processing
            update_query = text("""
                UPDATE matches
                SET user_feedback = COALESCE(user_feedback, '{}'::jsonb) ||
                    jsonb_build_object(
                        'high_priority', true,
                        'priority_processed_at', :processed_at,
                        'priority_task_id', :task_id
                    )
                WHERE id = :match_id
            """)

            session.execute(
                update_query,
                {
                    "match_id": str(match_uuid),
                    "processed_at": time.time(),
                    "task_id": task_id,
                }
            )

            # Trigger immediate alert delivery
            # Import here to avoid circular dependency
            from backend.tasks.notifications import send_high_match_alert

            alert_result = send_high_match_alert.apply_async(
                kwargs={
                    "user_id": str(user_id),
                    "grant_id": str(grant_id),
                    "match_id": str(match_uuid),
                    "match_score": match_score,
                },
                queue="critical",
                priority=10,
            )

            session.commit()

            processing_time_ms = (time.time() - start_time) * 1000

            logger.info(
                "process_high_priority_match_completed",
                task_id=task_id,
                match_id=match_id,
                user_id=str(user_id),
                grant_id=str(grant_id),
                match_score=match_score,
                alert_task_id=alert_result.id,
                processing_time_ms=processing_time_ms,
            )

            return {
                "match_id": match_id,
                "user_id": str(user_id),
                "grant_id": str(grant_id),
                "match_score": match_score,
                "alert_triggered": True,
                "alert_task_id": alert_result.id,
                "processing_time_ms": processing_time_ms,
            }

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(
                "database_error_processing_high_priority_match",
                task_id=task_id,
                match_id=match_id,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            session.rollback()
            logger.error(
                "process_high_priority_match_failed",
                task_id=task_id,
                match_id=match_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise


# =============================================================================
# Task 3: Recompute User Matches
# =============================================================================

@celery_app.task(
    bind=True,
    queue="normal",
    priority=3,
    soft_time_limit=600,  # 10 minutes soft limit
    time_limit=720,  # 12 minutes hard limit
    max_retries=2,
    autoretry_for=(Exception,),
    retry_backoff=True,
)
def recompute_user_matches(self, user_id: str) -> dict[str, Any]:
    """
    Recompute all grant matches for a user when their profile is updated.

    This task:
    1. Validates user exists and has lab profile
    2. Fetches all grants with embeddings
    3. Re-computes matches using GrantMatcher
    4. Updates existing Match records (upserts)
    5. Publishes newly high-scoring matches to stream

    Args:
        user_id: UUID string of the user whose matches to recompute.

    Returns:
        Dictionary with recomputation statistics:
        - user_id: User identifier
        - grants_evaluated: Number of grants checked
        - matches_updated: Number of match records updated
        - new_high_matches: Number of new high-scoring matches
        - processing_time_seconds: Time taken to process

    Raises:
        ValueError: If user_id is invalid or user has no lab profile.
        SQLAlchemyError: If database operations fail.
    """
    start_time = time.time()
    task_id = self.request.id

    logger.info(
        "recompute_user_matches_started",
        task_id=task_id,
        user_id=user_id,
    )

    # Validate user_id format
    try:
        user_uuid = UUID(user_id)
    except (ValueError, AttributeError) as e:
        logger.error(
            "invalid_user_id",
            task_id=task_id,
            user_id=user_id,
            error=str(e),
        )
        raise ValueError(f"Invalid user_id format: {user_id}") from e

    matcher = GrantMatcher(db_engine=sync_engine)
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)

    stats = {
        "user_id": user_id,
        "grants_evaluated": 0,
        "matches_updated": 0,
        "new_high_matches": 0,
        "processing_time_seconds": 0,
    }

    with Session(sync_engine) as session:
        try:
            # Verify user has a lab profile with embedding
            profile_query = text("""
                SELECT
                    id,
                    profile_embedding,
                    research_areas,
                    methods,
                    past_grants,
                    institution
                FROM lab_profiles
                WHERE user_id = :user_id
                  AND profile_embedding IS NOT NULL
                LIMIT 1
            """)

            profile_result = session.execute(
                profile_query,
                {"user_id": str(user_uuid)}
            ).fetchone()

            if not profile_result:
                logger.warning(
                    "user_profile_not_found_or_missing_embedding",
                    task_id=task_id,
                    user_id=user_id,
                )
                raise ValueError(
                    f"User {user_id} has no lab profile or profile lacks embedding"
                )

            profile_embedding = profile_result.profile_embedding

            # Fetch all grants with embeddings for re-matching
            # Use vector similarity to find relevant grants
            grants_query = text("""
                SELECT
                    id,
                    title,
                    description,
                    agency as funding_agency,
                    amount_max as funding_amount,
                    deadline,
                    eligibility as eligibility_criteria,
                    categories,
                    raw_data->>'keywords' as keywords,
                    embedding
                FROM grants
                WHERE embedding IS NOT NULL
                ORDER BY posted_at DESC
                LIMIT 1000
            """)

            grants = session.execute(grants_query).fetchall()
            stats["grants_evaluated"] = len(grants)

            if not grants:
                logger.info(
                    "no_grants_to_match",
                    task_id=task_id,
                    user_id=user_id,
                )
                return stats

            logger.info(
                "recomputing_matches_for_grants",
                task_id=task_id,
                user_id=user_id,
                grant_count=len(grants),
            )

            # Get existing match scores to detect improvements
            existing_scores_query = text("""
                SELECT grant_id, match_score
                FROM matches
                WHERE user_id = :user_id
            """)
            existing_scores = {
                str(row.grant_id): row.match_score
                for row in session.execute(
                    existing_scores_query,
                    {"user_id": str(user_uuid)}
                )
            }

            # Process each grant
            for grant in grants:
                try:
                    grant_id = grant.id

                    # Use the matcher to compute match for this specific grant-user pair
                    # We'll use the vector similarity + LLM approach
                    from agents.matching.models import (
                        GrantData,
                        ProfileMatch,
                        UserProfile,
                        BatchMatchRequest,
                    )

                    # Build GrantData object
                    grant_data = GrantData(
                        grant_id=UUID(grant_id),
                        title=grant.title,
                        description=grant.description or "",
                        funding_agency=grant.funding_agency,
                        funding_amount=grant.funding_amount,
                        deadline=grant.deadline,
                        eligibility_criteria=grant.eligibility_criteria or [],
                        categories=grant.categories or [],
                        keywords=[],
                        embedding=grant.embedding,
                    )

                    # Build UserProfile object
                    user_profile = UserProfile(
                        user_id=user_uuid,
                        research_areas=profile_result.research_areas or [],
                        methods=profile_result.methods or [],
                        past_grants=profile_result.past_grants or [],
                        institution=profile_result.institution,
                        department=None,
                        keywords=[],
                    )

                    # Calculate vector similarity
                    similarity_query = text("""
                        SELECT 1 - (
                            (SELECT profile_embedding FROM lab_profiles WHERE user_id = :user_id LIMIT 1)
                            <=>
                            (SELECT embedding FROM grants WHERE id = :grant_id)
                        ) AS similarity
                    """)
                    similarity_result = session.execute(
                        similarity_query,
                        {"user_id": str(user_uuid), "grant_id": str(grant_id)}
                    ).fetchone()
                    vector_similarity = float(similarity_result.similarity)

                    # Only proceed with LLM if vector similarity is reasonable
                    if vector_similarity < 0.3:
                        continue  # Skip low-similarity grants

                    # Build profile match for LLM evaluation
                    profile_match = ProfileMatch(
                        user_id=user_uuid,
                        vector_similarity=vector_similarity,
                        profile=user_profile,
                    )

                    # Call LLM for detailed evaluation
                    batch_request = BatchMatchRequest(
                        grant=grant_data,
                        profiles=[profile_match],
                    )

                    batch_response = matcher.evaluate_matches_batch(batch_request)

                    if not batch_response.results:
                        continue

                    # Extract match result
                    _, match_result = batch_response.results[0]

                    # Compute final weighted score
                    from agents.matching.models import FinalMatch
                    final_score = FinalMatch.compute_final_score(
                        vector_similarity,
                        match_result.match_score,
                    )

                    # Store/update match in database
                    upsert_query = text("""
                        INSERT INTO matches (
                            id,
                            grant_id,
                            user_id,
                            match_score,
                            reasoning,
                            predicted_success,
                            created_at
                        ) VALUES (
                            gen_random_uuid(),
                            :grant_id,
                            :user_id,
                            :match_score,
                            :reasoning,
                            :predicted_success,
                            NOW()
                        )
                        ON CONFLICT (grant_id, user_id) DO UPDATE SET
                            match_score = EXCLUDED.match_score,
                            reasoning = EXCLUDED.reasoning,
                            predicted_success = EXCLUDED.predicted_success,
                            created_at = NOW()
                    """)

                    session.execute(
                        upsert_query,
                        {
                            "grant_id": str(grant_id),
                            "user_id": str(user_uuid),
                            "match_score": final_score / 100,  # Convert to 0-1
                            "reasoning": match_result.reasoning,
                            "predicted_success": match_result.predicted_success / 100,
                        }
                    )

                    stats["matches_updated"] += 1

                    # Check if this is a newly high-scoring match
                    old_score = existing_scores.get(str(grant_id), 0)
                    if final_score > 70 and (old_score <= 70 or old_score == 0):
                        # Publish to matches:computed stream
                        from backend.core.events import MatchComputedEvent, PriorityLevel
                        from uuid import uuid4

                        priority = matcher._compute_priority_level(
                            final_score,
                            grant.deadline
                        )

                        event = MatchComputedEvent(
                            event_id=uuid4(),
                            match_id=uuid4(),  # Will be replaced with actual match_id
                            grant_id=UUID(grant_id),
                            user_id=user_uuid,
                            match_score=final_score / 100,
                            priority_level=priority,
                            matching_criteria=match_result.key_strengths,
                            explanation=match_result.reasoning,
                            grant_deadline=grant.deadline,
                        )

                        redis_client.xadd(
                            MATCHES_STREAM,
                            {"data": event.model_dump_json()}
                        )

                        stats["new_high_matches"] += 1

                except Exception as e:
                    logger.warning(
                        "failed_to_compute_match_for_grant",
                        task_id=task_id,
                        user_id=user_id,
                        grant_id=str(grant.id),
                        error=str(e),
                    )
                    continue  # Continue with other grants

            # Commit all updates
            session.commit()

            stats["processing_time_seconds"] = time.time() - start_time

            logger.info(
                "recompute_user_matches_completed",
                task_id=task_id,
                user_id=user_id,
                grants_evaluated=stats["grants_evaluated"],
                matches_updated=stats["matches_updated"],
                new_high_matches=stats["new_high_matches"],
                duration_seconds=stats["processing_time_seconds"],
            )

            return stats

        except SQLAlchemyError as e:
            session.rollback()
            logger.error(
                "database_error_recomputing_user_matches",
                task_id=task_id,
                user_id=user_id,
                error=str(e),
                exc_info=True,
            )
            raise
        except Exception as e:
            session.rollback()
            logger.error(
                "recompute_user_matches_failed",
                task_id=task_id,
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True,
            )
            raise
        finally:
            matcher.close()
            redis_client.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "compute_grant_matches",
    "process_high_priority_match",
    "recompute_user_matches",
]
