"""
GrantRadar Celery Application Configuration

This module configures the Celery distributed task queue for GrantRadar,
including priority queues, retry policies, scheduling, and monitoring.
"""

import logging
import time
from datetime import timedelta
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

from celery import Celery, Task
from celery.signals import (
    task_failure,
    task_postrun,
    task_prerun,
    task_retry,
    task_success,
)
from kombu import Exchange, Queue

from backend.core.config import settings

logger = logging.getLogger(__name__)

# Type variable for generic task decorator
F = TypeVar("F", bound=Callable[..., Any])


# =============================================================================
# Queue Definitions
# =============================================================================

# Define exchanges
default_exchange = Exchange("default", type="direct")
priority_exchange = Exchange("priority", type="direct")

# Define priority queues
TASK_QUEUES = (
    # Critical queue: >90% match alerts, urgent deadlines
    Queue(
        "critical",
        exchange=priority_exchange,
        routing_key="critical",
        queue_arguments={"x-max-priority": 10},
    ),
    # High queue: new grant processing, validation
    Queue(
        "high",
        exchange=priority_exchange,
        routing_key="high",
        queue_arguments={"x-max-priority": 7},
    ),
    # Normal queue: re-indexing, analytics, background tasks
    Queue(
        "normal",
        exchange=default_exchange,
        routing_key="normal",
        queue_arguments={"x-max-priority": 3},
    ),
)

# Task routing configuration
TASK_ROUTES = {
    # Critical priority tasks
    "backend.tasks.notifications.send_high_match_alert": {"queue": "critical"},
    "backend.tasks.notifications.send_deadline_urgent_alert": {"queue": "critical"},
    "backend.tasks.matching.process_high_priority_match": {"queue": "critical"},
    # High priority tasks
    "backend.tasks.grants.process_new_grant": {"queue": "high"},
    "backend.tasks.grants.validate_grant": {"queue": "high"},
    "backend.tasks.matching.compute_grant_matches": {"queue": "high"},
    "backend.tasks.polling.poll_grants_gov": {"queue": "high"},
    "backend.tasks.polling.poll_nsf": {"queue": "high"},
    "backend.tasks.polling.scrape_nih": {"queue": "high"},
    # Normal priority tasks (default)
    "backend.tasks.indexing.reindex_grants": {"queue": "normal"},
    "backend.tasks.analytics.compute_analytics": {"queue": "normal"},
    "backend.tasks.cleanup.cleanup_expired_data": {"queue": "normal"},
    "backend.tasks.cleanup.cleanup_old_alerts": {"queue": "normal"},
    "backend.tasks.cleanup.cleanup_redis_streams": {"queue": "normal"},
    "backend.tasks.cleanup.cleanup_failed_tasks": {"queue": "normal"},
    "backend.tasks.cleanup.archive_old_grants": {"queue": "normal"},
}


# =============================================================================
# Celery Application
# =============================================================================

