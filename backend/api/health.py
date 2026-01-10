"""
GrantRadar Health Check Endpoints
Comprehensive health monitoring for Kubernetes and infrastructure monitoring.
"""

import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

import redis.asyncio as aioredis
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from backend.core.config import settings
from backend.database import AsyncSessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# Health Status Models
# =============================================================================


class HealthStatus(str, Enum):
    """Health status values for components and overall system."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status for an individual component."""

    status: HealthStatus
    latency_ms: Optional[float] = None
    message: Optional[str] = None
    details: Optional[dict[str, Any]] = None


class CeleryComponentHealth(ComponentHealth):
    """Extended health status for Celery workers."""

    workers: Optional[int] = None


class HealthResponse(BaseModel):
    """Full health check response."""

    status: HealthStatus
    timestamp: str
    components: dict[str, Any]
    version: str


class LivenessResponse(BaseModel):
    """Simple liveness check response."""

    status: str


class StartupResponse(BaseModel):
    """Startup probe response."""

    status: str
    started_at: str


# =============================================================================
# Application State
# =============================================================================

# Track when the application started
_startup_time: Optional[datetime] = None


def mark_startup_complete() -> None:
    """Mark the application as started. Call this during app startup."""
    global _startup_time
    _startup_time = datetime.now(timezone.utc)


def get_startup_time() -> Optional[datetime]:
    """Get the application startup time."""
    return _startup_time


# =============================================================================
# Health Check Functions
# =============================================================================


async def check_database() -> ComponentHealth:
    """
    Check PostgreSQL database connectivity.

    Runs a simple query and measures latency.
    """
    start_time = time.perf_counter()
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            latency = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="Database connection successful",
            )
    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        logger.error(f"Database health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=f"Database connection failed: {str(e)}",
        )


async def check_redis() -> ComponentHealth:
    """
    Check Redis connectivity.

    Runs PING command and measures latency.
    """
    start_time = time.perf_counter()
    try:
        redis_client = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5.0,
            socket_connect_timeout=5.0,
        )
        try:
            await redis_client.ping()
            latency = (time.perf_counter() - start_time) * 1000
            return ComponentHealth(
                status=HealthStatus.HEALTHY,
                latency_ms=round(latency, 2),
                message="Redis connection successful",
            )
        finally:
            await redis_client.aclose()
    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        logger.error(f"Redis health check failed: {e}")
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            latency_ms=round(latency, 2),
            message=f"Redis connection failed: {str(e)}",
        )


async def check_celery() -> CeleryComponentHealth:
    """
    Check Celery worker availability.

    Uses the Celery app to inspect active workers.
    """
    start_time = time.perf_counter()
    try:
        from backend.celery_app import celery_app

        # Get active worker count using inspect
        inspector = celery_app.control.inspect(timeout=2.0)
        active_workers = inspector.active()

        latency = (time.perf_counter() - start_time) * 1000

        if active_workers is None:
            # No workers responded
            return CeleryComponentHealth(
                status=HealthStatus.DEGRADED,
                latency_ms=round(latency, 2),
                message="No Celery workers available",
                workers=0,
            )

        worker_count = len(active_workers)
        return CeleryComponentHealth(
            status=HealthStatus.HEALTHY if worker_count > 0 else HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=f"{worker_count} Celery worker(s) active",
            workers=worker_count,
        )
    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        logger.warning(f"Celery health check failed: {e}")
        # Celery being unavailable is degraded, not unhealthy
        # The API can still function without background workers
        return CeleryComponentHealth(
            status=HealthStatus.DEGRADED,
            latency_ms=round(latency, 2),
            message=f"Celery check failed: {str(e)}",
            workers=0,
        )


def determine_overall_status(components: dict[str, ComponentHealth]) -> HealthStatus:
    """
    Determine overall system health based on component statuses.

    - UNHEALTHY: If database is unhealthy (critical)
    - DEGRADED: If any component is degraded or non-critical components are unhealthy
    - HEALTHY: If all components are healthy
    """
    # Database is critical - if it's down, the system is unhealthy
    db_status = components.get("database")
    if db_status and db_status.status == HealthStatus.UNHEALTHY:
        return HealthStatus.UNHEALTHY

    # Check for any degraded or unhealthy components
    has_degraded = False
    for name, component in components.items():
        if component.status == HealthStatus.UNHEALTHY:
            # Non-database unhealthy components cause degraded state
            has_degraded = True
        elif component.status == HealthStatus.DEGRADED:
            has_degraded = True

    if has_degraded:
        return HealthStatus.DEGRADED

    return HealthStatus.HEALTHY


# =============================================================================
# Router Definition
# =============================================================================

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=LivenessResponse,
    summary="Basic liveness check",
    description="Simple health check that returns OK if the service is running.",
)
async def basic_health() -> LivenessResponse:
    """
    Basic liveness check.

    This endpoint always returns OK if the service is reachable.
    Use this for basic uptime monitoring.
    """
    return LivenessResponse(status="ok")


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Kubernetes liveness probe",
    description="Liveness probe for Kubernetes. Returns 200 if the process is alive.",
)
async def liveness_probe() -> LivenessResponse:
    """
    Kubernetes-style liveness probe.

    This endpoint indicates whether the application process is running.
    If this fails, Kubernetes should restart the container.
    """
    return LivenessResponse(status="ok")


@router.get(
    "/startup",
    response_model=StartupResponse,
    summary="Kubernetes startup probe",
    description="Startup probe for Kubernetes. Returns 200 once initialization is complete.",
)
async def startup_probe(response: Response) -> StartupResponse:
    """
    Kubernetes-style startup probe.

    This endpoint indicates whether the application has finished initialization.
    During startup, this returns 503 until the app is ready.
    """
    startup_time = get_startup_time()

    if startup_time is None:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return StartupResponse(
            status="starting",
            started_at="",
        )

    return StartupResponse(
        status="started",
        started_at=startup_time.isoformat(),
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness check",
    description="Comprehensive readiness check that verifies all dependencies.",
    responses={
        200: {"description": "All systems operational"},
        503: {"description": "One or more systems degraded or unhealthy"},
    },
)
async def readiness_check(response: Response) -> HealthResponse:
    """
    Comprehensive readiness check.

    Verifies connectivity to:
    - PostgreSQL database
    - Redis cache
    - Celery workers

    Returns component-level status with latency metrics.
    Use this for Kubernetes readiness probes and monitoring dashboards.
    """
    # Run all health checks concurrently
    import asyncio

    db_check, redis_check, celery_check = await asyncio.gather(
        check_database(),
        check_redis(),
        check_celery(),
    )

    components = {
        "database": db_check,
        "redis": redis_check,
        "celery": celery_check,
    }

    overall_status = determine_overall_status(components)

    # Set appropriate HTTP status code
    if overall_status == HealthStatus.UNHEALTHY:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif overall_status == HealthStatus.DEGRADED:
        # Return 200 for degraded - the service can still handle requests
        # but monitoring should be alerted
        response.status_code = status.HTTP_200_OK

    # Convert Pydantic models to dicts for the response
    components_dict = {
        "database": {
            "status": db_check.status.value,
            "latency_ms": db_check.latency_ms,
        },
        "redis": {
            "status": redis_check.status.value,
            "latency_ms": redis_check.latency_ms,
        },
        "celery": {
            "status": celery_check.status.value,
            "latency_ms": celery_check.latency_ms,
            "workers": celery_check.workers,
        },
    }

    return HealthResponse(
        status=overall_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        components=components_dict,
        version=settings.app_version,
    )
