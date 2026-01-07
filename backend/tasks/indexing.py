"""
GrantRadar Indexing Tasks

Celery tasks for generating and updating vector embeddings for grants
and lab profiles, plus database index optimization.
"""

import logging
import time
from typing import Any

import openai
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import get_sync_db
from backend.models import Grant, LabProfile

logger = logging.getLogger(__name__)

# Initialize OpenAI client
openai.api_key = settings.openai_api_key


# =============================================================================
# Embedding Generation Utilities
# =============================================================================


def generate_embedding(text: str, retry_count: int = 3) -> list[float] | None:
    """
    Generate embedding vector for text using OpenAI API.

    Args:
        text: Text to embed.
        retry_count: Number of retries for rate limit errors.

    Returns:
        Embedding vector or None if generation fails.
    """
    if not text or not text.strip():
        logger.warning("Empty text provided for embedding generation")
        return None

    for attempt in range(retry_count):
        try:
            response = openai.embeddings.create(
                model=settings.embedding_model,
                input=text.strip(),
                encoding_format="float",
            )
            embedding = response.data[0].embedding
            logger.debug(f"Generated embedding of dimension {len(embedding)}")
            return embedding

        except openai.RateLimitError as e:
            wait_time = (2 ** attempt) * 2  # Exponential backoff: 2s, 4s, 8s
            logger.warning(
                f"Rate limit hit (attempt {attempt + 1}/{retry_count}). "
                f"Waiting {wait_time}s: {e}"
            )
            if attempt < retry_count - 1:
                time.sleep(wait_time)
            else:
                logger.error("Max retries reached for rate limit")
                raise

        except openai.APIError as e:
            logger.error(f"OpenAI API error during embedding generation: {e}")
            if attempt < retry_count - 1:
                time.sleep(1)
            else:
                raise

        except Exception as e:
            logger.error(f"Unexpected error generating embedding: {e}", exc_info=True)
            raise

    return None


def create_grant_text(grant: Grant) -> str:
    """
    Create comprehensive text representation of grant for embedding.

    Args:
        grant: Grant model instance.

    Returns:
        Formatted text containing all relevant grant information.
    """
    parts = []

    # Title (most important)
    if grant.title:
        parts.append(f"Title: {grant.title}")

    # Agency and source
    if grant.agency:
        parts.append(f"Funding Agency: {grant.agency}")
    if grant.source:
        parts.append(f"Source: {grant.source}")

    # Description (core content)
    if grant.description:
        parts.append(f"Description: {grant.description}")

    # Categories/tags
    if grant.categories:
        categories_str = ", ".join(grant.categories)
        parts.append(f"Research Areas: {categories_str}")

    # Eligibility criteria
    if grant.eligibility:
        # Convert JSONB eligibility to readable text
        eligibility_parts = []
        for key, value in grant.eligibility.items():
            if isinstance(value, list):
                eligibility_parts.append(f"{key}: {', '.join(str(v) for v in value)}")
            else:
                eligibility_parts.append(f"{key}: {value}")
        if eligibility_parts:
            parts.append(f"Eligibility: {'; '.join(eligibility_parts)}")

    # Funding amount (helps with matching)
    if grant.amount_min or grant.amount_max:
        amount_str = ""
        if grant.amount_min and grant.amount_max:
            amount_str = f"${grant.amount_min:,} - ${grant.amount_max:,}"
        elif grant.amount_min:
            amount_str = f"Minimum ${grant.amount_min:,}"
        elif grant.amount_max:
            amount_str = f"Maximum ${grant.amount_max:,}"
        parts.append(f"Funding: {amount_str}")

    return "\n\n".join(parts)


def create_profile_text(profile: LabProfile) -> str:
    """
    Create comprehensive text representation of lab profile for embedding.

    Args:
        profile: LabProfile model instance.

    Returns:
        Formatted text containing all relevant profile information.
    """
    parts = []

    # Research areas (most important)
    if profile.research_areas:
        areas_str = ", ".join(profile.research_areas)
        parts.append(f"Research Areas: {areas_str}")

    # Methods and techniques
    if profile.methods:
        methods_str = ", ".join(profile.methods)
        parts.append(f"Research Methods: {methods_str}")

    # Career stage
    if profile.career_stage:
        parts.append(f"Career Stage: {profile.career_stage.replace('_', ' ').title()}")

    # Past grants
    if profile.past_grants:
        grants_parts = []
        if isinstance(profile.past_grants, dict):
            for key, value in profile.past_grants.items():
                if isinstance(value, str):
                    grants_parts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    grants_parts.append(f"{key}: {', '.join(str(v) for v in value)}")
        if grants_parts:
            parts.append(f"Past Grants: {'; '.join(grants_parts)}")

    # Publications
    if profile.publications:
        pubs_parts = []
        if isinstance(profile.publications, dict):
            for key, value in profile.publications.items():
                if isinstance(value, (str, int, float)):
                    pubs_parts.append(f"{key}: {value}")
        if pubs_parts:
            parts.append(f"Publications: {'; '.join(pubs_parts)}")

    # ORCID
    if profile.orcid:
        parts.append(f"ORCID: {profile.orcid}")

    return "\n\n".join(parts)


