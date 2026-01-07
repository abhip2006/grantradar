"""
GrantRadar Celery Tasks

This package contains all Celery task definitions for the GrantRadar platform.

Task Modules:
    - grants: Grant data processing and validation tasks
    - matching: Profile-to-grant matching computation tasks
    - notifications: Email, SMS, and push notification tasks
    - polling: External API polling tasks (Grants.gov, NSF, NIH)
    - indexing: Search index and embedding generation tasks
    - analytics: Analytics computation and reporting tasks
    - cleanup: Data cleanup and maintenance tasks

Queue Priorities:
    - critical: >90% match alerts, urgent deadlines (highest priority)
    - high: New grant processing, validation
    - normal: Re-indexing, analytics, background tasks

Usage:
    from backend.tasks import grants, matching, notifications

    # Queue a new grant for processing
    grants.process_new_grant.delay(grant_id="12345")

    # Compute matches for a researcher profile
    matching.compute_grant_matches.delay(profile_id="abc123")

    # Send high-match alert (routed to critical queue)
    notifications.send_high_match_alert.delay(
        user_id="user123",
        grant_id="grant456",
        match_score=95.5,
    )
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Import task modules for type checking only
    # Actual imports happen at runtime to avoid circular dependencies
    from backend.tasks import (
        analytics,
        cleanup,
        embeddings,
        grants,
        indexing,
        matching,
        notifications,
        polling,
    )

# Version of the tasks package
__version__ = "1.0.0"

# Task modules will be auto-discovered by Celery via celery_app.py include config
__all__ = [
    "grants",
    "matching",
    "notifications",
    "polling",
    "indexing",
    "analytics",
    "cleanup",
    "embeddings",
]
