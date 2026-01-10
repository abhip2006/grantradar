"""
Sentry Error Tracking Configuration
Centralized Sentry SDK initialization for the GrantRadar backend.
"""

import logging
from typing import Any

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from backend.core.config import settings

logger = logging.getLogger(__name__)


def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Process events before sending to Sentry.

    Filter out sensitive data or certain error types.
    """
    # Filter out health check errors
    if "request" in event and event["request"].get("url", "").endswith("/health"):
        return None

    # Remove sensitive headers if present
    if "request" in event and "headers" in event["request"]:
        sensitive_headers = ["authorization", "cookie", "x-api-key"]
        for header in sensitive_headers:
            if header in event["request"]["headers"]:
                event["request"]["headers"][header] = "[REDACTED]"

    return event


def before_send_transaction(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Process transactions before sending to Sentry.

    Filter out health check and other high-volume low-value transactions.
    """
    transaction_name = event.get("transaction", "")

    # Skip health check endpoints from performance monitoring
    if transaction_name in ["/health", "/health/ready", "/health/live"]:
        return None

    return event


def init_sentry() -> bool:
    """
    Initialize Sentry SDK with FastAPI integration.

    Returns:
        bool: True if Sentry was initialized successfully, False otherwise.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry DSN not configured, error tracking disabled")
        return False

    try:
        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.sentry_environment or settings.environment,
            release=f"grantradar-backend@{settings.app_version}",
            # Performance monitoring
            traces_sample_rate=settings.sentry_traces_sample_rate,
            profiles_sample_rate=settings.sentry_profiles_sample_rate,
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                StarletteIntegration(transaction_style="endpoint"),
                LoggingIntegration(
                    level=logging.INFO,
                    event_level=logging.ERROR,
                ),
                SqlalchemyIntegration(),
            ],
            # Event processing
            before_send=before_send,
            before_send_transaction=before_send_transaction,
            # Additional options
            send_default_pii=False,  # Don't send PII by default
            attach_stacktrace=True,  # Attach stack traces to log messages
            max_breadcrumbs=50,  # Limit breadcrumbs
            # Debug mode for development (logs Sentry events)
            debug=settings.debug and settings.environment == "development",
        )

        # Set user context if available (will be updated per-request)
        sentry_sdk.set_tag("service", "backend")
        sentry_sdk.set_tag("app_name", settings.app_name)

        logger.info(
            f"Sentry initialized successfully "
            f"(env={settings.sentry_environment or settings.environment}, "
            f"traces={settings.sentry_traces_sample_rate}, "
            f"profiles={settings.sentry_profiles_sample_rate})"
        )
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")
        return False


def capture_exception(
    error: Exception,
    user_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str | None:
    """
    Capture an exception and send to Sentry.

    Args:
        error: The exception to capture
        user_id: Optional user ID for context
        extra: Optional extra data to attach

    Returns:
        Event ID if captured, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        event_id = sentry_sdk.capture_exception(error)
        return event_id


def capture_message(
    message: str,
    level: str = "info",
    user_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> str | None:
    """
    Capture a message and send to Sentry.

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        user_id: Optional user ID for context
        extra: Optional extra data to attach

    Returns:
        Event ID if captured, None otherwise
    """
    with sentry_sdk.push_scope() as scope:
        if user_id:
            scope.set_user({"id": user_id})

        if extra:
            for key, value in extra.items():
                scope.set_extra(key, value)

        event_id = sentry_sdk.capture_message(message, level=level)
        return event_id


def set_user_context(user_id: str, email: str | None = None) -> None:
    """
    Set user context for Sentry events.

    Call this after authentication to associate errors with users.
    """
    sentry_sdk.set_user(
        {
            "id": user_id,
            "email": email,
        }
    )


def clear_user_context() -> None:
    """Clear user context (e.g., on logout)."""
    sentry_sdk.set_user(None)
