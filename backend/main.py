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

from backend.api import alerts, analytics, auth, calendar, chat, compare, contact, deadlines, eligibility, forecast, funder_insights, grants, integrations, matches, pipeline, preferences, profile, reminders, research, saved_searches, similar, stats, templates
from backend.core.config import settings
from backend.database import check_db_connection, close_db, init_db

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
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=[settings.frontend_url] if not settings.debug else "*",
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle application startup and shutdown events.

    Startup:
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

    # Initialize database (in production, use migrations instead)
    if settings.debug:
        try:
            await init_db()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")

    yield

    # Shutdown
    logger.info("Shutting down GrantRadar API...")
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
    version="1.0.0",
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
    allowed_origins.extend([
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Exception Handlers
# =============================================================================


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

    # Don't expose internal errors in production
    detail = str(exc) if settings.debug else "Internal server error"

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": detail,
            "status_code": 500,
        },
    )


# =============================================================================
# Health Check Endpoints
# =============================================================================


@app.get(
    "/health",
    tags=["Health"],
    summary="Health check",
    description="Basic health check endpoint.",
)
async def health_check() -> dict[str, Any]:
    """
    Basic health check.

    Returns application status and version.
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": "1.0.0",
        "environment": settings.environment,
    }


@app.get(
    "/health/ready",
    tags=["Health"],
    summary="Readiness check",
    description="Check if the application is ready to serve requests.",
)
async def readiness_check() -> dict[str, Any]:
    """
    Readiness check including database connectivity.

    Returns detailed status of all dependencies.
    """
    db_status = await check_db_connection()

    is_ready = db_status.get("status") == "healthy"

    return {
        "status": "ready" if is_ready else "not_ready",
        "checks": {
            "database": db_status,
        },
    }


# =============================================================================
# API Routers
# =============================================================================

# Include all API routers
app.include_router(alerts.router)
app.include_router(analytics.router)
app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(chat.router)
app.include_router(compare.router)
app.include_router(contact.router)
app.include_router(deadlines.router)
app.include_router(eligibility.router)
app.include_router(forecast.router)
app.include_router(funder_insights.router)
app.include_router(grants.router)
app.include_router(integrations.router)
app.include_router(matches.router)
app.include_router(pipeline.router)
app.include_router(preferences.router)
app.include_router(profile.router)
app.include_router(reminders.router)
app.include_router(research.router)
app.include_router(saved_searches.router)
app.include_router(similar.router)
app.include_router(stats.router)
app.include_router(templates.router)


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
        "version": "1.0.0",
        "description": "Grant Intelligence Platform API",
        "docs_url": "/docs" if settings.debug else None,
        "health_url": "/health",
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
