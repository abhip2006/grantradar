"""
GrantRadar FastAPI Application
Main entry point for the grant intelligence platform API.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

import socketio
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.api import (
    admin_analytics,
    admin_seed,
    aims,
    alerts,
    analytics,
    api_keys,
    audit,
    auth,
    budgets,
    calendar,
    chat,
    checklists,
    compare,
    compliance,
    compliance_engine,
    components,
    contact,
    deadlines,
    effort,
    eligibility,
    filters,
    forecast,
    funder_insights,
    grants,
    health,
    insights,
    institution,
    integrations,
    intelligence,
    kanban,
    matches,
    notifications,
    permission_templates,
    pipeline,
    preferences,
    probability,
    profile,
    reminders,
    research,
    reviews,
    saved_searches,
    sharing,
    similar,
    stats,
    team,
    team_collaboration,
    templates,
    verification,
    winners,
    workflow_analytics,
    writing,
)
from backend.core.config import settings
from backend.core.rate_limit import (
    RateLimitMiddleware,
    close_rate_limiter,
    rate_limit_exception_handler,
)
from backend.core.sentry import capture_exception, init_sentry
from backend.database import close_db, init_db

# =============================================================================
# Logging Configuration
# =============================================================================

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# =============================================================================
# Socket.IO Setup
# =============================================================================


# Create Socket.IO server with CORS support
# SECURITY: Never use wildcard "*" for CORS - always specify allowed origins
def get_socketio_cors_origins() -> list:
    """Get allowed origins for Socket.IO CORS."""
    origins = [settings.frontend_url]
    if settings.debug:
        # In debug mode, also allow common development ports
        origins.extend(
            [
                "http://localhost:3000",
                "http://localhost:5173",
                "http://localhost:5174",
                "http://127.0.0.1:3000",
                "http://127.0.0.1:5173",
                "http://127.0.0.1:5174",
            ]
        )
    return origins


sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=get_socketio_cors_origins(),
    logger=settings.debug,
    engineio_logger=settings.debug,
)


@sio.event
async def connect(sid: str, environ: dict) -> bool:
    """Handle client connection."""
    logger.info(f"Client connected: {sid}")
    return True


@sio.event
async def disconnect(sid: str) -> None:
    """Handle client disconnection."""
    logger.info(f"Client disconnected: {sid}")


@sio.event
async def subscribe_matches(sid: str, data: dict) -> None:
    """Subscribe to match updates for a user."""
    user_id = data.get("user_id")
    if user_id:
        await sio.enter_room(sid, f"user_{user_id}")
        logger.info(f"Client {sid} subscribed to matches for user {user_id}")


@sio.event
async def unsubscribe_matches(sid: str, data: dict) -> None:
    """Unsubscribe from match updates."""
    user_id = data.get("user_id")
    if user_id:
        await sio.leave_room(sid, f"user_{user_id}")
        logger.info(f"Client {sid} unsubscribed from matches for user {user_id}")


# Helper function to emit match notifications
async def notify_new_match(user_id: str, match_data: dict) -> None:
    """Send new match notification to a user."""
    await sio.emit("new_match", match_data, room=f"user_{user_id}")


# =============================================================================
# Lifespan Events
# =============================================================================


def validate_security_settings() -> None:
    """
    Validate critical security settings at startup.
    Raises RuntimeError if insecure configuration detected in production.
    """
    import os

    is_production = settings.environment.lower() in ("production", "prod")
    warnings = []
    errors = []

    # Check secret key
    insecure_keys = [
        "dev-secret-key-change-in-production",
        "CHANGE-THIS-IN-PRODUCTION-REQUIRED",
        "secret",
        "changeme",
    ]
    if settings.secret_key in insecure_keys or len(settings.secret_key) < 32:
        msg = "SECRET_KEY is insecure or too short (minimum 32 characters required)"
        if is_production:
            errors.append(msg)
        else:
            warnings.append(msg)

    # Check debug mode in production
    if is_production and settings.debug:
        errors.append("DEBUG mode must be disabled in production (set DEBUG=false)")

    # Check DEV_BYPASS_AUTH
    dev_bypass = os.getenv("DEV_BYPASS_AUTH", "false").lower() == "true"
    if is_production and dev_bypass:
        errors.append("DEV_BYPASS_AUTH must be disabled in production")

    # Check SSL in production
    if is_production and not settings.ssl_enabled:
        warnings.append("SSL_ENABLED is false - ensure HTTPS is handled by reverse proxy")

    # Check cookie security in production with SSL
    if is_production and settings.ssl_enabled and not settings.cookie_secure:
        warnings.append("COOKIE_SECURE should be true when SSL is enabled")

    # Log warnings
    for warning in warnings:
        logger.warning(f"SECURITY WARNING: {warning}")

    # Raise errors in production
    if errors:
        for error in errors:
            logger.error(f"SECURITY ERROR: {error}")
        raise RuntimeError(f"Cannot start in production with insecure configuration: {'; '.join(errors)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.

    Startup:
    - Validate security settings
    - Initialize database connection
    - Create tables if needed (dev only)

    Shutdown:
    - Close database connections
    - Cleanup resources
    """
    # Startup
    logger.info("Starting GrantRadar API...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    logger.info(f"Version: {settings.app_version}")

    # Validate security settings before anything else
    validate_security_settings()

    # Initialize Sentry error tracking
    if init_sentry():
        logger.info("Sentry error tracking enabled")
    else:
        logger.info("Sentry error tracking disabled (no DSN configured)")

    # Initialize database (in production, use migrations instead)
    if settings.debug:
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    # Mark startup complete for health check probes
    from backend.api.health import mark_startup_complete

    mark_startup_complete()
    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down GrantRadar API...")
    await close_rate_limiter()
    logger.info("Rate limiter closed")
    await close_db()
    logger.info("Database connections closed")


# =============================================================================
# FastAPI Application
# =============================================================================

app = FastAPI(
    title="GrantRadar API",
    description="""
    Grant Intelligence Platform API

    GrantRadar helps researchers discover and match with relevant grant opportunities
    using AI-powered analysis and semantic similarity.

    ## Features

    - **Grant Discovery**: Browse and search grants from NIH, NSF, and Grants.gov
    - **Smart Matching**: AI-powered matching based on research profile
    - **Real-time Alerts**: WebSocket notifications for new matches
    - **Profile Management**: Maintain research profile for better matches

    ## Authentication

    Most endpoints require JWT authentication. Use the `/api/auth/login` endpoint
    to obtain access and refresh tokens.
    """,
    version=settings.app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# =============================================================================
# CORS Middleware
# =============================================================================

# Parse allowed origins
allowed_origins = [settings.frontend_url]
if settings.debug:
    allowed_origins.extend(
        [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:5175",
            "http://localhost:5176",
            "http://localhost:5177",
            "http://localhost:5178",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:5174",
            "http://127.0.0.1:5175",
            "http://127.0.0.1:5176",
            "http://127.0.0.1:5177",
            "http://127.0.0.1:5178",
        ]
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Rate Limiting Middleware
# =============================================================================

# Add rate limit middleware to include headers in responses
if settings.rate_limit_enabled:
    app.add_middleware(RateLimitMiddleware)
    logger.info("Rate limiting middleware enabled")
else:
    logger.info("Rate limiting middleware disabled")

# =============================================================================
# Exception Handlers
# =============================================================================

# Register rate limit exception handler for 429 responses
app.add_exception_handler(429, rate_limit_exception_handler)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions with consistent format."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")

    # Capture exception to Sentry with request context
    event_id = capture_exception(
        exc,
        extra={
            "request_url": str(request.url),
            "request_method": request.method,
            "request_path": request.url.path,
        },
    )

    # Don't expose internal errors in production
    if settings.debug:
        detail = str(exc)
    else:
        detail = f"Internal server error (ref: {event_id})" if event_id else "Internal server error"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": detail,
            "status_code": 500,
            "error_id": event_id,
        },
    )


