"""
Curation/Validation Agent
Consumes from 'grants:discovered' stream, validates, enriches, and deduplicates grants.
"""

import json
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

import openai
import redis
import structlog
from celery import Celery
from pydantic import BaseModel, Field

from backend.core.config import settings

# Initialize logger
logger = structlog.get_logger().bind(agent="curation", component="validator")

# Initialize Celery with high priority queue
celery_app = Celery(
    "curation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_routes={
        "agents.curation.validator.*": {"queue": "high_priority"},
    },
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


# ===== Pydantic Models =====


class ValidationResult(BaseModel):
    """Result of grant quality validation."""

    is_valid: bool = Field(..., description="Whether the grant passed validation")
    quality_score: int = Field(..., ge=0, le=100, description="Quality score from 0-100")
    issues: list[str] = Field(default_factory=list, description="List of validation issues found")
    categories: list[str] = Field(default_factory=list, description="Assigned research categories")


class EnrichedGrant(BaseModel):
    """Grant with all enriched fields including embedding."""

    grant_id: UUID = Field(..., description="Unique identifier for the grant")
    external_id: Optional[str] = Field(default=None, description="External ID from source")
    source: str = Field(..., description="Source of the grant")
    title: str = Field(..., description="Grant title")
    description: Optional[str] = Field(default=None, description="Grant description")
    url: str = Field(..., description="URL to the original grant posting")
    funding_agency: Optional[str] = Field(default=None, description="Name of the funding agency")
    estimated_amount: Optional[float] = Field(default=None, description="Estimated funding amount in USD")
    deadline: Optional[datetime] = Field(default=None, description="Application deadline")
    discovered_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the grant was discovered",
    )
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the grant was validated",
    )
    categories: list[str] = Field(default_factory=list, description="Research categories")
    embedding: Optional[list[float]] = Field(default=None, description="Vector embedding for semantic search")
    quality_score: int = Field(default=0, ge=0, le=100, description="Quality score from validation")
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence after deduplication")
    eligibility_criteria: Optional[list[str]] = Field(default=None, description="Extracted eligibility criteria")
    keywords: Optional[list[str]] = Field(default=None, description="Extracted keywords")
    raw_data: Optional[dict] = Field(default=None, description="Original raw data from source")


class ManualReviewEntry(BaseModel):
    """Entry for grants requiring manual review."""

    grant_id: UUID = Field(..., description="ID of the grant requiring review")
    reason: str = Field(..., description="Reason for manual review")
    quality_score: int = Field(default=0, ge=0, le=100, description="Quality score that triggered review")
    issues: list[str] = Field(default_factory=list, description="Validation issues found")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the review entry was created",
    )
    grant_data: Optional[dict] = Field(default=None, description="Original grant data for review")


# ===== Core Validator Class =====


