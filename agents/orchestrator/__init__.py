"""
GrantRadar Orchestrator Agent

The Orchestrator is the central coordination layer for GrantRadar, responsible for:
- Event pipeline coordination (discovery -> validation -> matching -> delivery)
- Priority queue management with dynamic routing
- Health monitoring and alerting
- Circuit breaker management for graceful degradation
- Auto-scaling decisions for Celery workers
- Metrics collection and SLO tracking

Usage:
    from agents.orchestrator import get_orchestrator

    orchestrator = await get_orchestrator()
    status = await orchestrator.get_system_status()
"""

from .coordinator import (
    LLMCircuitBreaker,
    Orchestrator,
    PipelineTracker,
    PriorityQueueManager,
    close_orchestrator,
    get_orchestrator,
)
from .health import (
    HealthChecker,
    LatencyTracker,
    close_health_checker,
    get_health_checker,
)
from .metrics import (
    MetricKeys,
    MetricsCollector,
    close_metrics_collector,
    get_metrics_collector,
)
from .models import (
    AgentHealth,
    AgentType,
    CircuitBreakerState,
    CircuitState,
    EndpointHealth,
    HealthStatus,
    OnCallAlert,
    PipelineStage,
    PipelineState,
    QueueMetrics,
    SLOStatus,
    SystemMetrics,
    WorkerScalingDecision,
)

__all__ = [
    # Coordinator
    "Orchestrator",
    "get_orchestrator",
    "close_orchestrator",
    "PipelineTracker",
    "PriorityQueueManager",
    "LLMCircuitBreaker",
    # Health
    "HealthChecker",
    "get_health_checker",
    "close_health_checker",
    "LatencyTracker",
    # Metrics
    "MetricsCollector",
    "get_metrics_collector",
    "close_metrics_collector",
    "MetricKeys",
    # Models
    "PipelineStage",
    "PipelineState",
    "AgentType",
    "AgentHealth",
    "HealthStatus",
    "CircuitState",
    "CircuitBreakerState",
    "EndpointHealth",
    "QueueMetrics",
    "SystemMetrics",
    "SLOStatus",
    "WorkerScalingDecision",
    "OnCallAlert",
]
