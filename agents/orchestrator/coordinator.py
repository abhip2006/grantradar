"""
GrantRadar Orchestrator Agent - Coordinator
Coordinates all agents and monitors system health.

The Orchestrator is the central nervous system of GrantRadar, responsible for:
- Event pipeline coordination (discovery -> validation -> matching -> delivery)
- Priority queue management with dynamic routing
- Health monitoring and alerting
- Circuit breaker management for graceful degradation
- Auto-scaling decisions for Celery workers
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Optional
from uuid import UUID

import redis.asyncio as redis

from backend.celery_app import (
    CircuitBreaker,
    celery_app,
    grants_gov_circuit,
    nih_circuit,
    nsf_circuit,
)
from backend.core.config import settings
from backend.events import EventBus, get_event_bus

from .health import HealthChecker, get_health_checker
from .metrics import MetricsCollector, get_metrics_collector
from .models import (
    AgentHealth,
    AgentType,
    CircuitBreakerState,
    CircuitState,
    OnCallAlert,
    PipelineStage,
    PipelineState,
    WorkerScalingDecision,
)

logger = logging.getLogger(__name__)


class LLMCircuitBreaker:
    """
    Circuit breaker for LLM API calls with provider fallback.

    Routes to fallback provider when primary circuit is open.
    """

    def __init__(
        self,
        primary_provider: str = "claude",
        fallback_provider: str = "openai",
        latency_threshold_ms: float = 10000,  # 10 seconds
        failure_threshold: int = 3,
        recovery_timeout: int = 60,
    ):
        """
        Initialize LLM circuit breaker.

        Args:
            primary_provider: Primary LLM provider.
            fallback_provider: Fallback provider when primary is slow/down.
            latency_threshold_ms: Latency threshold to trigger fallback.
            failure_threshold: Failures before opening circuit.
            recovery_timeout: Seconds before testing primary again.
        """
        self.primary_provider = primary_provider
        self.fallback_provider = fallback_provider
        self.latency_threshold_ms = latency_threshold_ms

        self._circuit = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )

        self._recent_latencies: list[float] = []
        self._max_latency_samples = 10

    def record_latency(self, latency_ms: float) -> None:
        """Record LLM call latency for monitoring."""
        self._recent_latencies.append(latency_ms)
        if len(self._recent_latencies) > self._max_latency_samples:
            self._recent_latencies.pop(0)

        # If recent calls are consistently slow, trigger fallback
        if len(self._recent_latencies) >= 3:
            avg_latency = sum(self._recent_latencies) / len(self._recent_latencies)
            if avg_latency > self.latency_threshold_ms:
                self._circuit.record_failure()
                logger.warning(
                    f"LLM latency ({avg_latency:.0f}ms) exceeds threshold, "
                    f"triggering fallback to {self.fallback_provider}"
                )

    def record_success(self) -> None:
        """Record successful call."""
        self._circuit.record_success()

    def record_failure(self) -> None:
        """Record failed call."""
        self._circuit.record_failure()

    def get_provider(self) -> str:
        """Get the provider to use based on circuit state."""
        if self._circuit.can_execute():
            return self.primary_provider
        return self.fallback_provider

    @property
    def state(self) -> CircuitBreakerState:
        """Get current circuit breaker state."""
        state_map = {
            CircuitBreaker.CLOSED: CircuitState.CLOSED,
            CircuitBreaker.OPEN: CircuitState.OPEN,
            CircuitBreaker.HALF_OPEN: CircuitState.HALF_OPEN,
        }
        return CircuitBreakerState(
            service_name=f"llm_{self.primary_provider}",
            state=state_map.get(self._circuit.state, CircuitState.CLOSED),
            failure_count=self._circuit._failure_count,
            failure_threshold=self._circuit.failure_threshold,
            last_failure_time=(
                datetime.fromtimestamp(self._circuit._last_failure_time) if self._circuit._last_failure_time else None
            ),
            recovery_timeout_seconds=self._circuit.recovery_timeout,
            fallback_service=f"llm_{self.fallback_provider}",
        )


class PipelineTracker:
    """
    Tracks grants through the processing pipeline.

    Monitors latency at each stage and detects stalled pipelines.
    """

    # Target latencies in seconds
    VALIDATION_TARGET = 30
    MATCHING_TARGET = 60
    ALERTING_TARGET = 30
    TOTAL_TARGET = 120  # 2 minutes end-to-end

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize pipeline tracker.

        Args:
            redis_client: Redis connection for state storage.
        """
        self._redis = redis_client
        self._pipelines: dict[str, PipelineState] = {}

    def _pipeline_key(self, grant_id: UUID) -> str:
        """Get Redis key for pipeline state."""
        return f"pipeline:state:{grant_id}"

    async def start_pipeline(
        self,
        grant_id: UUID,
        priority: str = "normal",
        metadata: Optional[dict[str, Any]] = None,
    ) -> PipelineState:
        """
        Start tracking a new pipeline.

        Args:
            grant_id: Grant being processed.
            priority: Pipeline priority (critical, high, normal).
            metadata: Additional context.

        Returns:
            New PipelineState.
        """
        state = PipelineState(
            grant_id=grant_id,
            current_stage=PipelineStage.DISCOVERED,
            priority=priority,
            metadata=metadata or {},
        )
        state.stage_timestamps[PipelineStage.DISCOVERED.value] = datetime.utcnow()

        # Store in Redis
        await self._redis.setex(
            self._pipeline_key(grant_id),
            3600,  # 1 hour TTL
            state.model_dump_json(),
        )

        self._pipelines[str(grant_id)] = state
        logger.info(f"Pipeline started for grant {grant_id} with priority {priority}")

        return state

    async def transition_stage(
        self,
        grant_id: UUID,
        from_stage: PipelineStage,
        to_stage: PipelineStage,
    ) -> tuple[PipelineState, float]:
        """
        Record a stage transition.

        Args:
            grant_id: Grant ID.
            from_stage: Stage transitioning from.
            to_stage: Stage transitioning to.

        Returns:
            Tuple of (updated state, latency in seconds).
        """
        state = self._pipelines.get(str(grant_id))

        if state is None:
            # Try to load from Redis
            data = await self._redis.get(self._pipeline_key(grant_id))
            if data:
                state = PipelineState.model_validate_json(data)
                self._pipelines[str(grant_id)] = state
            else:
                # Create new state if not found
                state = await self.start_pipeline(grant_id)

        latency = state.record_stage_transition(from_stage, to_stage)

        # Update Redis
        await self._redis.setex(
            self._pipeline_key(grant_id),
            3600,
            state.model_dump_json(),
        )

        logger.info(f"Pipeline {grant_id}: {from_stage.value} -> {to_stage.value} (latency: {latency:.2f}s)")

        return state, latency

    async def complete_pipeline(
        self,
        grant_id: UUID,
    ) -> tuple[PipelineState, float]:
        """
        Mark pipeline as completed.

        Returns:
            Tuple of (final state, total latency).
        """
        state, latency = await self.transition_stage(
            grant_id,
            PipelineStage.ALERTING,
            PipelineStage.COMPLETED,
        )

        total_latency = state.total_latency()

        # Log if exceeded target
        if total_latency > self.TOTAL_TARGET:
            logger.warning(f"Pipeline {grant_id} exceeded target latency: {total_latency:.2f}s > {self.TOTAL_TARGET}s")

        # Cleanup
        del self._pipelines[str(grant_id)]
        await self._redis.delete(self._pipeline_key(grant_id))

        return state, total_latency

    async def fail_pipeline(
        self,
        grant_id: UUID,
        error: str,
    ) -> PipelineState:
        """Mark pipeline as failed."""
        state = self._pipelines.get(str(grant_id))

        if state is None:
            data = await self._redis.get(self._pipeline_key(grant_id))
            if data:
                state = PipelineState.model_validate_json(data)

        if state:
            state.current_stage = PipelineStage.FAILED
            state.error_message = error

            await self._redis.setex(
                self._pipeline_key(grant_id),
                86400,  # Keep failed pipelines for 24h
                state.model_dump_json(),
            )

            logger.error(f"Pipeline {grant_id} failed: {error}")

        return state  # type: ignore

    async def get_active_pipelines(self) -> list[PipelineState]:
        """Get all active (non-completed) pipelines."""
        return list(self._pipelines.values())

    async def get_stalled_pipelines(
        self,
        stall_threshold_seconds: float = 300,
    ) -> list[PipelineState]:
        """Get pipelines that appear stalled."""
        stalled = []
        now = datetime.utcnow()

        for state in self._pipelines.values():
            current_stage_time = state.stage_timestamps.get(state.current_stage.value)
            if current_stage_time:
                elapsed = (now - current_stage_time).total_seconds()
                if elapsed > stall_threshold_seconds:
                    stalled.append(state)

        return stalled


