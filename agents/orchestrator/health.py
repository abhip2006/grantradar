"""
GrantRadar Orchestrator Health Checker
Health monitoring for agents, endpoints, and system components.
"""
import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Optional

import redis.asyncio as redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.core.config import settings

from .models import (
    AgentHealth,
    AgentType,
    EndpointHealth,
    HealthStatus,
)

logger = logging.getLogger(__name__)


class LatencyTracker:
    """
    Track latency measurements with percentile calculations.

    Maintains a sliding window of latency samples for statistical analysis.
    """

    def __init__(self, window_size: int = 1000):
        """
        Initialize latency tracker.

        Args:
            window_size: Maximum number of samples to retain.
        """
        self._samples: deque[float] = deque(maxlen=window_size)
        self._window_size = window_size

    def record(self, latency_ms: float) -> None:
        """Record a latency sample in milliseconds."""
        self._samples.append(latency_ms)

    def clear(self) -> None:
        """Clear all samples."""
        self._samples.clear()

    @property
    def count(self) -> int:
        """Number of samples recorded."""
        return len(self._samples)

    def average(self) -> float:
        """Calculate average latency."""
        if not self._samples:
            return 0.0
        return sum(self._samples) / len(self._samples)

    def percentile(self, p: float) -> float:
        """
        Calculate percentile latency.

        Args:
            p: Percentile to calculate (0-100).

        Returns:
            Latency at the given percentile.
        """
        if not self._samples:
            return 0.0

        sorted_samples = sorted(self._samples)
        index = int((p / 100) * len(sorted_samples))
        index = min(index, len(sorted_samples) - 1)
        return sorted_samples[index]

    def p50(self) -> float:
        """Get 50th percentile (median) latency."""
        return self.percentile(50)

    def p95(self) -> float:
        """Get 95th percentile latency."""
        return self.percentile(95)

    def p99(self) -> float:
        """Get 99th percentile latency."""
        return self.percentile(99)

    def stats(self) -> dict[str, float]:
        """Get all latency statistics."""
        return {
            "avg_ms": round(self.average(), 2),
            "p50_ms": round(self.p50(), 2),
            "p95_ms": round(self.p95(), 2),
            "p99_ms": round(self.p99(), 2),
            "sample_count": self.count,
        }