# =============================================================================
# API Routers
# =============================================================================

# Include health router (public endpoints - no auth required)
app.include_router(health.router)

# Include all API routers
app.include_router(admin_analytics.router)
app.include_router(admin_seed.router)
app.include_router(aims.router)
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(api_keys.router)
app.include_router(audit.router)
app.include_router(auth.router)
app.include_router(budgets.router)
app.include_router(calendar.router)
app.include_router(chat.router)
app.include_router(checklists.router)
app.include_router(compare.router)
app.include_router(compliance.router)
app.include_router(compliance_engine.router)
app.include_router(components.router)
app.include_router(contact.router)
app.include_router(deadlines.router)
app.include_router(effort.router)
app.include_router(eligibility.router)
app.include_router(filters.router)
app.include_router(forecast.router)
app.include_router(funder_insights.router)
app.include_router(grants.router)
app.include_router(insights.router)
app.include_router(institution.router)
app.include_router(integrations.router)
app.include_router(intelligence.router)
app.include_router(kanban.router)
app.include_router(matches.router)
app.include_router(notifications.router)
app.include_router(permission_templates.router)
app.include_router(pipeline.router)
app.include_router(preferences.router)
app.include_router(probability.router)
app.include_router(profile.router)
app.include_router(reminders.router)
app.include_router(research.router)
app.include_router(reviews.router)
app.include_router(saved_searches.router)
app.include_router(sharing.router)
app.include_router(similar.router)
app.include_router(stats.router)
app.include_router(team.router)
app.include_router(team_collaboration.router)
app.include_router(templates.router)
app.include_router(verification.router)
app.include_router(winners.router)
app.include_router(workflow_analytics.router)
app.include_router(writing.router)


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get(
    "/",
    tags=["Root"],
    summary="API root",
    description="Welcome endpoint with API information.",
)
async def root() -> dict[str, Any]:
    """
    API root endpoint.

    Returns basic API information and links.
    """
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Grant Intelligence Platform API",
        "docs_url": "/docs" if settings.debug else None,
        "health_url": "/health",
        "readiness_url": "/health/ready",
    }


# =============================================================================
# Mount Socket.IO Application
# =============================================================================

# Create ASGI app combining FastAPI and Socket.IO
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)


# =============================================================================
# Application Factory
# =============================================================================


def create_app() -> socketio.ASGIApp:
    """
    Application factory function.

    Returns the combined FastAPI + Socket.IO ASGI application.
    """
    return socket_app


# For running with uvicorn directly
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:socket_app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
    )
