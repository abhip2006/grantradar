"""
GrantRadar Orchestrator Agent Models
Pydantic models for pipeline state, agent health, and system metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PipelineStage(str, Enum):
    """Stages in the grant processing pipeline."""

    DISCOVERED = "discovered"
    VALIDATING = "validating"
    VALIDATED = "validated"
    MATCHING = "matching"
    MATCHED = "matched"
    ALERTING = "alerting"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentType(str, Enum):
    """Types of agents in the system."""

    DISCOVERY = "discovery"
    CURATION = "curation"
    MATCHING = "matching"
    DELIVERY = "delivery"
    ORCHESTRATOR = "orchestrator"


class HealthStatus(str, Enum):
    """Health status values for agents and services."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Service failing, blocking requests
    HALF_OPEN = "half_open"  # Testing recovery


class PipelineState(BaseModel):
    """
    Track a grant's progress through the processing pipeline.

    Monitors latency at each stage and total processing time.
    """

    grant_id: UUID = Field(..., description="Unique identifier for the grant")
    current_stage: PipelineStage = Field(..., description="Current stage in the pipeline")
    started_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When pipeline processing started",
    )
    latencies: dict[str, float] = Field(
        default_factory=dict,
        description="Latency in seconds for each completed stage",
    )
    stage_timestamps: dict[str, datetime] = Field(
        default_factory=dict,
        description="Timestamp when each stage was entered",
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if pipeline failed",
    )
    retry_count: int = Field(
        default=0,
        description="Number of retry attempts",
    )
    priority: str = Field(
        default="normal",
        description="Pipeline priority (critical, high, normal)",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional pipeline metadata",
    )

    def record_stage_transition(
        self,
        from_stage: PipelineStage,
        to_stage: PipelineStage,
    ) -> float:
        """
        Record a stage transition and calculate latency.

        Args:
            from_stage: Stage transitioning from.
            to_stage: Stage transitioning to.

        Returns:
            Latency in seconds for the completed stage.
        """
        now = datetime.utcnow()
        stage_start = self.stage_timestamps.get(from_stage.value)

        if stage_start:
            latency = (now - stage_start).total_seconds()
            self.latencies[from_stage.value] = latency
        else:
            latency = 0.0

        self.stage_timestamps[to_stage.value] = now
        self.current_stage = to_stage

        return latency

    def total_latency(self) -> float:
        """Calculate total pipeline latency in seconds."""
        return (datetime.utcnow() - self.started_at).total_seconds()

    def is_critical(self) -> bool:
        """Check if this is a critical priority pipeline."""
        return self.priority == "critical"


class AgentHealth(BaseModel):
    """
    Health status for a single agent in the system.

    Tracks heartbeat, error rates, and processing metrics.
    """

    name: AgentType = Field(..., description="Agent type/name")
    status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Current health status",
    )
    last_heartbeat: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last heartbeat timestamp",
    )
    error_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Error rate in the last window (0.0 to 1.0)",
    )
    avg_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average processing latency in milliseconds",
    )
    p95_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="95th percentile latency in milliseconds",
    )
    p99_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="99th percentile latency in milliseconds",
    )
    tasks_processed: int = Field(
        default=0,
        ge=0,
        description="Total tasks processed in the current window",
    )
    tasks_failed: int = Field(
        default=0,
        ge=0,
        description="Failed tasks in the current window",
    )
    active_workers: int = Field(
        default=0,
        ge=0,
        description="Number of active workers",
    )
    circuit_state: CircuitState = Field(
        default=CircuitState.CLOSED,
        description="Circuit breaker state for this agent",
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message",
    )
    downtime_started_at: Optional[datetime] = Field(
        default=None,
        description="When the agent went down (if unhealthy)",
    )

    def is_down(self) -> bool:
        """Check if agent is considered down."""
        return self.status == HealthStatus.UNHEALTHY

    def downtime_seconds(self) -> float:
        """Calculate how long agent has been down."""
        if self.downtime_started_at:
            return (datetime.utcnow() - self.downtime_started_at).total_seconds()
        return 0.0

    def needs_alert(self, threshold_seconds: float = 300) -> bool:
        """Check if agent downtime exceeds alert threshold (default 5 min)."""
        return self.downtime_seconds() > threshold_seconds


class EndpointHealth(BaseModel):
    """Health status for an external endpoint (Redis, Postgres, APIs)."""

    name: str = Field(..., description="Endpoint name")
    url: str = Field(..., description="Endpoint URL (sanitized)")
    status: HealthStatus = Field(
        default=HealthStatus.UNKNOWN,
        description="Current health status",
    )
    latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Latest latency in milliseconds",
    )
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last health check timestamp",
    )
    last_error: Optional[str] = Field(
        default=None,
        description="Last error message if unhealthy",
    )
    consecutive_failures: int = Field(
        default=0,
        ge=0,
        description="Number of consecutive failures",
    )


