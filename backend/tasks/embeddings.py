"""
Profile Embedding Generation Tasks
Celery tasks for computing and updating user profile embeddings.
"""
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import create_engine

from backend.celery_app import celery_app, normal_task
from backend.core.config import settings

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    queue="normal",
    priority=3,
    soft_time_limit=60,
    time_limit=90,
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def compute_profile_embedding(self, profile_id: str) -> dict[str, Any]:
    """
    Compute and store embedding for a user profile.

    This task is triggered when:
    - A new profile is created during onboarding
    - An existing profile is updated with changes to embedding-relevant fields
      (research_areas, methods, publications, past_grants)

    Args:
        profile_id: UUID string of the LabProfile to compute embedding for

    Returns:
        dict with status and metadata about the embedding generation

    Raises:
        Exception: If embedding generation fails after retries
    """
    from agents.matching.profile_builder import ProfileBuilder

    logger.info(f"Computing profile embedding for profile_id={profile_id}")

    # Create database engine for this task
    engine = create_engine(
        settings.database_url,
        pool_size=2,
        max_overflow=5,
        pool_pre_ping=True,
    )

    try:
        # Initialize profile builder
        builder = ProfileBuilder(engine)

        # Fetch the profile to get user_id
        # The ProfileBuilder.build_embedding() method expects user_id, not profile_id
        # We need to query the database to get the user_id from the profile_id
        from sqlalchemy import text
        from sqlalchemy.orm import Session

        with Session(engine) as session:
            query = text("""
                SELECT user_id
                FROM lab_profiles
                WHERE id = :profile_id
            """)
            result = session.execute(query, {"profile_id": profile_id}).fetchone()

            if not result:
                logger.error(f"Profile not found: profile_id={profile_id}")
                return {
                    "status": "error",
                    "profile_id": profile_id,
                    "error": "Profile not found",
                }

            user_id = UUID(result.user_id)

        # Generate embedding (force=True to always regenerate)
        embedding_result = builder.build_embedding(user_id, force=True)

        if embedding_result:
            logger.info(
                f"Successfully generated embedding for profile_id={profile_id}, "
                f"user_id={user_id}, dims={len(embedding_result.embedding)}"
            )
            return {
                "status": "success",
                "profile_id": profile_id,
                "user_id": str(user_id),
                "embedding_dimensions": len(embedding_result.embedding),
                "created_at": embedding_result.created_at.isoformat(),
            }
        else:
            logger.warning(
                f"Embedding generation returned None for profile_id={profile_id}, "
                f"user_id={user_id}"
            )
            return {
                "status": "skipped",
                "profile_id": profile_id,
                "user_id": str(user_id),
                "reason": "Empty profile data or embedding already up-to-date",
            }

    except Exception as e:
        logger.error(
            f"Failed to compute embedding for profile_id={profile_id}: {e}",
            exc_info=True,
        )
        # Re-raise to trigger Celery retry
        raise

    finally:
        # Clean up database connection
        engine.dispose()


@celery_app.task(
    bind=True,
    queue="normal",
    priority=3,
    soft_time_limit=300,
    time_limit=360,
)
def rebuild_all_profile_embeddings(self) -> dict[str, Any]:
    """
    Rebuild embeddings for all user profiles.

    Use this for:
    - Initial setup when deploying the system
    - Full reindexing after model upgrades
    - Recovery from embedding corruption

    Returns:
        Statistics about the rebuild operation
    """
    from agents.matching.profile_builder import ProfileBuilder

    logger.info("Starting full profile embedding rebuild")

    engine = create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    try:
        builder = ProfileBuilder(engine)
        stats = builder.rebuild_all_embeddings()

        logger.info(f"Profile embedding rebuild complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Failed to rebuild profile embeddings: {e}", exc_info=True)
        raise

    finally:
        engine.dispose()


@celery_app.task(
    bind=True,
    queue="normal",
    priority=3,
    soft_time_limit=180,
    time_limit=240,
)
def compute_profile_embeddings_batch(
    self, profile_ids: list[str]
) -> dict[str, Any]:
    """
    Compute embeddings for multiple profiles in batch.

    More efficient than individual tasks when processing many profiles.

    Args:
        profile_ids: List of LabProfile UUID strings

    Returns:
        Statistics about the batch operation
    """
    from agents.matching.profile_builder import ProfileBuilder
    from sqlalchemy import text
    from sqlalchemy.orm import Session

    logger.info(f"Computing embeddings for {len(profile_ids)} profiles")

    engine = create_engine(
        settings.database_url,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
    )

    try:
        builder = ProfileBuilder(engine)

        # Get user_ids from profile_ids
        user_ids = []
        with Session(engine) as session:
            query = text("""
                SELECT user_id
                FROM lab_profiles
                WHERE id = ANY(:profile_ids)
            """)
            results = session.execute(
                query, {"profile_ids": profile_ids}
            ).fetchall()
            user_ids = [UUID(row.user_id) for row in results]

        # Generate embeddings in batch
        embeddings = builder.build_embeddings_batch(user_ids, force=True)

        stats = {
            "status": "success",
            "profiles_requested": len(profile_ids),
            "profiles_found": len(user_ids),
            "embeddings_generated": len(embeddings),
        }

        logger.info(f"Batch embedding generation complete: {stats}")
        return stats

    except Exception as e:
        logger.error(
            f"Failed to compute batch embeddings: {e}",
            exc_info=True,
        )
        raise

    finally:
        engine.dispose()