def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.

    Returns:
        Configured Celery application instance.
    """
    app = Celery(
        "grantradar",
        broker=settings.celery_broker_url,
        backend=settings.celery_result_backend,
        include=[
            "backend.tasks.grants",
            "backend.tasks.matching",
            "backend.tasks.notifications",
            "backend.tasks.polling",
            "backend.tasks.indexing",
            "backend.tasks.analytics",
            "backend.tasks.embeddings",
            "backend.tasks.cleanup",
        ],
    )

    # Core configuration
    app.conf.update(
        # =============
        # Serialization
        # =============
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",

        # =======
        # Queues
        # =======
        task_queues=TASK_QUEUES,
        task_routes=TASK_ROUTES,
        task_default_queue="normal",
        task_default_exchange="default",
        task_default_routing_key="normal",

        # ===========
        # Time Limits
        # ===========
        task_soft_time_limit=300,  # 5 minutes soft limit
        task_time_limit=600,  # 10 minutes hard limit

        # =============
        # Retry Policy
        # =============
        task_default_retry_delay=10,  # 10 seconds initial delay
        task_max_retries=3,

        # ==========
        # Concurrency
        # ==========
        worker_concurrency=4,  # Number of concurrent worker processes
        worker_prefetch_multiplier=2,  # Prefetch 2 tasks per worker

        # ===========
        # Result Backend
        # ===========
        result_expires=86400,  # Results expire after 24 hours
        result_extended=True,  # Store additional metadata

        # ==========
        # Task Track
        # ==========
        task_track_started=True,
        task_acks_late=True,  # Acknowledge after task completes
        task_reject_on_worker_lost=True,

        # ========
        # Timezone
        # ========
        timezone="UTC",
        enable_utc=True,

        # ===========
        # Broker Settings
        # ===========
        broker_connection_retry_on_startup=True,
        broker_pool_limit=10,

        # ==========
        # Beat Schedule
        # ==========
        beat_schedule={
            "grants-gov-poll": {
                "task": "backend.tasks.polling.poll_grants_gov",
                "schedule": timedelta(minutes=5),
                "options": {"queue": "high"},
            },
            "nsf-poll": {
                "task": "backend.tasks.polling.poll_nsf",
                "schedule": timedelta(minutes=15),
                "options": {"queue": "high"},
            },
            "nih-scrape": {
                "task": "backend.tasks.polling.scrape_nih",
                "schedule": timedelta(minutes=30),
                "options": {"queue": "high"},
            },
            "deadline-reminder": {
                "task": "backend.tasks.notifications.send_deadline_reminders",
                "schedule": timedelta(hours=1),
                "options": {"queue": "critical"},
            },
            "analytics-compute": {
                "task": "backend.tasks.analytics.compute_daily_analytics",
                "schedule": timedelta(hours=6),
                "options": {"queue": "normal"},
            },
            "cleanup-expired": {
                "task": "backend.tasks.cleanup.cleanup_expired_data",
                "schedule": timedelta(hours=24),
                "options": {"queue": "normal"},
            },
        },
    )

    return app


# Create the Celery app instance
celery_app = create_celery_app()


# =============================================================================
# Circuit Breaker Pattern
# =============================================================================

class CircuitBreaker:
    """
    Circuit breaker pattern implementation for external API calls.

    Prevents cascading failures by temporarily stopping requests to
    failing external services.

    States:
        - CLOSED: Normal operation, requests pass through
        - OPEN: Service is failing, requests are blocked
        - HALF_OPEN: Testing if service has recovered
    """

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit.
            recovery_timeout: Seconds to wait before testing recovery.
            expected_exception: Exception type to catch.
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._state = self.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._success_count = 0

    @property
    def state(self) -> str:
        """Get current circuit state, checking for recovery timeout."""
        if self._state == self.OPEN:
            if (
                self._last_failure_time
                and time.time() - self._last_failure_time >= self.recovery_timeout
            ):
                self._state = self.HALF_OPEN
        return self._state

    def record_success(self) -> None:
        """Record a successful call."""
        self._failure_count = 0
        if self._state == self.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= 2:  # Require 2 successes to close
                self._state = self.CLOSED
                self._success_count = 0
                logger.info("Circuit breaker closed after successful recovery")

    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        self._success_count = 0

        if self._failure_count >= self.failure_threshold:
            self._state = self.OPEN
            logger.warning(
                f"Circuit breaker opened after {self._failure_count} failures"
            )

    def can_execute(self) -> bool:
        """Check if requests can be executed."""
        return self.state in (self.CLOSED, self.HALF_OPEN)

    def __call__(self, func: F) -> F:
        """Decorator to wrap functions with circuit breaker logic."""
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if not self.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is open for {func.__name__}"
                )

            try:
                result = func(*args, **kwargs)
                self.record_success()
                return result
            except self.expected_exception as e:
                self.record_failure()
                raise e

        return wrapper  # type: ignore


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


# Circuit breakers for external APIs
grants_gov_circuit = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120,  # 2 minutes
)
nsf_circuit = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=120,
)
nih_circuit = CircuitBreaker(
    failure_threshold=5,
    recovery_timeout=180,  # 3 minutes (scraping is more fragile)
)


# =============================================================================
# Priority Routing Helper
# =============================================================================

def route_by_priority(match_score: Optional[float] = None, is_new_grant: bool = False) -> str:
    """
    Determine the appropriate queue based on priority routing logic.

    Args:
        match_score: Grant match score (0-100). Scores >90% route to critical.
        is_new_grant: Whether this is a new grant being processed.

    Returns:
        Queue name: 'critical', 'high', or 'normal'.
    """
    if match_score is not None and match_score > 90:
        return "critical"
    elif is_new_grant:
        return "high"
    else:
        return "normal"


# =============================================================================
# Custom Task Base Class with Retry Policy
# =============================================================================

class BaseTaskWithRetry(Task):
    """
    Base task class with exponential backoff retry policy.

    Implements:
        - 3 retry attempts
        - Exponential backoff starting at 10 seconds
        - Maximum delay of 5 minutes
    """

    autoretry_for = (Exception,)
    max_retries = 3
    retry_backoff = True  # Enable exponential backoff
    retry_backoff_max = 300  # 5 minutes max delay
    retry_jitter = True  # Add randomness to prevent thundering herd

    def on_failure(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Log task failure."""
        logger.error(
            f"Task {self.name}[{task_id}] failed after {self.request.retries} retries: {exc}",
            exc_info=True,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_retry(
        self,
        exc: Exception,
        task_id: str,
        args: tuple,
        kwargs: dict,
        einfo: Any,
    ) -> None:
        """Log task retry."""
        logger.warning(
            f"Task {self.name}[{task_id}] retrying (attempt {self.request.retries + 1}/{self.max_retries}): {exc}"
        )
        super().on_retry(exc, task_id, args, kwargs, einfo)


# Register base task class
celery_app.Task = BaseTaskWithRetry


# =============================================================================
# Monitoring Hooks
# =============================================================================

# Store for task latency tracking
_task_start_times: dict[str, float] = {}


@task_prerun.connect
def task_prerun_handler(
    sender: Task | None = None,
    task_id: str | None = None,
    task: Task | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    **extra: Any,
) -> None:
    """Record task start time for latency tracking."""
    if task_id:
        _task_start_times[task_id] = time.time()
        logger.debug(f"Task {sender.name if sender else 'unknown'}[{task_id}] started")


@task_postrun.connect
def task_postrun_handler(
    sender: Task | None = None,
    task_id: str | None = None,
    task: Task | None = None,
    args: tuple | None = None,
    kwargs: dict | None = None,
    retval: Any = None,
    state: str | None = None,
    **extra: Any,
) -> None:
    """Calculate and log task latency."""
    if task_id and task_id in _task_start_times:
        latency = time.time() - _task_start_times.pop(task_id)
        task_name = sender.name if sender else "unknown"

        # Log latency for monitoring
        logger.info(
            f"Task {task_name}[{task_id}] completed in {latency:.3f}s with state={state}"
        )

        # Here you could emit metrics to your monitoring system
        # e.g., prometheus_client, datadog, etc.
        emit_task_metric(task_name, latency, state)


@task_success.connect
def task_success_handler(
    sender: Task | None = None,
    result: Any = None,
    **kwargs: Any,
) -> None:
    """Handle successful task completion."""
    logger.debug(f"Task {sender.name if sender else 'unknown'} succeeded")


@task_failure.connect
def task_failure_handler(
    sender: Task | None = None,
    task_id: str | None = None,
    exception: Exception | None = None,
    traceback: Any = None,
    **kwargs: Any,
) -> None:
    """Handle task failure."""
    logger.error(
        f"Task {sender.name if sender else 'unknown'}[{task_id}] failed: {exception}"
    )
    # Clean up start time if present
    if task_id:
        _task_start_times.pop(task_id, None)


@task_retry.connect
def task_retry_handler(
    sender: Task | None = None,
    request: Any = None,
    reason: Any = None,
    **kwargs: Any,
) -> None:
    """Handle task retry."""
    task_id = request.id if request else "unknown"
    logger.warning(f"Task {sender.name if sender else 'unknown'}[{task_id}] retrying: {reason}")


def emit_task_metric(task_name: str, latency: float, state: str | None) -> None:
    """
    Emit task metrics to monitoring system.

    This is a placeholder for integration with monitoring systems like:
    - Prometheus
    - Datadog
    - CloudWatch
    - StatsD

    Args:
        task_name: Name of the completed task.
        latency: Task execution time in seconds.
        state: Final task state.
    """
    # TODO: Integrate with actual monitoring system
    # Example with prometheus_client:
    # TASK_LATENCY.labels(task=task_name).observe(latency)
    # TASK_COUNTER.labels(task=task_name, state=state).inc()
    pass


# =============================================================================
# Convenience Decorators
# =============================================================================

def critical_task(func: F) -> F:
    """Decorator to mark a task as critical priority."""
    return celery_app.task(queue="critical", priority=10)(func)


def high_priority_task(func: F) -> F:
    """Decorator to mark a task as high priority."""
    return celery_app.task(queue="high", priority=7)(func)


def normal_task(func: F) -> F:
    """Decorator to mark a task as normal priority."""
    return celery_app.task(queue="normal", priority=3)(func)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "celery_app",
    "BaseTaskWithRetry",
    "CircuitBreaker",
    "CircuitBreakerOpenError",
    "grants_gov_circuit",
    "nsf_circuit",
    "nih_circuit",
    "route_by_priority",
    "critical_task",
    "high_priority_task",
    "normal_task",
]
