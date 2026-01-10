"""
GrantRadar Orchestrator Metrics Collector
Collects and stores metrics in Redis for dashboard visualization.
"""

import json
import logging
import time
from datetime import datetime
from typing import Any, Optional

import redis.asyncio as redis

from backend.core.config import settings

from .models import (
    AgentHealth,
    AgentType,
    EndpointHealth,
    QueueMetrics,
    SLOStatus,
    SystemMetrics,
)

logger = logging.getLogger(__name__)


# Redis key prefixes for metrics storage
class MetricKeys:
    """Redis key patterns for metrics storage."""

    # Time-series metrics (sorted sets with timestamp scores)
    PIPELINE_LATENCIES = "metrics:pipeline:latencies"  # Per-stage latencies
    AGENT_LATENCIES = "metrics:agent:{agent}:latencies"  # Per-agent latencies
    LLM_LATENCIES = "metrics:llm:latencies"  # LLM call latencies
    LLM_TOKENS = "metrics:llm:tokens"  # Token usage over time

    # Counters (with TTL for automatic expiry)
    PIPELINE_SUCCESS = "metrics:pipeline:success:{window}"
    PIPELINE_FAILURE = "metrics:pipeline:failure:{window}"
    AGENT_SUCCESS = "metrics:agent:{agent}:success:{window}"
    AGENT_FAILURE = "metrics:agent:{agent}:failure:{window}"
    ALERTS_SENT = "metrics:alerts:sent:{window}"
    ALERTS_DELIVERED = "metrics:alerts:delivered:{window}"

    # Current state (hashes)
    QUEUE_DEPTHS = "metrics:queues:depths"
    AGENT_HEALTH = "metrics:agents:health"
    ENDPOINT_HEALTH = "metrics:endpoints:health"
    SYSTEM_METRICS = "metrics:system:current"

    # Historical snapshots (for dashboard)
    METRICS_HISTORY = "metrics:history:{date}"

    # LLM cost tracking
    LLM_COST = "metrics:llm:cost:{date}"