class PriorityQueueManager:
    """
    Manages priority routing for grant processing.

    Routes critical grants (high match + urgent deadline) to fast path.
    """

    # Priority thresholds
    CRITICAL_MATCH_THRESHOLD = 0.95  # 95% match score
    CRITICAL_DEADLINE_DAYS = 30

    # Queue depth thresholds for scaling
    SCALE_UP_THRESHOLD = 100
    SCALE_DOWN_THRESHOLD = 20

    def __init__(self, celery_app: Any):
        """
        Initialize queue manager.

        Args:
            celery_app: Celery application instance.
        """
        self._celery = celery_app
        self._inspect = celery_app.control.inspect()

    def determine_priority(
        self,
        match_score: float,
        deadline: Optional[datetime],
    ) -> str:
        """
        Determine queue priority for a grant.

        Args:
            match_score: Match score (0.0 to 1.0).
            deadline: Grant deadline if known.

        Returns:
            Queue name (critical, high, or normal).
        """
        is_high_match = match_score >= self.CRITICAL_MATCH_THRESHOLD
        is_urgent = False

        if deadline:
            days_until = (deadline - datetime.utcnow()).days
            is_urgent = days_until <= self.CRITICAL_DEADLINE_DAYS

        if is_high_match and is_urgent:
            return "critical"
        elif is_high_match or is_urgent:
            return "high"
        else:
            return "normal"

    def route_task(
        self,
        task_name: str,
        match_score: Optional[float] = None,
        deadline: Optional[datetime] = None,
        is_background: bool = False,
    ) -> dict[str, Any]:
        """
        Get routing options for a task.

        Args:
            task_name: Celery task name.
            match_score: Optional match score for priority.
            deadline: Optional deadline for priority.
            is_background: Whether this is a background task.

        Returns:
            Dictionary with queue and priority options.
        """
        if is_background:
            return {"queue": "normal", "priority": 1}

        if match_score is not None:
            queue = self.determine_priority(match_score, deadline)
            priority_map = {"critical": 10, "high": 7, "normal": 3}
            return {
                "queue": queue,
                "priority": priority_map.get(queue, 3),
            }

        return {"queue": "normal", "priority": 3}

    async def get_queue_depths(self) -> dict[str, int]:
        """Get current depth of each queue."""
        try:
            # Get queue lengths from Redis
            # Note: This uses the Celery broker URL
            broker_url = settings.celery_broker_url
            r = redis.from_url(broker_url, decode_responses=True)

            depths = {}
            for queue in ["critical", "high", "normal"]:
                # Celery uses list data structure for queues
                length = await r.llen(queue)
                depths[queue] = length

            await r.aclose()
            return depths

        except Exception as e:
            logger.error(f"Failed to get queue depths: {e}")
            return {}

    async def check_scaling_needed(self) -> Optional[WorkerScalingDecision]:
        """
        Check if worker scaling is needed.

        Returns:
            WorkerScalingDecision if scaling is needed, None otherwise.
        """
        depths = await self.get_queue_depths()
        total_depth = sum(depths.values())

        # Get current worker count
        try:
            stats = self._inspect.stats()
            worker_count = len(stats) if stats else 0
        except Exception:
            worker_count = 0

        if total_depth > self.SCALE_UP_THRESHOLD:
            return WorkerScalingDecision(
                queue_name="all",
                current_workers=worker_count,
                target_workers=worker_count + 2,
                reason=f"Queue depth ({total_depth}) exceeds threshold",
                queue_depth=total_depth,
                threshold=self.SCALE_UP_THRESHOLD,
            )

        elif total_depth < self.SCALE_DOWN_THRESHOLD and worker_count > 2:
            return WorkerScalingDecision(
                queue_name="all",
                current_workers=worker_count,
                target_workers=max(2, worker_count - 1),
                reason=f"Queue depth ({total_depth}) below threshold",
                queue_depth=total_depth,
                threshold=self.SCALE_DOWN_THRESHOLD,
            )

        return None