# =============================================================================
# Celery Tasks
# =============================================================================


@celery_app.task(
    bind=True,
    name="backend.tasks.indexing.reindex_grants",
    max_retries=3,
    default_retry_delay=60,
)
def reindex_grants(self, batch_size: int = 100) -> dict[str, Any]:
    """
    Reindex all grants without embeddings or with outdated embeddings.

    Processes grants in batches to manage memory and API rate limits.
    Generates embeddings using OpenAI API and updates the database.

    Args:
        batch_size: Number of grants to process in each batch.

    Returns:
        Dictionary with reindexing statistics:
            - total_processed: Number of grants processed
            - successful: Number of successful embeddings
            - failed: Number of failed embeddings
            - duration: Time taken in seconds
    """
    start_time = time.time()
    db: Session = get_sync_db()

    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "duration": 0,
    }

    try:
        # Find grants without embeddings
        query = select(Grant).where(Grant.embedding.is_(None))
        grants_to_index = db.execute(query).scalars().all()
        total_grants = len(grants_to_index)

        logger.info(f"Found {total_grants} grants without embeddings")

        if total_grants == 0:
            logger.info("No grants to reindex")
            return stats

        # Process in batches
        for i in range(0, total_grants, batch_size):
            batch = grants_to_index[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_grants + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} grants)"
            )

            for grant in batch:
                try:
                    # Create text representation
                    grant_text = create_grant_text(grant)

                    # Generate embedding
                    embedding = generate_embedding(grant_text)

                    if embedding:
                        # Update grant with embedding
                        grant.embedding = embedding
                        stats["successful"] += 1
                        logger.debug(f"Generated embedding for grant {grant.id}")
                    else:
                        stats["failed"] += 1
                        logger.warning(f"Failed to generate embedding for grant {grant.id}")

                    stats["total_processed"] += 1

                except Exception as e:
                    stats["failed"] += 1
                    stats["total_processed"] += 1
                    logger.error(
                        f"Error processing grant {grant.id}: {e}",
                        exc_info=True
                    )

            # Commit batch
            try:
                db.commit()
                logger.info(f"Committed batch {batch_num}/{total_batches}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error committing batch {batch_num}: {e}", exc_info=True)
                raise

            # Rate limiting: small delay between batches
            if i + batch_size < total_grants:
                time.sleep(1)

        stats["duration"] = time.time() - start_time
        logger.info(
            f"Reindexing complete. Processed {stats['total_processed']} grants "
            f"({stats['successful']} successful, {stats['failed']} failed) "
            f"in {stats['duration']:.2f}s"
        )

        return stats

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error in reindex_grants: {e}", exc_info=True)
        raise

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.indexing.reindex_profiles",
    max_retries=3,
    default_retry_delay=60,
)
def reindex_profiles(self, batch_size: int = 50) -> dict[str, Any]:
    """
    Reindex all lab profiles without embeddings.

    Processes profiles in batches to manage memory and API rate limits.
    Generates embeddings using OpenAI API and updates the database.

    Args:
        batch_size: Number of profiles to process in each batch.

    Returns:
        Dictionary with reindexing statistics:
            - total_processed: Number of profiles processed
            - successful: Number of successful embeddings
            - failed: Number of failed embeddings
            - duration: Time taken in seconds
    """
    start_time = time.time()
    db: Session = get_sync_db()

    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "duration": 0,
    }

    try:
        # Find profiles without embeddings
        query = select(LabProfile).where(LabProfile.profile_embedding.is_(None))
        profiles_to_index = db.execute(query).scalars().all()
        total_profiles = len(profiles_to_index)

        logger.info(f"Found {total_profiles} profiles without embeddings")

        if total_profiles == 0:
            logger.info("No profiles to reindex")
            return stats

        # Process in batches
        for i in range(0, total_profiles, batch_size):
            batch = profiles_to_index[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_profiles + batch_size - 1) // batch_size

            logger.info(
                f"Processing batch {batch_num}/{total_batches} "
                f"({len(batch)} profiles)"
            )

            for profile in batch:
                try:
                    # Create text representation
                    profile_text = create_profile_text(profile)

                    # Generate embedding
                    embedding = generate_embedding(profile_text)

                    if embedding:
                        # Update profile with embedding
                        profile.profile_embedding = embedding
                        stats["successful"] += 1
                        logger.debug(f"Generated embedding for profile {profile.id}")
                    else:
                        stats["failed"] += 1
                        logger.warning(
                            f"Failed to generate embedding for profile {profile.id}"
                        )

                    stats["total_processed"] += 1

                except Exception as e:
                    stats["failed"] += 1
                    stats["total_processed"] += 1
                    logger.error(
                        f"Error processing profile {profile.id}: {e}",
                        exc_info=True
                    )

            # Commit batch
            try:
                db.commit()
                logger.info(f"Committed batch {batch_num}/{total_batches}")
            except Exception as e:
                db.rollback()
                logger.error(f"Error committing batch {batch_num}: {e}", exc_info=True)
                raise

            # Rate limiting: small delay between batches
            if i + batch_size < total_profiles:
                time.sleep(1)

        stats["duration"] = time.time() - start_time
        logger.info(
            f"Profile reindexing complete. Processed {stats['total_processed']} "
            f"profiles ({stats['successful']} successful, {stats['failed']} failed) "
            f"in {stats['duration']:.2f}s"
        )

        return stats

    except Exception as e:
        db.rollback()
        logger.error(f"Fatal error in reindex_profiles: {e}", exc_info=True)
        raise

    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="backend.tasks.indexing.rebuild_vector_indexes",
    max_retries=2,
    default_retry_delay=120,
)
def rebuild_vector_indexes(self) -> dict[str, Any]:
    """
    Rebuild pgvector IVFFLAT indexes and optimize database performance.

    Drops and recreates vector indexes on grants and lab_profiles tables,
    then runs VACUUM ANALYZE to update statistics and reclaim space.

    This task should be run:
    - After bulk data imports
    - Periodically (weekly/monthly) for large datasets
    - When query performance degrades

    Returns:
        Dictionary with operation results:
            - grants_index_rebuilt: Boolean
            - profiles_index_rebuilt: Boolean
            - vacuum_completed: Boolean
            - duration: Time taken in seconds
    """
    start_time = time.time()
    db: Session = get_sync_db()

    results = {
        "grants_index_rebuilt": False,
        "profiles_index_rebuilt": False,
        "vacuum_completed": False,
        "duration": 0,
    }

    try:
        logger.info("Starting vector index rebuild")

        # Drop and recreate grants embedding index
        logger.info("Rebuilding grants embedding index...")
        try:
            db.execute(text("DROP INDEX IF EXISTS ix_grants_embedding"))
            db.commit()

            db.execute(text(
                """
                CREATE INDEX ix_grants_embedding ON grants
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            ))
            db.commit()
            results["grants_index_rebuilt"] = True
            logger.info("Grants embedding index rebuilt successfully")

        except Exception as e:
            db.rollback()
            logger.error(f"Error rebuilding grants index: {e}", exc_info=True)
            raise

        # Drop and recreate lab_profiles embedding index
        logger.info("Rebuilding lab_profiles embedding index...")
        try:
            db.execute(text("DROP INDEX IF EXISTS ix_lab_profiles_embedding"))
            db.commit()

            db.execute(text(
                """
                CREATE INDEX ix_lab_profiles_embedding ON lab_profiles
                USING ivfflat (profile_embedding vector_cosine_ops)
                WITH (lists = 100)
                """
            ))
            db.commit()
            results["profiles_index_rebuilt"] = True
            logger.info("Lab profiles embedding index rebuilt successfully")

        except Exception as e:
            db.rollback()
            logger.error(f"Error rebuilding profiles index: {e}", exc_info=True)
            raise

        # Run VACUUM ANALYZE on both tables
        logger.info("Running VACUUM ANALYZE on grants and lab_profiles...")
        try:
            # VACUUM cannot run inside a transaction, so we need autocommit
            db.connection().connection.set_isolation_level(0)

            db.execute(text("VACUUM ANALYZE grants"))
            logger.info("VACUUM ANALYZE completed for grants")

            db.execute(text("VACUUM ANALYZE lab_profiles"))
            logger.info("VACUUM ANALYZE completed for lab_profiles")

            # Reset isolation level
            db.connection().connection.set_isolation_level(1)

            results["vacuum_completed"] = True

        except Exception as e:
            logger.error(f"Error during VACUUM ANALYZE: {e}", exc_info=True)
            # Reset isolation level on error
            try:
                db.connection().connection.set_isolation_level(1)
            except:
                pass
            raise

        results["duration"] = time.time() - start_time
        logger.info(
            f"Vector index rebuild complete in {results['duration']:.2f}s. "
            f"Grants: {results['grants_index_rebuilt']}, "
            f"Profiles: {results['profiles_index_rebuilt']}, "
            f"Vacuum: {results['vacuum_completed']}"
        )

        return results

    except Exception as e:
        logger.error(f"Fatal error in rebuild_vector_indexes: {e}", exc_info=True)
        raise

    finally:
        db.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "reindex_grants",
    "reindex_profiles",
    "rebuild_vector_indexes",
    "generate_embedding",
    "create_grant_text",
    "create_profile_text",
]