class MetricsCollector:
    """
    Collects and stores metrics for the GrantRadar system.

    Features:
    - Time-series storage with automatic cleanup
    - Counter-based success/failure tracking
    - SLO calculation and monitoring
    - Dashboard-ready metric aggregation
    """

    # Metric retention periods
    LATENCY_RETENTION_HOURS = 24
    COUNTER_WINDOW_MINUTES = 60
    HISTORY_RETENTION_DAYS = 30

    # SLO targets
    SLO_PIPELINE_LATENCY_SECONDS = 120  # 2 minutes end-to-end
    SLO_SUCCESS_RATE_PERCENT = 99.0
    SLO_ALERT_DELIVERY_RATE_PERCENT = 99.5
    SLO_LLM_LATENCY_MS = 10000  # 10 seconds

    def __init__(self, redis_url: Optional[str] = None):
        """
        Initialize metrics collector.

        Args:
            redis_url: Redis connection URL. Defaults to settings.redis_url.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self._redis.ping()
            logger.info("Metrics collector connected to Redis")

    async def disconnect(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.aclose()
            self._redis = None

    async def _ensure_connected(self) -> redis.Redis:
        """Ensure Redis connection is established."""
        if self._redis is None:
            await self.connect()
        return self._redis  # type: ignore

    def _current_window(self) -> str:
        """Get current time window key (hourly)."""
        now = datetime.utcnow()
        return now.strftime("%Y%m%d%H")

    def _current_date(self) -> str:
        """Get current date key."""
        return datetime.utcnow().strftime("%Y%m%d")

    # =========================================================================
    # Latency Recording
    # =========================================================================

    async def record_pipeline_latency(
        self,
        stage: str,
        latency_seconds: float,
        grant_id: Optional[str] = None,
    ) -> None:
        """
        Record pipeline stage latency.

        Args:
            stage: Pipeline stage name.
            latency_seconds: Latency in seconds.
            grant_id: Optional grant ID for correlation.
        """
        r = await self._ensure_connected()
        now = time.time()

        key = f"{MetricKeys.PIPELINE_LATENCIES}:{stage}"
        value = json.dumps(
            {
                "latency": latency_seconds,
                "grant_id": grant_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        # Add to sorted set with timestamp as score
        await r.zadd(key, {value: now})

        # Cleanup old entries
        cutoff = now - (self.LATENCY_RETENTION_HOURS * 3600)
        await r.zremrangebyscore(key, 0, cutoff)

    async def record_agent_latency(
        self,
        agent: AgentType,
        latency_ms: float,
        task_id: Optional[str] = None,
    ) -> None:
        """
        Record agent processing latency.

        Args:
            agent: Agent type.
            latency_ms: Latency in milliseconds.
            task_id: Optional task ID for correlation.
        """
        r = await self._ensure_connected()
        now = time.time()

        key = MetricKeys.AGENT_LATENCIES.format(agent=agent.value)
        value = json.dumps(
            {
                "latency_ms": latency_ms,
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

        await r.zadd(key, {value: now})

        # Cleanup old entries
        cutoff = now - (self.LATENCY_RETENTION_HOURS * 3600)
        await r.zremrangebyscore(key, 0, cutoff)

    async def record_llm_call(
        self,
        provider: str,
        model: str,
        latency_ms: float,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        """
        Record an LLM API call.

        Args:
            provider: LLM provider (claude, openai).
            model: Model name.
            latency_ms: Call latency in milliseconds.
            input_tokens: Number of input tokens.
            output_tokens: Number of output tokens.
            cost_usd: Estimated cost in USD.
        """
        r = await self._ensure_connected()
        now = time.time()

        # Record latency
        latency_value = json.dumps(
            {
                "provider": provider,
                "model": model,
                "latency_ms": latency_ms,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await r.zadd(MetricKeys.LLM_LATENCIES, {latency_value: now})

        # Record tokens
        token_value = json.dumps(
            {
                "provider": provider,
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        await r.zadd(MetricKeys.LLM_TOKENS, {token_value: now})

        # Update daily cost
        cost_key = MetricKeys.LLM_COST.format(date=self._current_date())
        await r.incrbyfloat(cost_key, cost_usd)
        await r.expire(cost_key, 86400 * self.HISTORY_RETENTION_DAYS)

        # Cleanup old entries
        cutoff = now - (self.LATENCY_RETENTION_HOURS * 3600)
        await r.zremrangebyscore(MetricKeys.LLM_LATENCIES, 0, cutoff)
        await r.zremrangebyscore(MetricKeys.LLM_TOKENS, 0, cutoff)

    # =========================================================================
    # Success/Failure Counters
    # =========================================================================

    async def record_pipeline_success(self, grant_id: str) -> None:
        """Record a successful pipeline completion."""
        r = await self._ensure_connected()
        key = MetricKeys.PIPELINE_SUCCESS.format(window=self._current_window())
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    async def record_pipeline_failure(self, grant_id: str, error: str) -> None:
        """Record a pipeline failure."""
        r = await self._ensure_connected()
        key = MetricKeys.PIPELINE_FAILURE.format(window=self._current_window())
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    async def record_agent_success(self, agent: AgentType) -> None:
        """Record a successful agent task."""
        r = await self._ensure_connected()
        key = MetricKeys.AGENT_SUCCESS.format(
            agent=agent.value,
            window=self._current_window(),
        )
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    async def record_agent_failure(self, agent: AgentType, error: str) -> None:
        """Record an agent task failure."""
        r = await self._ensure_connected()
        key = MetricKeys.AGENT_FAILURE.format(
            agent=agent.value,
            window=self._current_window(),
        )
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    async def record_alert_sent(self, channel: str) -> None:
        """Record an alert sent."""
        r = await self._ensure_connected()
        key = MetricKeys.ALERTS_SENT.format(window=self._current_window())
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    async def record_alert_delivered(self, channel: str) -> None:
        """Record a successful alert delivery."""
        r = await self._ensure_connected()
        key = MetricKeys.ALERTS_DELIVERED.format(window=self._current_window())
        await r.incr(key)
        await r.expire(key, self.COUNTER_WINDOW_MINUTES * 60 * 2)

    # =========================================================================
    # Queue Metrics
    # =========================================================================

    async def update_queue_depths(
        self,
        queue_depths: dict[str, int],
    ) -> None:
        """
        Update current queue depths.

        Args:
            queue_depths: Dictionary of queue name to depth.
        """
        r = await self._ensure_connected()
        if queue_depths:
            await r.hset(
                MetricKeys.QUEUE_DEPTHS,
                mapping={k: str(v) for k, v in queue_depths.items()},
            )

    async def get_queue_depths(self) -> dict[str, int]:
        """Get current queue depths."""
        r = await self._ensure_connected()
        depths = await r.hgetall(MetricKeys.QUEUE_DEPTHS)
        return {k: int(v) for k, v in depths.items()}

    async def get_queue_metrics(self, queue_name: str) -> QueueMetrics:
        """Get metrics for a specific queue."""
        depths = await self.get_queue_depths()
        return QueueMetrics(
            queue_name=queue_name,
            depth=depths.get(queue_name, 0),
        )

    # =========================================================================
    # Health State Storage
    # =========================================================================

    async def store_agent_health(self, health: AgentHealth) -> None:
        """Store agent health status."""
        r = await self._ensure_connected()
        await r.hset(
            MetricKeys.AGENT_HEALTH,
            health.name.value,
            health.model_dump_json(),
        )

    async def store_endpoint_health(self, health: EndpointHealth) -> None:
        """Store endpoint health status."""
        r = await self._ensure_connected()
        await r.hset(
            MetricKeys.ENDPOINT_HEALTH,
            health.name,
            health.model_dump_json(),
        )

    async def get_stored_agent_health(self) -> dict[str, AgentHealth]:
        """Get all stored agent health."""
        r = await self._ensure_connected()
        data = await r.hgetall(MetricKeys.AGENT_HEALTH)
        return {k: AgentHealth.model_validate_json(v) for k, v in data.items()}

    async def get_stored_endpoint_health(self) -> dict[str, EndpointHealth]:
        """Get all stored endpoint health."""
        r = await self._ensure_connected()
        data = await r.hgetall(MetricKeys.ENDPOINT_HEALTH)
        return {k: EndpointHealth.model_validate_json(v) for k, v in data.items()}

    # =========================================================================
    # Metric Aggregation
    # =========================================================================

    async def _get_latency_percentile(
        self,
        key: str,
        percentile: float,
    ) -> float:
        """Calculate latency percentile from sorted set."""
        r = await self._ensure_connected()

        # Get all entries from last hour
        now = time.time()
        cutoff = now - 3600
        entries = await r.zrangebyscore(key, cutoff, now)

        if not entries:
            return 0.0

        latencies = []
        for entry in entries:
            try:
                data = json.loads(entry)
                latency = data.get("latency", data.get("latency_ms", 0))
                latencies.append(latency)
            except (json.JSONDecodeError, KeyError):
                continue

        if not latencies:
            return 0.0

        latencies.sort()
        index = int((percentile / 100) * len(latencies))
        index = min(index, len(latencies) - 1)
        return latencies[index]

    async def _get_success_rate(
        self,
        success_key_pattern: str,
        failure_key_pattern: str,
    ) -> float:
        """Calculate success rate from counters."""
        r = await self._ensure_connected()
        window = self._current_window()

        success_key = success_key_pattern.format(window=window)
        failure_key = failure_key_pattern.format(window=window)

        success = int(await r.get(success_key) or 0)
        failure = int(await r.get(failure_key) or 0)

        total = success + failure
        if total == 0:
            return 1.0  # Default to 100% if no data

        return success / total

    async def get_pipeline_success_rate(self) -> float:
        """Get pipeline success rate for current window."""
        return await self._get_success_rate(
            MetricKeys.PIPELINE_SUCCESS,
            MetricKeys.PIPELINE_FAILURE,
        )

    async def get_agent_success_rate(self, agent: AgentType) -> float:
        """Get agent success rate for current window."""
        return await self._get_success_rate(
            MetricKeys.AGENT_SUCCESS.replace("{agent}", agent.value),
            MetricKeys.AGENT_FAILURE.replace("{agent}", agent.value),
        )

    async def get_alert_delivery_rate(self) -> float:
        """Get alert delivery rate for current window."""
        return await self._get_success_rate(
            MetricKeys.ALERTS_DELIVERED,
            MetricKeys.ALERTS_SENT,
        )

    async def get_llm_metrics(self) -> dict[str, Any]:
        """Get aggregated LLM metrics."""
        r = await self._ensure_connected()

        # Get today's cost
        cost_key = MetricKeys.LLM_COST.format(date=self._current_date())
        cost = float(await r.get(cost_key) or 0)

        # Get latency p95
        p95_latency = await self._get_latency_percentile(
            MetricKeys.LLM_LATENCIES,
            95,
        )

        # Count tokens from last hour
        now = time.time()
        cutoff = now - 3600
        token_entries = await r.zrangebyscore(
            MetricKeys.LLM_TOKENS,
            cutoff,
            now,
        )

        total_tokens = 0
        for entry in token_entries:
            try:
                data = json.loads(entry)
                total_tokens += data.get("input_tokens", 0)
                total_tokens += data.get("output_tokens", 0)
            except (json.JSONDecodeError, KeyError):
                continue

        return {
            "tokens_last_hour": total_tokens,
            "cost_today_usd": round(cost, 4),
            "p95_latency_ms": round(p95_latency, 2),
        }

    # =========================================================================
    # SLO Calculation
    # =========================================================================

    async def calculate_slos(self) -> list[SLOStatus]:
        """
        Calculate current SLO status.

        Returns:
            List of SLO statuses with current values.
        """
        slos = []

        # Pipeline latency SLO
        p95_pipeline = await self._get_latency_percentile(
            f"{MetricKeys.PIPELINE_LATENCIES}:completed",
            95,
        )
        slos.append(
            SLOStatus.create(
                name="Pipeline Latency (p95)",
                target=self.SLO_PIPELINE_LATENCY_SECONDS,
                current=p95_pipeline,
                unit="seconds",
                higher_is_better=False,
            )
        )

        # Success rate SLO
        success_rate = await self.get_pipeline_success_rate()
        slos.append(
            SLOStatus.create(
                name="Pipeline Success Rate",
                target=self.SLO_SUCCESS_RATE_PERCENT,
                current=success_rate * 100,
                unit="percent",
                higher_is_better=True,
            )
        )

        # Alert delivery SLO
        delivery_rate = await self.get_alert_delivery_rate()
        slos.append(
            SLOStatus.create(
                name="Alert Delivery Rate",
                target=self.SLO_ALERT_DELIVERY_RATE_PERCENT,
                current=delivery_rate * 100,
                unit="percent",
                higher_is_better=True,
            )
        )

        # LLM latency SLO
        llm_metrics = await self.get_llm_metrics()
        slos.append(
            SLOStatus.create(
                name="LLM Latency (p95)",
                target=self.SLO_LLM_LATENCY_MS,
                current=llm_metrics["p95_latency_ms"],
                unit="milliseconds",
                higher_is_better=False,
            )
        )

        return slos

    # =========================================================================
    # System Metrics Aggregation
    # =========================================================================

    async def collect_system_metrics(self) -> SystemMetrics:
        """
        Collect and aggregate all system metrics.

        Returns:
            SystemMetrics with current system state.
        """
        r = await self._ensure_connected()

        # Collect queue depths
        queue_depths = await self.get_queue_depths()

        # Collect agent health
        agent_health = await self.get_stored_agent_health()

        # Collect endpoint health
        endpoint_health = await self.get_stored_endpoint_health()

        # Calculate success rates
        success_rates = {}
        for agent_type in AgentType:
            rate = await self.get_agent_success_rate(agent_type)
            success_rates[agent_type.value] = rate

        # Get LLM metrics
        llm_metrics = await self.get_llm_metrics()

        # Get alert metrics
        window = self._current_window()
        alerts_sent = int(await r.get(MetricKeys.ALERTS_SENT.format(window=window)) or 0)
        alert_delivery_rate = await self.get_alert_delivery_rate()

        # Calculate average latencies per stage
        latencies = {}
        for stage in ["validated", "matched", "completed"]:
            key = f"{MetricKeys.PIPELINE_LATENCIES}:{stage}"
            avg = await self._get_latency_percentile(key, 50)
            latencies[stage] = avg

        return SystemMetrics(
            timestamp=datetime.utcnow(),
            queue_depths=queue_depths,
            latencies=latencies,
            success_rates=success_rates,
            agent_health=agent_health,
            endpoint_health=endpoint_health,
            llm_tokens_used=llm_metrics["tokens_last_hour"],
            llm_cost_usd=llm_metrics["cost_today_usd"],
            llm_avg_latency_ms=llm_metrics["p95_latency_ms"],
            alerts_sent=alerts_sent,
            alert_delivery_rate=alert_delivery_rate,
        )

    async def store_metrics_snapshot(
        self,
        metrics: SystemMetrics,
    ) -> None:
        """
        Store a metrics snapshot for historical tracking.

        Args:
            metrics: System metrics to store.
        """
        r = await self._ensure_connected()

        # Store current metrics
        await r.set(
            MetricKeys.SYSTEM_METRICS,
            metrics.model_dump_json(),
        )

        # Append to daily history
        history_key = MetricKeys.METRICS_HISTORY.format(
            date=self._current_date(),
        )
        await r.rpush(history_key, metrics.model_dump_json())
        await r.expire(history_key, 86400 * self.HISTORY_RETENTION_DAYS)

    async def get_current_metrics(self) -> Optional[SystemMetrics]:
        """Get the most recently stored metrics snapshot."""
        r = await self._ensure_connected()
        data = await r.get(MetricKeys.SYSTEM_METRICS)
        if data:
            return SystemMetrics.model_validate_json(data)
        return None

    async def get_metrics_history(
        self,
        date: Optional[str] = None,
        limit: int = 100,
    ) -> list[SystemMetrics]:
        """
        Get historical metrics for a date.

        Args:
            date: Date in YYYYMMDD format. Defaults to today.
            limit: Maximum number of entries to return.

        Returns:
            List of historical metrics snapshots.
        """
        r = await self._ensure_connected()
        date = date or self._current_date()

        history_key = MetricKeys.METRICS_HISTORY.format(date=date)
        entries = await r.lrange(history_key, -limit, -1)

        return [SystemMetrics.model_validate_json(entry) for entry in entries]


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


async def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_collector

    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
        await _metrics_collector.connect()

    return _metrics_collector


async def close_metrics_collector() -> None:
    """Close the global metrics collector."""
    global _metrics_collector

    if _metrics_collector is not None:
        await _metrics_collector.disconnect()
        _metrics_collector = None
