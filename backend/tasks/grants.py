"""
GrantRadar Grant Processing Tasks

Celery tasks for processing, validating, and enriching grant data.
Tasks consume from Redis streams and manage the grant lifecycle.
"""
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import openai
import redis
from anthropic import Anthropic
from celery import Task
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from agents.curation.validator import CurationValidator
from backend.celery_app import celery_app
from backend.core.config import settings
from backend.database import SyncSessionLocal, get_sync_db
from backend.models import Grant

logger = logging.getLogger(__name__)


# =============================================================================
# Redis Stream Helper
# =============================================================================

def get_redis_client() -> redis.Redis:
    """Get a Redis client instance for stream operations."""
    return redis.from_url(settings.redis_url, decode_responses=True)


# =============================================================================
# Task 1: Process New Grant
# =============================================================================

@celery_app.task(
    name="backend.tasks.grants.process_new_grant",
    bind=True,
    queue="high",
    max_retries=3,
    default_retry_delay=30,
)
def process_new_grant(self: Task, grant_data: dict[str, Any]) -> Optional[dict[str, Any]]:
    """
    Process a new grant from the discovery stream.

    Workflow:
        1. Consume from "grants:discovered" stream
        2. Validate and normalize grant data
        3. Check for duplicates in database
        4. Create Grant record in database
        5. Publish to "grants:validated" stream
        6. Trigger embedding generation

    Args:
        grant_data: Raw grant data from discovery agent with fields:
            - title: Grant title (required)
            - description: Grant description
            - source: Source system (e.g., 'nih', 'nsf', 'grants_gov')
            - external_id: ID from source system
            - url: Link to grant opportunity
            - agency: Funding agency name
            - amount_min: Minimum funding amount
            - amount_max: Maximum funding amount
            - deadline: Application deadline (ISO format string or datetime)
            - posted_at: When grant was posted (ISO format string or datetime)
            - eligibility: Eligibility criteria dict
            - categories: Research categories list
            - raw_data: Original data from source

    Returns:
        Dict with grant_id and processing status, or None if validation fails.

    Raises:
        Exception: Re-raises on retry exhaustion.
    """
    logger.info(
        "Processing new grant",
        extra={
            "title": grant_data.get("title", "")[:100],
            "source": grant_data.get("source"),
        },
    )

    db = None
    redis_client = None

    try:
        # Step 1: Validate and normalize data
        title = grant_data.get("title")
        if not title:
            logger.warning("Grant missing required field: title", extra={"grant_data": grant_data})
            return None

        source = grant_data.get("source", "unknown")
        external_id = grant_data.get("external_id", str(uuid4()))

        # Step 2: Check for duplicates in database
        db = get_sync_db()

        # Check by external_id + source combination
        existing_grant = db.execute(
            select(Grant).where(
                Grant.external_id == external_id,
                Grant.source == source,
            )
        ).scalar_one_or_none()

        if existing_grant:
            logger.info(
                "Duplicate grant found, skipping",
                extra={
                    "grant_id": str(existing_grant.id),
                    "external_id": external_id,
                    "source": source,
                },
            )
            return {
                "grant_id": str(existing_grant.id),
                "status": "duplicate",
                "message": "Grant already exists in database",
            }

        # Step 3: Create Grant record
        grant_id = uuid4()

        # Parse deadline and posted_at if they're strings
        deadline = grant_data.get("deadline")
        if isinstance(deadline, str):
            try:
                deadline = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                deadline = None

        posted_at = grant_data.get("posted_at")
        if isinstance(posted_at, str):
            try:
                posted_at = datetime.fromisoformat(posted_at.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                posted_at = None

        new_grant = Grant(
            id=grant_id,
            source=source,
            external_id=external_id,
            title=title,
            description=grant_data.get("description"),
            agency=grant_data.get("agency"),
            amount_min=grant_data.get("amount_min"),
            amount_max=grant_data.get("amount_max"),
            deadline=deadline,
            posted_at=posted_at,
            url=grant_data.get("url"),
            eligibility=grant_data.get("eligibility"),
            categories=grant_data.get("categories"),
            raw_data=grant_data.get("raw_data"),
            created_at=datetime.now(timezone.utc),
        )

        db.add(new_grant)
        db.commit()
        db.refresh(new_grant)

        logger.info(
            "Grant created in database",
            extra={
                "grant_id": str(grant_id),
                "title": title[:100],
                "source": source,
            },
        )

        # Step 4: Publish to "grants:validated" stream
        redis_client = get_redis_client()

        validated_event = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "grant_id": str(grant_id),
            "source": source,
            "external_id": external_id,
            "title": title,
            "description": grant_data.get("description", ""),
            "url": grant_data.get("url", ""),
            "agency": grant_data.get("agency"),
            "deadline": deadline.isoformat() if deadline else None,
            "categories": grant_data.get("categories", []),
        }

        message_id = redis_client.xadd(
            "grants:validated",
            {"data": json.dumps(validated_event)},
        )

        logger.info(
            "Grant published to validated stream",
            extra={
                "grant_id": str(grant_id),
                "message_id": message_id,
            },
        )

        # Step 5: Trigger embedding generation (async)
        compute_grant_embedding.delay(str(grant_id))

        return {
            "grant_id": str(grant_id),
            "status": "success",
            "message": "Grant processed and queued for embedding generation",
            "stream_message_id": message_id,
        }

    except IntegrityError as e:
        if db:
            db.rollback()
        logger.warning(
            "Database integrity error (likely duplicate)",
            extra={"error": str(e)},
        )
        return {
            "grant_id": None,
            "status": "duplicate",
            "message": "Grant already exists (integrity constraint)",
        }

    except Exception as e:
        if db:
            db.rollback()
        logger.error(
            "Error processing grant",
            extra={
                "error": str(e),
                "grant_data": grant_data,
            },
            exc_info=True,
        )
        # Retry with exponential backoff
        raise self.retry(exc=e)

    finally:
        if db:
            db.close()
        if redis_client:
            redis_client.close()