class HealthChecker:
    """
    Health checker for all system components.

    Monitors:
    - Redis connectivity and latency
    - PostgreSQL database health
    - External API availability (NIH, NSF, Grants.gov)
    - Agent heartbeats
    - Claude/OpenAI API response times
    """

    # Health check timeout in seconds
    CHECK_TIMEOUT = 5.0

    # Consecutive failures before marking unhealthy
    FAILURE_THRESHOLD = 3

    # Agent heartbeat timeout in seconds (consider down if no heartbeat)
    HEARTBEAT_TIMEOUT = 60.0

    def __init__(
        self,
        redis_url: Optional[str] = None,
        database_url: Optional[str] = None,
    ):
        """
        Initialize health checker.

        Args:
            redis_url: Redis connection URL. Defaults to settings.
            database_url: PostgreSQL connection URL. Defaults to settings.
        """
        self._redis_url = redis_url or settings.redis_url
        self._database_url = database_url or settings.async_database_url

        # Connection pools
        self._redis: Optional[redis.Redis] = None
        self._db_engine: Optional[Any] = None

        # Latency trackers by endpoint
        self._latency_trackers: dict[str, LatencyTracker] = {}

        # Endpoint health state
        self._endpoint_health: dict[str, EndpointHealth] = {}

        # Agent health state
        self._agent_health: dict[str, AgentHealth] = {}

        # Initialize latency trackers for known endpoints
        self._init_trackers()

    def _init_trackers(self) -> None:
        """Initialize latency trackers for known endpoints."""
        endpoints = [
            "redis",
            "postgres",
            "nih_api",
            "nsf_api",
            "grants_gov",
            "claude_api",
            "openai_api",
        ]
        for endpoint in endpoints:
            self._latency_trackers[endpoint] = LatencyTracker()

    async def connect(self) -> None:
        """Establish connections to Redis and database."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )

        if self._db_engine is None:
            self._db_engine = create_async_engine(
                self._database_url,
                pool_size=2,
                max_overflow=0,
            )

    async def disconnect(self) -> None:
        """Close connections."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

        if self._db_engine:
            await self._db_engine.dispose()
            self._db_engine = None

    async def _ensure_connected(self) -> None:
        """Ensure connections are established."""
        if self._redis is None or self._db_engine is None:
            await self.connect()

    def _get_tracker(self, name: str) -> LatencyTracker:
        """Get or create a latency tracker."""
        if name not in self._latency_trackers:
            self._latency_trackers[name] = LatencyTracker()
        return self._latency_trackers[name]

    def _update_endpoint_health(
        self,
        name: str,
        url: str,
        status: HealthStatus,
        latency_ms: float,
        error: Optional[str] = None,
    ) -> EndpointHealth:
        """Update endpoint health state."""
        current = self._endpoint_health.get(name)

        if current is None:
            consecutive_failures = 1 if status == HealthStatus.UNHEALTHY else 0
        else:
            if status == HealthStatus.UNHEALTHY:
                consecutive_failures = current.consecutive_failures + 1
            else:
                consecutive_failures = 0

        health = EndpointHealth(
            name=name,
            url=url,
            status=status,
            latency_ms=latency_ms,
            last_check=datetime.utcnow(),
            last_error=error,
            consecutive_failures=consecutive_failures,
        )

        self._endpoint_health[name] = health
        return health

    async def check_redis(self) -> EndpointHealth:
        """
        Check Redis health and latency.

        Returns:
            EndpointHealth with current status.
        """
        await self._ensure_connected()

        name = "redis"
        url = self._redis_url.split("@")[-1] if "@" in self._redis_url else "localhost"
        tracker = self._get_tracker(name)

        try:
            start = time.perf_counter()
            await asyncio.wait_for(
                self._redis.ping(),  # type: ignore
                timeout=self.CHECK_TIMEOUT,
            )
            latency_ms = (time.perf_counter() - start) * 1000

            tracker.record(latency_ms)

            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError:
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=self.CHECK_TIMEOUT * 1000,
                error="Connection timeout",
            )

        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                error=str(e),
            )

    async def check_postgres(self) -> EndpointHealth:
        """
        Check PostgreSQL database health.

        Returns:
            EndpointHealth with current status.
        """
        await self._ensure_connected()

        name = "postgres"
        # Sanitize URL for display
        url = "postgresql://***"
        if self._database_url:
            parts = self._database_url.split("@")
            if len(parts) > 1:
                url = f"postgresql://{parts[-1]}"

        tracker = self._get_tracker(name)

        try:
            start = time.perf_counter()

            async with self._db_engine.connect() as conn:  # type: ignore
                await asyncio.wait_for(
                    conn.execute(text("SELECT 1")),
                    timeout=self.CHECK_TIMEOUT,
                )

            latency_ms = (time.perf_counter() - start) * 1000
            tracker.record(latency_ms)

            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.HEALTHY,
                latency_ms=latency_ms,
            )

        except asyncio.TimeoutError:
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=self.CHECK_TIMEOUT * 1000,
                error="Query timeout",
            )

        except Exception as e:
            logger.error(f"Postgres health check failed: {e}")
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                error=str(e),
            )

    async def check_external_api(
        self,
        name: str,
        url: str,
        timeout: float = 10.0,
    ) -> EndpointHealth:
        """
        Check external API health via HTTP HEAD request.

        Args:
            name: API name for tracking.
            url: API endpoint URL.
            timeout: Request timeout in seconds.

        Returns:
            EndpointHealth with current status.
        """
        import httpx

        tracker = self._get_tracker(name)

        try:
            start = time.perf_counter()

            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.head(url)

            latency_ms = (time.perf_counter() - start) * 1000
            tracker.record(latency_ms)

            if response.status_code < 500:
                status = HealthStatus.HEALTHY
                error = None
            else:
                status = HealthStatus.DEGRADED
                error = f"HTTP {response.status_code}"

            return self._update_endpoint_health(
                name=name,
                url=url,
                status=status,
                latency_ms=latency_ms,
                error=error,
            )

        except httpx.TimeoutException:
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=timeout * 1000,
                error="Request timeout",
            )

        except Exception as e:
            logger.error(f"API health check failed for {name}: {e}")
            return self._update_endpoint_health(
                name=name,
                url=url,
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                error=str(e),
            )

    async def check_nih_api(self) -> EndpointHealth:
        """Check NIH Reporter API health."""
        return await self.check_external_api(
            name="nih_api",
            url=settings.nih_reporter_api_url,
        )

    async def check_nsf_api(self) -> EndpointHealth:
        """Check NSF API health."""
        return await self.check_external_api(
            name="nsf_api",
            url=settings.nsf_api_url,
        )

    async def check_grants_gov(self) -> EndpointHealth:
        """Check Grants.gov API health."""
        return await self.check_external_api(
            name="grants_gov",
            url=settings.grants_gov_rss_url,
        )

    def record_agent_heartbeat(
        self,
        agent_type: AgentType,
        metrics: Optional[dict[str, Any]] = None,
    ) -> AgentHealth:
        """
        Record a heartbeat from an agent.

        Args:
            agent_type: Type of agent reporting.
            metrics: Optional metrics from the agent.

        Returns:
            Updated AgentHealth.
        """
        now = datetime.utcnow()
        metrics = metrics or {}

        current = self._agent_health.get(agent_type.value)

        health = AgentHealth(
            name=agent_type,
            status=HealthStatus.HEALTHY,
            last_heartbeat=now,
            error_rate=metrics.get("error_rate", 0.0),
            avg_latency_ms=metrics.get("avg_latency_ms", 0.0),
            p95_latency_ms=metrics.get("p95_latency_ms", 0.0),
            p99_latency_ms=metrics.get("p99_latency_ms", 0.0),
            tasks_processed=metrics.get("tasks_processed", 0),
            tasks_failed=metrics.get("tasks_failed", 0),
            active_workers=metrics.get("active_workers", 0),
            downtime_started_at=None,  # Reset downtime on heartbeat
        )

        self._agent_health[agent_type.value] = health
        return health

    def check_agent_health(self, agent_type: AgentType) -> AgentHealth:
        """
        Check health of an agent based on last heartbeat.

        Args:
            agent_type: Type of agent to check.

        Returns:
            Current AgentHealth.
        """
        current = self._agent_health.get(agent_type.value)

        if current is None:
            # No heartbeat received yet
            return AgentHealth(
                name=agent_type,
                status=HealthStatus.UNKNOWN,
            )

        # Check if heartbeat is stale
        elapsed = (datetime.utcnow() - current.last_heartbeat).total_seconds()

        if elapsed > self.HEARTBEAT_TIMEOUT:
            # Agent is considered down
            if current.downtime_started_at is None:
                current.downtime_started_at = current.last_heartbeat
            current.status = HealthStatus.UNHEALTHY
        elif current.error_rate > 0.5:
            # High error rate indicates degraded status
            current.status = HealthStatus.DEGRADED
        else:
            current.status = HealthStatus.HEALTHY

        return current

    async def check_all_endpoints(self) -> dict[str, EndpointHealth]:
        """
        Run health checks on all endpoints in parallel.

        Returns:
            Dictionary of endpoint name to health status.
        """
        # Run checks concurrently
        results = await asyncio.gather(
            self.check_redis(),
            self.check_postgres(),
            self.check_nih_api(),
            self.check_nsf_api(),
            self.check_grants_gov(),
            return_exceptions=True,
        )

        names = ["redis", "postgres", "nih_api", "nsf_api", "grants_gov"]

        for name, result in zip(names, results):
            if isinstance(result, Exception):
                logger.error(f"Health check exception for {name}: {result}")
                self._update_endpoint_health(
                    name=name,
                    url="unknown",
                    status=HealthStatus.UNHEALTHY,
                    latency_ms=0,
                    error=str(result),
                )

        return self._endpoint_health.copy()

    def check_all_agents(self) -> dict[str, AgentHealth]:
        """
        Check health of all agents.

        Returns:
            Dictionary of agent name to health status.
        """
        for agent_type in AgentType:
            self.check_agent_health(agent_type)

        return {k: v for k, v in self._agent_health.items()}

    def get_latency_stats(self, endpoint: str) -> dict[str, float]:
        """
        Get latency statistics for an endpoint.

        Args:
            endpoint: Endpoint name.

        Returns:
            Dictionary with avg, p50, p95, p99 latencies.
        """
        tracker = self._latency_trackers.get(endpoint)
        if tracker is None:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
        return tracker.stats()

    def get_all_latency_stats(self) -> dict[str, dict[str, float]]:
        """Get latency stats for all endpoints."""
        return {
            name: tracker.stats()
            for name, tracker in self._latency_trackers.items()
        }

    async def get_full_health_report(self) -> dict[str, Any]:
        """
        Generate a complete health report.

        Returns:
            Full health status including endpoints, agents, and latencies.
        """
        endpoints = await self.check_all_endpoints()
        agents = self.check_all_agents()

        # Calculate overall system status
        unhealthy_endpoints = [
            e for e in endpoints.values()
            if e.status == HealthStatus.UNHEALTHY
        ]
        unhealthy_agents = [
            a for a in agents.values()
            if a.status == HealthStatus.UNHEALTHY
        ]

        if unhealthy_endpoints or unhealthy_agents:
            overall_status = HealthStatus.UNHEALTHY
        elif any(
            e.status == HealthStatus.DEGRADED for e in endpoints.values()
        ) or any(
            a.status == HealthStatus.DEGRADED for a in agents.values()
        ):
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return {
            "overall_status": overall_status.value,
            "timestamp": datetime.utcnow().isoformat(),
            "endpoints": {
                name: health.model_dump()
                for name, health in endpoints.items()
            },
            "agents": {
                name: health.model_dump()
                for name, health in agents.items()
            },
            "latencies": self.get_all_latency_stats(),
            "issues": {
                "unhealthy_endpoints": [e.name for e in unhealthy_endpoints],
                "unhealthy_agents": [a.name.value for a in unhealthy_agents],
            },
        }


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


async def get_health_checker() -> HealthChecker:
    """Get the global health checker instance."""
    global _health_checker

    if _health_checker is None:
        _health_checker = HealthChecker()
        await _health_checker.connect()

    return _health_checker


async def close_health_checker() -> None:
    """Close the global health checker."""
    global _health_checker

    if _health_checker is not None:
        await _health_checker.disconnect()
        _health_checker = None