class QueueMetrics(BaseModel):
    """Metrics for a Celery task queue."""

    queue_name: str = Field(..., description="Queue name")
    depth: int = Field(default=0, ge=0, description="Current queue depth")
    oldest_task_age_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="Age of oldest task in queue",
    )
    processing_rate: float = Field(
        default=0.0,
        ge=0.0,
        description="Tasks processed per minute",
    )
    active_workers: int = Field(
        default=0,
        ge=0,
        description="Workers processing this queue",
    )


class SystemMetrics(BaseModel):
    """
    Aggregated system metrics for the orchestrator dashboard.

    Collects metrics across all agents, queues, and services.
    """

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When metrics were collected",
    )
    queue_depths: dict[str, int] = Field(
        default_factory=dict,
        description="Queue depths by queue name",
    )
    latencies: dict[str, float] = Field(
        default_factory=dict,
        description="Average latencies by stage in seconds",
    )
    success_rates: dict[str, float] = Field(
        default_factory=dict,
        description="Success rates by agent (0.0 to 1.0)",
    )
    agent_health: dict[str, AgentHealth] = Field(
        default_factory=dict,
        description="Health status by agent name",
    )
    endpoint_health: dict[str, EndpointHealth] = Field(
        default_factory=dict,
        description="Health status by endpoint name",
    )
    active_pipelines: int = Field(
        default=0,
        ge=0,
        description="Number of grants currently being processed",
    )
    pipeline_throughput: float = Field(
        default=0.0,
        ge=0.0,
        description="Pipelines completed per minute",
    )
    total_labs: int = Field(
        default=0,
        ge=0,
        description="Total number of lab profiles",
    )
    # LLM metrics
    llm_tokens_used: int = Field(
        default=0,
        ge=0,
        description="Total LLM tokens used in the current window",
    )
    llm_cost_usd: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated LLM cost in USD",
    )
    llm_avg_latency_ms: float = Field(
        default=0.0,
        ge=0.0,
        description="Average LLM call latency in milliseconds",
    )
    # Alert metrics
    alerts_sent: int = Field(
        default=0,
        ge=0,
        description="Total alerts sent in the current window",
    )
    alert_delivery_rate: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Successful alert delivery rate",
    )


class SLOStatus(BaseModel):
    """
    Service Level Objective status.

    Tracks SLO targets and current performance.
    """

    name: str = Field(..., description="SLO name")
    target: float = Field(..., description="Target value")
    current: float = Field(..., description="Current value")
    unit: str = Field(..., description="Unit (e.g., 'seconds', 'percent')")
    is_met: bool = Field(..., description="Whether SLO is currently met")
    window_hours: int = Field(
        default=24,
        description="Time window for SLO calculation",
    )

    @classmethod
    def create(
        cls,
        name: str,
        target: float,
        current: float,
        unit: str,
        higher_is_better: bool = False,
    ) -> "SLOStatus":
        """Create SLOStatus with automatic is_met calculation."""
        if higher_is_better:
            is_met = current >= target
        else:
            is_met = current <= target

        return cls(
            name=name,
            target=target,
            current=current,
            unit=unit,
            is_met=is_met,
        )


class CircuitBreakerState(BaseModel):
    """
    State of a circuit breaker for an external service.

    Used for graceful degradation and fallback routing.
    """

    service_name: str = Field(..., description="Name of the service")
    state: CircuitState = Field(
        default=CircuitState.CLOSED,
        description="Current circuit state",
    )
    failure_count: int = Field(
        default=0,
        ge=0,
        description="Current failure count",
    )
    failure_threshold: int = Field(
        default=5,
        gt=0,
        description="Failures before opening circuit",
    )
    last_failure_time: Optional[datetime] = Field(
        default=None,
        description="When last failure occurred",
    )
    recovery_timeout_seconds: int = Field(
        default=60,
        gt=0,
        description="Seconds before attempting recovery",
    )
    success_count_in_half_open: int = Field(
        default=0,
        ge=0,
        description="Successful calls in half-open state",
    )
    fallback_service: Optional[str] = Field(
        default=None,
        description="Name of fallback service when circuit is open",
    )

    def should_attempt_recovery(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.state != CircuitState.OPEN:
            return False
        if not self.last_failure_time:
            return True
        elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
        return elapsed >= self.recovery_timeout_seconds


class WorkerScalingDecision(BaseModel):
    """Decision for auto-scaling Celery workers."""

    queue_name: str = Field(..., description="Queue to scale")
    current_workers: int = Field(..., ge=0, description="Current worker count")
    target_workers: int = Field(..., ge=0, description="Target worker count")
    reason: str = Field(..., description="Reason for scaling decision")
    queue_depth: int = Field(..., ge=0, description="Current queue depth")
    threshold: int = Field(..., ge=0, description="Queue depth threshold")


class OnCallAlert(BaseModel):
    """Alert to send to on-call personnel."""

    severity: str = Field(..., description="Alert severity (critical, warning)")
    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")
    agent_name: Optional[str] = Field(
        default=None,
        description="Affected agent if applicable",
    )
    endpoint_name: Optional[str] = Field(
        default=None,
        description="Affected endpoint if applicable",
    )
    downtime_seconds: float = Field(
        default=0.0,
        ge=0.0,
        description="How long the issue has persisted",
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When alert was created",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context",
    )