class CurationValidator:
    """
    Validates, enriches, and deduplicates discovered grants.

    Consumes from 'grants:discovered' stream and publishes validated
    grants to 'grants:validated' stream.
    """

    INPUT_STREAM = "grants:discovered"
    OUTPUT_STREAM = "grants:validated"
    CONSUMER_GROUP = "curation_validators"
    CONSUMER_NAME = "validator_worker"
    MANUAL_REVIEW_KEY = "grants:manual_review"
    QUALITY_THRESHOLD = 70

    # Research categories for classification
    VALID_CATEGORIES = [
        "Biomedical",
        "Computer Science",
        "Physics",
        "Chemistry",
        "Social Sciences",
        "Engineering",
        "Environmental Science",
        "Mathematics",
        "Psychology",
        "Economics",
        "Other",
    ]

    def __init__(self):
        """Initialize the curation validator."""
        self.logger = logger.bind(validator="curation")
        self._redis_client: Optional[redis.Redis] = None
        self._openai_client: Optional[openai.OpenAI] = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy-loaded Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(settings.redis_url, decode_responses=True)
        return self._redis_client

    @property
    def openai_client(self) -> openai.OpenAI:
        """Lazy-loaded OpenAI client."""
        if self._openai_client is None:
            if not settings.openai_api_key:
                raise ValueError("OPENAI_API_KEY is required for validation and embeddings")
            self._openai_client = openai.OpenAI(api_key=settings.openai_api_key)
        return self._openai_client

    def _ensure_consumer_group(self) -> None:
        """Create consumer group if it doesn't exist."""
        try:
            self.redis_client.xgroup_create(self.INPUT_STREAM, self.CONSUMER_GROUP, id="0", mkstream=True)
            self.logger.info(
                "consumer_group_created",
                stream=self.INPUT_STREAM,
                group=self.CONSUMER_GROUP,
            )
        except redis.ResponseError as e:
            if "BUSYGROUP" not in str(e):
                raise

    async def validate_quality(self, grant_data: dict[str, Any]) -> ValidationResult:
        """
        Validate grant quality using Claude LLM.

        Args:
            grant_data: Raw grant data from discovery

        Returns:
            ValidationResult with is_valid, quality_score, and issues
        """
        title = grant_data.get("title", "")
        description = grant_data.get("description", "")
        deadline = grant_data.get("deadline")
        funding_agency = grant_data.get("funding_agency", "")

        # Check if deadline has passed
        is_expired = False
        if deadline:
            try:
                if isinstance(deadline, str):
                    deadline_dt = datetime.fromisoformat(deadline.replace("Z", "+00:00"))
                else:
                    deadline_dt = deadline
                is_expired = deadline_dt < datetime.now(timezone.utc)
            except (ValueError, TypeError):
                pass

        prompt = f"""Is this a legitimate research grant? Check the following criteria:
(1) Has title and description
(2) Has deadline
(3) Not expired (deadline not in the past)
(4) For research (not community grants, scholarships for individuals, or non-research funding)

Grant Details:
- Title: {title}
- Description: {description[:1000] if description else "Not provided"}
- Deadline: {deadline if deadline else "Not provided"}
- Funding Agency: {funding_agency if funding_agency else "Not provided"}
- Is Expired: {is_expired}

Return ONLY a JSON object with this exact structure:
{{"is_valid": true/false, "quality_score": 0-100, "issues": ["issue1", "issue2"]}}

The quality_score should reflect:
- 90-100: Excellent - complete information, clearly a research grant
- 70-89: Good - mostly complete, likely a research grant
- 50-69: Fair - some missing info or unclear if research-focused
- 0-49: Poor - significant issues or not a research grant"""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content.strip()
            # Extract JSON from response
            if "{" in response_text:
                json_start = response_text.index("{")
                json_end = response_text.rindex("}") + 1
                json_str = response_text[json_start:json_end]
                result_data = json.loads(json_str)

                return ValidationResult(
                    is_valid=result_data.get("is_valid", False),
                    quality_score=result_data.get("quality_score", 0),
                    issues=result_data.get("issues", []),
                )
        except Exception as e:
            self.logger.error("validation_llm_error", error=str(e))

        # Fallback validation if LLM fails
        issues = []
        score = 100

        if not title:
            issues.append("Missing title")
            score -= 30

        if not description:
            issues.append("Missing description")
            score -= 20

        if not deadline:
            issues.append("Missing deadline")
            score -= 20

        if is_expired:
            issues.append("Grant deadline has passed")
            score -= 50

        return ValidationResult(
            is_valid=score >= self.QUALITY_THRESHOLD,
            quality_score=max(0, score),
            issues=issues,
        )

    async def categorize_grant(self, title: str, description: str) -> list[str]:
        """
        Categorize grant using Claude LLM.

        Args:
            title: Grant title
            description: Grant description

        Returns:
            List of 2-5 research categories
        """
        categories_str = ", ".join(self.VALID_CATEGORIES)

        prompt = f"""Assign research categories to this grant.

Title: {title}
Description: {description[:1500] if description else "Not provided"}

Return an array of 2-5 categories from this list ONLY: [{categories_str}]

Return ONLY a JSON array, e.g.: ["Computer Science", "Engineering"]"""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content.strip()
            # Extract JSON array from response
            if "[" in response_text:
                json_start = response_text.index("[")
                json_end = response_text.rindex("]") + 1
                json_str = response_text[json_start:json_end]
                categories = json.loads(json_str)

                # Validate categories against allowed list
                valid_categories = [c for c in categories if c in self.VALID_CATEGORIES]
                if valid_categories:
                    return valid_categories[:5]  # Max 5 categories
        except Exception as e:
            self.logger.error("categorization_llm_error", error=str(e))

        # Fallback to "Other" if categorization fails
        return ["Other"]

    async def generate_embedding(self, text: str) -> Optional[list[float]]:
        """
        Generate embedding using OpenAI text-embedding-3-small.

        Args:
            text: Text to embed (title + description)

        Returns:
            List of floats representing the embedding vector
        """
        if not text or not text.strip():
            return None

        try:
            # Truncate text if too long (8191 tokens max for embedding model)
            truncated_text = text[:8000]

            response = self.openai_client.embeddings.create(
                model=settings.embedding_model,
                input=truncated_text,
            )

            return response.data[0].embedding
        except Exception as e:
            self.logger.error("embedding_generation_error", error=str(e))
            return None

    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calculate Levenshtein distance between two strings."""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    async def find_potential_duplicates(self, grant_data: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Find potential duplicate grants in the database.

        Checks for:
        - Similar title (Levenshtein distance < 3)
        - Same external_id from different source

        Args:
            grant_data: Grant data to check

        Returns:
            List of potential duplicate grants
        """
        duplicates = []
        title = grant_data.get("title", "")
        external_id = grant_data.get("external_id")
        source = grant_data.get("source")

        # Get recently validated grants from Redis for quick duplicate check
        # In production, this would query the PostgreSQL grants table
        validated_grants_key = "grants:validated:recent"

        try:
            recent_grants = self.redis_client.lrange(validated_grants_key, 0, 1000)

            for grant_json in recent_grants:
                try:
                    existing_grant = json.loads(grant_json)
                    existing_title = existing_grant.get("title", "")
                    existing_external_id = existing_grant.get("external_id")
                    existing_source = existing_grant.get("source")

                    # Check title similarity
                    if title and existing_title:
                        distance = self._levenshtein_distance(title.lower()[:100], existing_title.lower()[:100])
                        if distance < 3:
                            duplicates.append(existing_grant)
                            continue

                    # Check same external_id from different source
                    if (
                        external_id
                        and existing_external_id
                        and external_id == existing_external_id
                        and source != existing_source
                    ):
                        duplicates.append(existing_grant)
                except json.JSONDecodeError:
                    continue
        except Exception as e:
            self.logger.error("duplicate_check_error", error=str(e))

        return duplicates

    async def check_is_duplicate(self, grant1: dict[str, Any], grant2: dict[str, Any]) -> bool:
        """
        Use LLM to determine if two grants are duplicates.

        Args:
            grant1: First grant data
            grant2: Second grant data

        Returns:
            True if grants are duplicates
        """
        prompt = f"""Are these two grants the same grant opportunity (possibly from different sources)?

Grant 1:
- Title: {grant1.get("title", "N/A")}
- Funding Agency: {grant1.get("funding_agency", "N/A")}
- Deadline: {grant1.get("deadline", "N/A")}
- Amount: {grant1.get("estimated_amount", "N/A")}
- Source: {grant1.get("source", "N/A")}
- Description snippet: {str(grant1.get("description", ""))[:500]}

Grant 2:
- Title: {grant2.get("title", "N/A")}
- Funding Agency: {grant2.get("funding_agency", "N/A")}
- Deadline: {grant2.get("deadline", "N/A")}
- Amount: {grant2.get("estimated_amount", "N/A")}
- Source: {grant2.get("source", "N/A")}
- Description snippet: {str(grant2.get("description", ""))[:500]}

Return ONLY "true" if these are the same grant, or "false" if they are different grants."""

        try:
            response = self.openai_client.chat.completions.create(
                model=settings.llm_model,
                max_tokens=50,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.choices[0].message.content.strip().lower()
            return response_text == "true" or "true" in response_text
        except Exception as e:
            self.logger.error("duplicate_check_llm_error", error=str(e))
            return False

    def _merge_grants(self, grant1: dict[str, Any], grant2: dict[str, Any]) -> dict[str, Any]:
        """
        Merge two duplicate grants, keeping the most complete version.

        Args:
            grant1: First grant data
            grant2: Second grant data

        Returns:
            Merged grant data
        """
        merged = {}

        # Fields to merge, preferring non-empty values
        fields = [
            "title",
            "description",
            "url",
            "funding_agency",
            "estimated_amount",
            "deadline",
            "eligibility_criteria",
            "keywords",
        ]

        for field in fields:
            val1 = grant1.get(field)
            val2 = grant2.get(field)

            if val1 and val2:
                # Prefer longer description
                if field == "description":
                    merged[field] = val1 if len(str(val1)) >= len(str(val2)) else val2
                else:
                    merged[field] = val1  # Keep first by default
            else:
                merged[field] = val1 if val1 else val2

        # Keep source information from both
        sources = []
        if grant1.get("source"):
            sources.append(grant1["source"])
        if grant2.get("source") and grant2["source"] not in sources:
            sources.append(grant2["source"])
        merged["source"] = sources[0] if sources else "unknown"
        merged["sources"] = sources

        # Keep earliest discovered_at
        discovered1 = grant1.get("discovered_at")
        discovered2 = grant2.get("discovered_at")
        if discovered1 and discovered2:
            merged["discovered_at"] = min(discovered1, discovered2)
        else:
            merged["discovered_at"] = discovered1 or discovered2

        # Keep the grant_id from the first grant
        merged["grant_id"] = grant1.get("grant_id") or grant2.get("grant_id")
        merged["external_id"] = grant1.get("external_id") or grant2.get("external_id")

        return merged

    async def log_manual_review(self, grant_data: dict[str, Any], validation_result: ValidationResult) -> None:
        """
        Log a grant to the manual review queue.

        Args:
            grant_data: Original grant data
            validation_result: Validation result that triggered review
        """
        grant_id = grant_data.get("grant_id") or str(uuid4())

        review_entry = ManualReviewEntry(
            grant_id=UUID(grant_id) if isinstance(grant_id, str) else grant_id,
            reason=f"Quality score below threshold: {validation_result.quality_score}/100",
            quality_score=validation_result.quality_score,
            issues=validation_result.issues,
            grant_data=grant_data,
        )

        try:
            self.redis_client.lpush(self.MANUAL_REVIEW_KEY, review_entry.model_dump_json())
            self.logger.info(
                "grant_logged_for_review",
                grant_id=str(grant_id),
                quality_score=validation_result.quality_score,
                issues=validation_result.issues,
            )
        except Exception as e:
            self.logger.error("manual_review_log_error", grant_id=str(grant_id), error=str(e))

    async def publish_validated_grant(self, enriched_grant: EnrichedGrant) -> str:
        """
        Publish validated grant to the output stream.

        Args:
            enriched_grant: Fully validated and enriched grant

        Returns:
            Redis stream message ID
        """
        # Prepare event data matching GrantValidatedEvent structure
        event_data = {
            "event_id": str(uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0",
            "grant_id": str(enriched_grant.grant_id),
            "quality_score": enriched_grant.quality_score / 100.0,  # Normalize to 0-1
            "categories": enriched_grant.categories,
            "embedding_generated": enriched_grant.embedding is not None,
            "validation_details": {
                "confidence_score": enriched_grant.confidence_score,
                "validated_at": enriched_grant.validated_at.isoformat(),
            },
            "eligibility_criteria": enriched_grant.eligibility_criteria,
            "keywords": enriched_grant.keywords,
        }

        message = {"data": json.dumps(event_data)}
        message_id = self.redis_client.xadd(self.OUTPUT_STREAM, message)

        # Also store the full enriched grant for quick access
        grant_json = enriched_grant.model_dump_json()
        self.redis_client.lpush("grants:validated:recent", grant_json)
        # Keep only last 1000 grants in the recent list
        self.redis_client.ltrim("grants:validated:recent", 0, 999)

        self.logger.info(
            "grant_validated_published",
            grant_id=str(enriched_grant.grant_id),
            quality_score=enriched_grant.quality_score,
            categories=enriched_grant.categories,
            message_id=message_id,
        )

        return message_id

    async def process_grant(self, grant_data: dict[str, Any]) -> Optional[EnrichedGrant]:
        """
        Process a single discovered grant through the full validation pipeline.

        Args:
            grant_data: Raw grant data from discovery stream

        Returns:
            EnrichedGrant if validation passes, None otherwise
        """
        grant_id = grant_data.get("grant_id") or str(uuid4())
        self.logger.info(
            "processing_grant",
            grant_id=grant_id,
            title=grant_data.get("title", "")[:100],
        )

        # Step 1: Quality validation
        validation_result = await self.validate_quality(grant_data)

        if validation_result.quality_score < self.QUALITY_THRESHOLD:
            # Log for manual review and skip
            await self.log_manual_review(grant_data, validation_result)
            self.logger.info(
                "grant_below_quality_threshold",
                grant_id=grant_id,
                quality_score=validation_result.quality_score,
            )
            return None

        # Step 2: Categorization
        title = grant_data.get("title", "")
        description = grant_data.get("description", "")
        categories = await self.categorize_grant(title, description)
        validation_result.categories = categories

        # Step 3: Generate embedding
        embedding_text = f"{title} {description}".strip()
        embedding = await self.generate_embedding(embedding_text)

        # Step 4: Check for duplicates
        potential_duplicates = await self.find_potential_duplicates(grant_data)
        confidence_score = 1.0
        final_grant_data = grant_data.copy()

        for duplicate in potential_duplicates:
            is_duplicate = await self.check_is_duplicate(grant_data, duplicate)
            if is_duplicate:
                self.logger.info(
                    "duplicate_found",
                    grant_id=grant_id,
                    duplicate_id=duplicate.get("grant_id"),
                )
                # Merge and update confidence
                final_grant_data = self._merge_grants(grant_data, duplicate)
                confidence_score = min(confidence_score, 0.8)  # Lower confidence for merged

        # Step 5: Create enriched grant
        enriched_grant = EnrichedGrant(
            grant_id=UUID(grant_id) if isinstance(grant_id, str) else grant_id,
            external_id=final_grant_data.get("external_id"),
            source=final_grant_data.get("source", "unknown"),
            title=final_grant_data.get("title", ""),
            description=final_grant_data.get("description"),
            url=final_grant_data.get("url", ""),
            funding_agency=final_grant_data.get("funding_agency"),
            estimated_amount=final_grant_data.get("estimated_amount"),
            deadline=(
                datetime.fromisoformat(final_grant_data["deadline"].replace("Z", "+00:00"))
                if isinstance(final_grant_data.get("deadline"), str)
                else final_grant_data.get("deadline")
            ),
            discovered_at=(
                datetime.fromisoformat(final_grant_data["discovered_at"].replace("Z", "+00:00"))
                if isinstance(final_grant_data.get("discovered_at"), str)
                else final_grant_data.get("discovered_at", datetime.now(timezone.utc))
            ),
            categories=categories,
            embedding=embedding,
            quality_score=validation_result.quality_score,
            confidence_score=confidence_score,
            eligibility_criteria=final_grant_data.get("eligibility_criteria"),
            keywords=final_grant_data.get("keywords"),
            raw_data=final_grant_data.get("raw_data"),
        )

        # Step 6: Publish to validated stream
        await self.publish_validated_grant(enriched_grant)

        return enriched_grant

    async def consume_stream(self, count: int = 10, block_ms: int = 5000) -> int:
        """
        Consume and process grants from the discovery stream.

        Args:
            count: Maximum number of messages to process per batch
            block_ms: How long to block waiting for new messages

        Returns:
            Number of grants successfully processed
        """
        self._ensure_consumer_group()

        processed = 0

        try:
            # Read new messages from the stream
            messages = self.redis_client.xreadgroup(
                self.CONSUMER_GROUP,
                self.CONSUMER_NAME,
                {self.INPUT_STREAM: ">"},
                count=count,
                block=block_ms,
            )

            if not messages:
                return 0

            for stream_name, stream_messages in messages:
                for message_id, message_data in stream_messages:
                    try:
                        # Parse grant data
                        grant_json = message_data.get("data", "{}")
                        grant_data = json.loads(grant_json)

                        # Process the grant
                        result = await self.process_grant(grant_data)

                        # Acknowledge the message
                        self.redis_client.xack(self.INPUT_STREAM, self.CONSUMER_GROUP, message_id)

                        if result:
                            processed += 1

                    except Exception as e:
                        self.logger.error(
                            "grant_processing_error",
                            message_id=message_id,
                            error=str(e),
                        )
                        # Still acknowledge to prevent reprocessing
                        # In production, might want to move to DLQ instead
                        self.redis_client.xack(self.INPUT_STREAM, self.CONSUMER_GROUP, message_id)

        except Exception as e:
            self.logger.error("stream_consumption_error", error=str(e))

        return processed

    def close(self) -> None:
        """Clean up resources."""
        if self._redis_client:
            self._redis_client.close()
            self._redis_client = None


# ===== Celery Tasks =====


@celery_app.task(
    name="agents.curation.validator.validate_grant_task",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def validate_grant_task(self, grant_data: dict[str, Any]) -> Optional[dict]:
    """
    Celery task to validate a single grant.

    Args:
        grant_data: Raw grant data from discovery

    Returns:
        Enriched grant data if valid, None otherwise
    """
    import asyncio

    validator = CurationValidator()
    try:
        result = asyncio.run(validator.process_grant(grant_data))
        return result.model_dump() if result else None
    except Exception as e:
        logger.error("validate_grant_task_error", error=str(e))
        raise self.retry(exc=e)
    finally:
        validator.close()


@celery_app.task(
    name="agents.curation.validator.consume_discovery_stream_task",
    bind=True,
)
def consume_discovery_stream_task(self, count: int = 10, block_ms: int = 5000) -> dict[str, int]:
    """
    Celery task to consume and process grants from discovery stream.

    Args:
        count: Maximum messages per batch
        block_ms: Blocking timeout in milliseconds

    Returns:
        Dict with processing statistics
    """
    import asyncio

    validator = CurationValidator()
    try:
        processed = asyncio.run(validator.consume_stream(count, block_ms))
        return {"processed": processed, "status": "success"}
    except Exception as e:
        logger.error("consume_stream_task_error", error=str(e))
        return {"processed": 0, "status": "error", "error": str(e)}
    finally:
        validator.close()


@celery_app.task(name="agents.curation.validator.run_validator_worker")
def run_validator_worker(batch_size: int = 10, iterations: int = 100) -> dict[str, int]:
    """
    Long-running Celery task that continuously processes the discovery stream.

    Args:
        batch_size: Number of messages to process per iteration
        iterations: Number of iterations before task completes

    Returns:
        Dict with total processing statistics
    """
    import asyncio

    validator = CurationValidator()
    total_processed = 0

    try:
        for i in range(iterations):
            processed = asyncio.run(validator.consume_stream(batch_size, block_ms=1000))
            total_processed += processed

            if processed == 0:
                # No messages available, wait a bit before next iteration
                import time

                time.sleep(1)

        return {"total_processed": total_processed, "iterations": iterations}
    except Exception as e:
        logger.error("validator_worker_error", error=str(e))
        return {"total_processed": total_processed, "error": str(e)}
    finally:
        validator.close()