class Orchestrator:
    """
    Main orchestrator coordinating all GrantRadar agents.

    Responsibilities:
    - Coordinate event pipeline flow
    - Monitor agent and system health
    - Manage circuit breakers for external services
    - Handle priority routing
    - Trigger on-call alerts when needed
    - Auto-scale workers based on load
    """

    # Health check interval in seconds
    HEALTH_CHECK_INTERVAL = 30

    # On-call alert threshold (agent down for 5 minutes)
    ON_CALL_ALERT_THRESHOLD_SECONDS = 300

    # Metrics collection interval
    METRICS_INTERVAL = 60

    def __init__(
        self,
        redis_url: Optional[str] = None,
        on_call_callback: Optional[Callable[[OnCallAlert], None]] = None,
    ):
        """
        Initialize orchestrator.

        Args:
            redis_url: Redis connection URL.
            on_call_callback: Callback for on-call alerts.
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None

        # Components
        self._health_checker: Optional[HealthChecker] = None
        self._metrics_collector: Optional[MetricsCollector] = None
        self._event_bus: Optional[EventBus] = None
        self._pipeline_tracker: Optional[PipelineTracker] = None
        self._queue_manager: Optional[PriorityQueueManager] = None

        # Circuit breakers
        self._llm_circuit = LLMCircuitBreaker()
        self._grant_source_circuits = {
            "nih": nih_circuit,
            "nsf": nsf_circuit,
            "grants_gov": grants_gov_circuit,
        }

        # Callbacks
        self._on_call_callback = on_call_callback

        # State
        self._running = False
        self._last_health_check: Optional[datetime] = None
        self._last_metrics_collection: Optional[datetime] = None

    async def start(self) -> None:
        """Start the orchestrator."""
        logger.info("Starting GrantRadar Orchestrator")

        # Initialize Redis connection
        self._redis = redis.from_url(
            self._redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._redis.ping()

        # Initialize components
        self._health_checker = await get_health_checker()
        self._metrics_collector = await get_metrics_collector()
        self._event_bus = await get_event_bus()
        self._pipeline_tracker = PipelineTracker(self._redis)
        self._queue_manager = PriorityQueueManager(celery_app)

        self._running = True
        logger.info("Orchestrator started successfully")

    async def stop(self) -> None:
        """Stop the orchestrator."""
        logger.info("Stopping GrantRadar Orchestrator")
        self._running = False

        if self._redis:
            await self._redis.aclose()

    async def run_monitoring_loop(self) -> None:
        """
        Main monitoring loop.

        Runs health checks, collects metrics, and handles alerts.
        """
        while self._running:
            try:
                await self._run_health_checks()
                await self._collect_metrics()
                await self._check_stalled_pipelines()
                await self._check_scaling()

            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)

            await asyncio.sleep(self.HEALTH_CHECK_INTERVAL)

    async def _run_health_checks(self) -> None:
        """Run health checks and trigger alerts if needed."""
        if not self._health_checker:
            return

        report = await self._health_checker.get_full_health_report()
        self._last_health_check = datetime.utcnow()

        # Check for agents that need on-call alerts
        for agent_name, agent_health_data in report.get("agents", {}).items():
            agent_health = AgentHealth.model_validate(agent_health_data)

            if agent_health.needs_alert(self.ON_CALL_ALERT_THRESHOLD_SECONDS):
                await self._trigger_on_call_alert(
                    severity="critical",
                    title=f"Agent {agent_name} is down",
                    message=(
                        f"Agent {agent_name} has been unhealthy for {agent_health.downtime_seconds():.0f} seconds"
                    ),
                    agent_name=agent_name,
                    downtime=agent_health.downtime_seconds(),
                )

        # Check for unhealthy endpoints
        for endpoint_name in report.get("issues", {}).get("unhealthy_endpoints", []):
            endpoint = report["endpoints"].get(endpoint_name, {})
            failures = endpoint.get("consecutive_failures", 0)

            if failures >= 3:
                await self._trigger_on_call_alert(
                    severity="warning",
                    title=f"Endpoint {endpoint_name} is unhealthy",
                    message=(f"Endpoint {endpoint_name} has failed {failures} consecutive health checks"),
                    endpoint_name=endpoint_name,
                )

        # Store health data in metrics
        if self._metrics_collector:
            for agent_name, health_data in report.get("agents", {}).items():
                health = AgentHealth.model_validate(health_data)
                await self._metrics_collector.store_agent_health(health)

    async def _collect_metrics(self) -> None:
        """Collect and store system metrics."""
        if not self._metrics_collector:
            return

        now = datetime.utcnow()
        if (
            self._last_metrics_collection
            and (now - self._last_metrics_collection).total_seconds() < self.METRICS_INTERVAL
        ):
            return

        metrics = await self._metrics_collector.collect_system_metrics()
        await self._metrics_collector.store_metrics_snapshot(metrics)
        self._last_metrics_collection = now

        # Update queue depths
        if self._queue_manager:
            depths = await self._queue_manager.get_queue_depths()
            await self._metrics_collector.update_queue_depths(depths)

    async def _check_stalled_pipelines(self) -> None:
        """Check for and handle stalled pipelines."""
        if not self._pipeline_tracker:
            return

        stalled = await self._pipeline_tracker.get_stalled_pipelines()

        for pipeline in stalled:
            logger.warning(f"Stalled pipeline detected: {pipeline.grant_id} at stage {pipeline.current_stage.value}")

            # Could implement retry logic here
            if pipeline.retry_count < 3:
                pipeline.retry_count += 1
                # Republish to retry
            else:
                await self._pipeline_tracker.fail_pipeline(
                    pipeline.grant_id,
                    "Pipeline stalled after max retries",
                )

    async def _check_scaling(self) -> None:
        """Check if worker scaling is needed."""
        if not self._queue_manager:
            return

        decision = await self._queue_manager.check_scaling_needed()

        if decision:
            logger.info(
                f"Scaling decision: {decision.current_workers} -> "
                f"{decision.target_workers} workers. Reason: {decision.reason}"
            )
            # In production, this would trigger actual scaling
            # (e.g., Kubernetes HPA, AWS Auto Scaling, etc.)

    async def _trigger_on_call_alert(
        self,
        severity: str,
        title: str,
        message: str,
        agent_name: Optional[str] = None,
        endpoint_name: Optional[str] = None,
        downtime: float = 0.0,
    ) -> None:
        """Trigger an on-call alert."""
        alert = OnCallAlert(
            severity=severity,
            title=title,
            message=message,
            agent_name=agent_name,
            endpoint_name=endpoint_name,
            downtime_seconds=downtime,
        )

        logger.warning(f"On-call alert: {title} - {message}")

        if self._on_call_callback:
            try:
                self._on_call_callback(alert)
            except Exception as e:
                logger.error(f"Failed to send on-call alert: {e}")

    # =========================================================================
    # Pipeline Coordination
    # =========================================================================

    async def handle_grant_discovered(
        self,
        grant_id: UUID,
        source: str,
        title: str,
        deadline: Optional[datetime] = None,
    ) -> str:
        """
        Handle a newly discovered grant.

        Starts the pipeline and routes to validation.

        Args:
            grant_id: Unique grant identifier.
            source: Grant source (nih, nsf, grants_gov).
            title: Grant title.
            deadline: Optional deadline.

        Returns:
            Pipeline priority.
        """
        if not self._pipeline_tracker:
            raise RuntimeError("Orchestrator not started")

        # Determine initial priority based on deadline
        priority = "normal"
        if deadline:
            days_until = (deadline - datetime.utcnow()).days
            if days_until <= 7:
                priority = "critical"
            elif days_until <= 30:
                priority = "high"

        # Start tracking
        await self._pipeline_tracker.start_pipeline(
            grant_id=grant_id,
            priority=priority,
            metadata={"source": source, "title": title},
        )

        # Record metrics
        if self._metrics_collector:
            await self._metrics_collector.record_agent_success(AgentType.DISCOVERY)

        logger.info(f"Grant discovered: {grant_id} from {source} with priority {priority}")

        return priority

    async def handle_grant_validated(
        self,
        grant_id: UUID,
        quality_score: float,
    ) -> None:
        """
        Handle a validated grant.

        Transitions pipeline and triggers matching.

        Args:
            grant_id: Grant identifier.
            quality_score: Validation quality score.
        """
        if not self._pipeline_tracker:
            raise RuntimeError("Orchestrator not started")

        state, latency = await self._pipeline_tracker.transition_stage(
            grant_id,
            PipelineStage.VALIDATING,
            PipelineStage.VALIDATED,
        )

        # Record metrics
        if self._metrics_collector:
            await self._metrics_collector.record_pipeline_latency(
                "validated",
                latency,
                str(grant_id),
            )
            await self._metrics_collector.record_agent_success(AgentType.CURATION)

        # Check if validation was fast enough
        if latency > PipelineTracker.VALIDATION_TARGET:
            logger.warning(
                f"Validation latency ({latency:.2f}s) exceeded target ({PipelineTracker.VALIDATION_TARGET}s)"
            )

    async def handle_matches_computed(
        self,
        grant_id: UUID,
        match_count: int,
        top_score: float,
    ) -> None:
        """
        Handle computed matches.

        Transitions pipeline and triggers alerts.

        Args:
            grant_id: Grant identifier.
            match_count: Number of matches computed.
            top_score: Highest match score.
        """
        if not self._pipeline_tracker:
            raise RuntimeError("Orchestrator not started")

        state, latency = await self._pipeline_tracker.transition_stage(
            grant_id,
            PipelineStage.MATCHING,
            PipelineStage.MATCHED,
        )

        # Record metrics
        if self._metrics_collector:
            await self._metrics_collector.record_pipeline_latency(
                "matched",
                latency,
                str(grant_id),
            )
            await self._metrics_collector.record_agent_success(AgentType.MATCHING)

        # Upgrade priority if high match found
        if top_score >= 0.95 and state.priority != "critical":
            state.priority = "critical"
            logger.info(f"Upgraded pipeline {grant_id} to critical priority due to high match ({top_score:.2%})")

    async def handle_alerts_sent(
        self,
        grant_id: UUID,
        alert_count: int,
    ) -> float:
        """
        Handle alerts sent.

        Completes the pipeline.

        Args:
            grant_id: Grant identifier.
            alert_count: Number of alerts sent.

        Returns:
            Total pipeline latency.
        """
        if not self._pipeline_tracker:
            raise RuntimeError("Orchestrator not started")

        # First transition to alerting if not already there
        state = self._pipeline_tracker._pipelines.get(str(grant_id))
        if state and state.current_stage == PipelineStage.MATCHED:
            await self._pipeline_tracker.transition_stage(
                grant_id,
                PipelineStage.MATCHED,
                PipelineStage.ALERTING,
            )

        # Complete pipeline
        state, total_latency = await self._pipeline_tracker.complete_pipeline(
            grant_id,
        )

        # Record metrics
        if self._metrics_collector:
            await self._metrics_collector.record_pipeline_latency(
                "completed",
                total_latency,
                str(grant_id),
            )
            await self._metrics_collector.record_agent_success(AgentType.DELIVERY)
            await self._metrics_collector.record_pipeline_success(str(grant_id))

            for _ in range(alert_count):
                await self._metrics_collector.record_alert_sent("email")
                await self._metrics_collector.record_alert_delivered("email")

        logger.info(f"Pipeline completed for {grant_id}: {alert_count} alerts sent in {total_latency:.2f}s")

        return total_latency

    # =========================================================================
    # Circuit Breaker Management
    # =========================================================================

    def get_grant_source_circuit(self, source: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker for a grant source."""
        return self._grant_source_circuits.get(source)

    def get_llm_provider(self) -> str:
        """Get the LLM provider to use based on circuit state."""
        return self._llm_circuit.get_provider()

    def record_llm_latency(self, latency_ms: float) -> None:
        """Record LLM call latency."""
        self._llm_circuit.record_latency(latency_ms)

    def record_llm_success(self) -> None:
        """Record successful LLM call."""
        self._llm_circuit.record_success()

    def record_llm_failure(self) -> None:
        """Record failed LLM call."""
        self._llm_circuit.record_failure()

    def get_circuit_breaker_states(self) -> dict[str, CircuitBreakerState]:
        """Get all circuit breaker states."""
        states = {}

        # Grant source circuits
        for name, circuit in self._grant_source_circuits.items():
            state_map = {
                CircuitBreaker.CLOSED: CircuitState.CLOSED,
                CircuitBreaker.OPEN: CircuitState.OPEN,
                CircuitBreaker.HALF_OPEN: CircuitState.HALF_OPEN,
            }
            states[name] = CircuitBreakerState(
                service_name=name,
                state=state_map.get(circuit.state, CircuitState.CLOSED),
                failure_count=circuit._failure_count,
                failure_threshold=circuit.failure_threshold,
                recovery_timeout_seconds=circuit.recovery_timeout,
            )

        # LLM circuit
        states["llm"] = self._llm_circuit.state

        return states

    # =========================================================================
    # System Status
    # =========================================================================

    async def get_system_status(self) -> dict[str, Any]:
        """
        Get comprehensive system status.

        Returns:
            Dictionary with all system status information.
        """
        status: dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "orchestrator_running": self._running,
        }

        # Health report
        if self._health_checker:
            status["health"] = await self._health_checker.get_full_health_report()

        # Current metrics
        if self._metrics_collector:
            metrics = await self._metrics_collector.get_current_metrics()
            if metrics:
                status["metrics"] = metrics.model_dump()

            # SLOs
            slos = await self._metrics_collector.calculate_slos()
            status["slos"] = [slo.model_dump() for slo in slos]

        # Active pipelines
        if self._pipeline_tracker:
            active = await self._pipeline_tracker.get_active_pipelines()
            status["active_pipelines"] = len(active)
            status["pipeline_details"] = [
                {
                    "grant_id": str(p.grant_id),
                    "stage": p.current_stage.value,
                    "priority": p.priority,
                    "latency_seconds": p.total_latency(),
                }
                for p in active
            ]

        # Queue depths
        if self._queue_manager:
            status["queue_depths"] = await self._queue_manager.get_queue_depths()

        # Circuit breakers
        status["circuit_breakers"] = {
            name: state.model_dump() for name, state in self.get_circuit_breaker_states().items()
        }

        return status


# Global orchestrator instance
_orchestrator: Optional[Orchestrator] = None


async def get_orchestrator() -> Orchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator

    if _orchestrator is None:
        _orchestrator = Orchestrator()
        await _orchestrator.start()

    return _orchestrator


async def close_orchestrator() -> None:
    """Close the global orchestrator."""
    global _orchestrator

    if _orchestrator is not None:
        await _orchestrator.stop()
        _orchestrator = None