# =============================================================================
# Task 2: Validate Grant
# =============================================================================

@celery_app.task(
    name="backend.tasks.grants.validate_grant",
    bind=True,
    queue="high",
    max_retries=2,
    default_retry_delay=60,
)
def validate_grant(self: Task, grant_id: str) -> dict[str, Any]:
    """
    Validate grant quality using the curation/validation agent.

    Uses agents/curation/validator.py to:
        - Check data quality
        - Flag issues
        - Update grant record with validation results

    Args:
        grant_id: UUID string of the grant to validate

    Returns:
        Dict with validation results:
            - grant_id: Grant UUID
            - quality_score: Quality score (0-100)
            - is_valid: Whether grant passes validation
            - issues: List of validation issues found
            - categories: Assigned research categories

    Raises:
        Exception: Re-raises on retry exhaustion.
    """
    logger.info("Validating grant", extra={"grant_id": grant_id})

    db = None
    validator = None

    try:
        # Step 1: Fetch grant from database
        db = get_sync_db()
        grant = db.execute(
            select(Grant).where(Grant.id == UUID(grant_id))
        ).scalar_one_or_none()

        if not grant:
            logger.error("Grant not found", extra={"grant_id": grant_id})
            return {
                "grant_id": grant_id,
                "status": "error",
                "message": "Grant not found in database",
            }

        # Step 2: Prepare grant data for validator
        grant_data = {
            "grant_id": str(grant.id),
            "title": grant.title,
            "description": grant.description,
            "deadline": grant.deadline,
            "funding_agency": grant.agency,
            "source": grant.source,
            "external_id": grant.external_id,
            "estimated_amount": grant.amount_max or grant.amount_min,
            "url": grant.url,
        }

        # Step 3: Use validation agent to check quality
        validator = CurationValidator()

        # Import asyncio to run async validation
        import asyncio
        validation_result = asyncio.run(validator.validate_quality(grant_data))

        logger.info(
            "Grant validation completed",
            extra={
                "grant_id": grant_id,
                "quality_score": validation_result.quality_score,
                "is_valid": validation_result.is_valid,
                "issues": validation_result.issues,
            },
        )

        # Step 4: Update grant categories if validated successfully
        if validation_result.is_valid and validation_result.categories:
            grant.categories = validation_result.categories
            db.commit()
            logger.info(
                "Updated grant categories",
                extra={
                    "grant_id": grant_id,
                    "categories": validation_result.categories,
                },
            )

        # Step 5: Flag issues in raw_data for tracking
        if validation_result.issues:
            if grant.raw_data is None:
                grant.raw_data = {}
            grant.raw_data["validation_issues"] = validation_result.issues
            grant.raw_data["quality_score"] = validation_result.quality_score
            db.commit()

        return {
            "grant_id": grant_id,
            "status": "success",
            "quality_score": validation_result.quality_score,
            "is_valid": validation_result.is_valid,
            "issues": validation_result.issues,
            "categories": validation_result.categories,
        }

    except Exception as e:
        if db:
            db.rollback()
        logger.error(
            "Error validating grant",
            extra={
                "grant_id": grant_id,
                "error": str(e),
            },
            exc_info=True,
        )
        raise self.retry(exc=e)

    finally:
        if db:
            db.close()
        if validator:
            validator.close()


