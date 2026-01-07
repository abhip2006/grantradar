"""
Curation Agent Module
Handles validation, enrichment, and deduplication of discovered grants.
"""
from agents.curation.validator import (
    CurationValidator,
    EnrichedGrant,
    ManualReviewEntry,
    ValidationResult,
    celery_app,
    consume_discovery_stream_task,
    run_validator_worker,
    validate_grant_task,
)

__all__ = [
    "CurationValidator",
    "ValidationResult",
    "EnrichedGrant",
    "ManualReviewEntry",
    "celery_app",
    "validate_grant_task",
    "consume_discovery_stream_task",
    "run_validator_worker",
]