# =============================================================================
# Task 3: Compute Grant Embedding
# =============================================================================

@celery_app.task(
    name="backend.tasks.grants.compute_grant_embedding",
    bind=True,
    queue="normal",
    max_retries=5,
    default_retry_delay=10,
    autoretry_for=(openai.RateLimitError,),
)
def compute_grant_embedding(self: Task, grant_id: str) -> dict[str, Any]:
    """
    Generate and store vector embedding for grant.

    Workflow:
        1. Fetch grant from database
        2. Create embedding text from title + description
        3. Call OpenAI API to generate embedding
        4. Store in grant.embedding field (Vector(1536))
        5. Handle rate limits and retries

    Args:
        grant_id: UUID string of the grant

    Returns:
        Dict with embedding generation results:
            - grant_id: Grant UUID
            - status: success/error
            - embedding_length: Length of embedding vector
            - model: Embedding model used

    Raises:
        openai.RateLimitError: Triggers automatic retry with backoff
        Exception: Re-raises other exceptions on retry exhaustion
    """
    logger.info("Computing grant embedding", extra={"grant_id": grant_id})

    db = None
    openai_client = None

    try:
        # Step 1: Fetch grant from database
        db = get_sync_db()
        grant = db.execute(
            select(Grant).where(Grant.id == UUID(grant_id))
        ).scalar_one_or_none()

        if not grant:
            logger.error("Grant not found", extra={"grant_id": grant_id})
            return {
                "grant_id": grant_id,
                "status": "error",
                "message": "Grant not found in database",
            }

        # Skip if embedding already exists
        if grant.embedding is not None:
            logger.info(
                "Grant already has embedding, skipping",
                extra={"grant_id": grant_id},
            )
            return {
                "grant_id": grant_id,
                "status": "skipped",
                "message": "Embedding already exists",
            }

        # Step 2: Create embedding text from title + description
        embedding_text = f"{grant.title or ''}\n\n{grant.description or ''}".strip()

        if not embedding_text:
            logger.warning(
                "Grant has no text for embedding",
                extra={"grant_id": grant_id},
            )
            return {
                "grant_id": grant_id,
                "status": "skipped",
                "message": "No text available for embedding",
            }

        # Truncate to reasonable length (8000 chars ≈ 2000 tokens)
        if len(embedding_text) > 8000:
            embedding_text = embedding_text[:8000]
            logger.info(
                "Truncated embedding text",
                extra={"grant_id": grant_id, "original_length": len(embedding_text)},
            )

        # Step 3: Call OpenAI API to generate embedding
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        openai_client = openai.OpenAI(api_key=settings.openai_api_key)

        # Add rate limit handling with exponential backoff
        try:
            response = openai_client.embeddings.create(
                model=settings.embedding_model,
                input=embedding_text,
            )
            embedding_vector = response.data[0].embedding

        except openai.RateLimitError as e:
            logger.warning(
                "OpenAI rate limit hit, will retry",
                extra={
                    "grant_id": grant_id,
                    "retry_count": self.request.retries,
                },
            )
            # Add jitter to retry delay to prevent thundering herd
            import random
            retry_delay = self.default_retry_delay * (2 ** self.request.retries) + random.uniform(0, 5)
            raise self.retry(exc=e, countdown=int(retry_delay))

        # Step 4: Store in grant.embedding field
        grant.embedding = embedding_vector
        db.commit()

        logger.info(
            "Grant embedding stored successfully",
            extra={
                "grant_id": grant_id,
                "embedding_length": len(embedding_vector),
                "model": settings.embedding_model,
            },
        )

        return {
            "grant_id": grant_id,
            "status": "success",
            "embedding_length": len(embedding_vector),
            "model": settings.embedding_model,
        }

    except openai.RateLimitError:
        # Let the retry decorator handle this
        raise

    except Exception as e:
        if db:
            db.rollback()
        logger.error(
            "Error computing grant embedding",
            extra={
                "grant_id": grant_id,
                "error": str(e),
                "retry_count": self.request.retries,
            },
            exc_info=True,
        )

        # Only retry on certain errors
        if isinstance(e, (openai.APIError, openai.APIConnectionError)):
            raise self.retry(exc=e)
        else:
            # Don't retry on validation or config errors
            return {
                "grant_id": grant_id,
                "status": "error",
                "message": str(e),
            }

    finally:
        if db:
            db.close()


# =============================================================================
# Stream Consumer Task (Bonus)
# =============================================================================

@celery_app.task(
    name="backend.tasks.grants.consume_discovered_grants",
    queue="high",
)
def consume_discovered_grants(batch_size: int = 10, block_ms: int = 5000) -> dict[str, int]:
    """
    Consume grants from "grants:discovered" stream and queue them for processing.

    This task can be scheduled periodically to process discovered grants.

    Args:
        batch_size: Number of grants to process per batch
        block_ms: Milliseconds to block waiting for new messages

    Returns:
        Dict with processing statistics:
            - consumed: Number of grants consumed
            - processed: Number of grants queued for processing
    """
    redis_client = None
    consumed_count = 0
    processed_count = 0

    try:
        redis_client = get_redis_client()

        # Create consumer group if it doesn't exist
        try:
            redis_client.xgroup_create(
                "grants:discovered",
                "grant_processors",
                id="0",
                mkstream=True,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

        # Read messages from stream
        messages = redis_client.xreadgroup(
            "grant_processors",
            "processor_worker",
            {"grants:discovered": ">"},
            count=batch_size,
            block=block_ms,
        )

        if not messages:
            logger.info("No new grants in discovery stream")
            return {"consumed": 0, "processed": 0}

        # Process each message
        for stream_name, stream_messages in messages:
            for message_id, message_data in stream_messages:
                consumed_count += 1

                try:
                    # Parse grant data
                    grant_json = message_data.get("data", "{}")
                    grant_data = json.loads(grant_json)

                    # Queue for processing
                    process_new_grant.delay(grant_data)
                    processed_count += 1

                    # Acknowledge the message
                    redis_client.xack("grants:discovered", "grant_processors", message_id)

                except Exception as e:
                    logger.error(
                        "Error processing discovered grant",
                        extra={
                            "message_id": message_id,
                            "error": str(e),
                        },
                    )
                    # Still acknowledge to prevent reprocessing
                    redis_client.xack("grants:discovered", "grant_processors", message_id)

        logger.info(
            "Consumed grants from discovery stream",
            extra={
                "consumed": consumed_count,
                "processed": processed_count,
            },
        )

        return {
            "consumed": consumed_count,
            "processed": processed_count,
        }

    except Exception as e:
        logger.error(
            "Error consuming discovered grants",
            extra={"error": str(e)},
            exc_info=True,
        )
        return {
            "consumed": consumed_count,
            "processed": processed_count,
            "error": str(e),
        }

    finally:
        if redis_client:
            redis_client.close()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "process_new_grant",
    "validate_grant",
    "compute_grant_embedding",
    "consume_discovered_grants",
]
