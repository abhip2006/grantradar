"""
Workflow Analytics Schemas

Pydantic schemas for workflow analytics operations including:
- Event tracking
- Time per stage analysis
- Bottleneck identification
- Completion rate tracking
- Deadline risk forecasting
"""

from datetime import date, datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from backend.schemas.common import PaginationInfo


# =============================================================================
# Workflow Event Schemas
# =============================================================================


class WorkflowEventBase(BaseModel):
    """Base schema for workflow events."""

    event_type: str = Field(
        ...,
        description="Type of event: 'stage_enter', 'stage_exit', 'action', 'milestone'",
    )
    stage: Optional[str] = Field(
        None,
        description="Stage associated with this event",
    )
    previous_stage: Optional[str] = Field(
        None,
        description="Previous stage (for stage transitions)",
    )
    metadata: Optional[dict[str, Any]] = Field(
        None,
        description="Additional event metadata",
    )


class WorkflowEventCreate(WorkflowEventBase):
    """Schema for creating a workflow event."""

    kanban_card_id: UUID = Field(
        ...,
        description="ID of the grant application (kanban card)",
    )

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate that event_type is a valid workflow event type."""
        valid_types = {
            "stage_enter",
            "stage_exit",
            "action",
            "milestone",
            "note_added",
            "subtask_completed",
            "subtask_added",
            "attachment_added",
            "priority_changed",
            "deadline_set",
            "assignee_added",
            "assignee_removed",
        }
        if v not in valid_types:
            raise ValueError(f"Invalid event_type '{v}'. Must be one of: {sorted(valid_types)}")
        return v

    @field_validator("metadata")
    @classmethod
    def validate_metadata_structure(cls, v: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        """Validate that metadata conforms to WorkflowEventMetadataDict structure."""
        if v is None:
            return v

        # Optional: Validate known metadata fields if present
        # Allow additional keys but log warning for unknown ones
        # This is a loose validation to allow flexibility

        return v


class WorkflowEventResponse(WorkflowEventBase):
    """Schema for workflow event response."""

    id: UUID = Field(..., description="Event ID")
    kanban_card_id: UUID = Field(..., description="Grant application ID")
    user_id: Optional[UUID] = Field(None, description="User who triggered the event")
    occurred_at: datetime = Field(..., description="When the event occurred")

    class Config:
        from_attributes = True


class WorkflowEventsListResponse(BaseModel):
    """Schema for list of workflow events (standard paginated format)."""

    data: List[WorkflowEventResponse] = Field(
        default_factory=list,
        description="List of workflow events",
    )
    pagination: PaginationInfo = Field(..., description="Pagination metadata")

    # Backward compatibility aliases
    @property
    def events(self) -> List[WorkflowEventResponse]:
        """Backward compatibility: alias for 'data'."""
        return self.data

    @property
    def total(self) -> int:
        """Backward compatibility: alias for 'pagination.total'."""
        return self.pagination.total


# =============================================================================
# Time Per Stage Schemas
# =============================================================================


class StageTimeMetrics(BaseModel):
    """Time metrics for a single pipeline stage."""

    stage: str = Field(..., description="Stage name")
    avg_hours: float = Field(..., description="Average hours spent in this stage")
    median_hours: float = Field(..., description="Median hours spent in this stage")
    min_hours: float = Field(..., description="Minimum hours in this stage")
    max_hours: float = Field(..., description="Maximum hours in this stage")
    applications_count: int = Field(
        ...,
        description="Number of applications that passed through this stage",
    )
    currently_in_stage: int = Field(
        ...,
        description="Number of applications currently in this stage",
    )


class TimePerStageResponse(BaseModel):
    """Response for time per stage analysis."""

    stages: list[StageTimeMetrics] = Field(
        default_factory=list,
        description="Time metrics for each stage",
    )
    total_avg_time_hours: float = Field(
        ...,
        description="Average total time from start to completion",
    )
    fastest_completion_hours: Optional[float] = Field(
        None,
        description="Fastest application completion time",
    )
    slowest_completion_hours: Optional[float] = Field(
        None,
        description="Slowest application completion time",
    )


# =============================================================================
# Bottleneck Schemas
# =============================================================================


class BottleneckInfo(BaseModel):
    """Information about a workflow bottleneck."""

    stage: str = Field(..., description="Stage where bottleneck occurs")
    severity: str = Field(
        ...,
        description="Severity level: 'low', 'medium', 'high', 'critical'",
    )
    avg_wait_hours: float = Field(
        ...,
        description="Average wait time in this stage",
    )
    applications_stuck: int = Field(
        ...,
        description="Number of applications currently stuck",
    )
    pct_above_threshold: float = Field(
        ...,
        description="Percentage of applications exceeding expected time",
        ge=0,
        le=100,
    )
    recommendation: str = Field(
        ...,
        description="Recommendation to address the bottleneck",
    )


class BottlenecksResponse(BaseModel):
    """Response for bottleneck identification."""

    bottlenecks: list[BottleneckInfo] = Field(
        default_factory=list,
        description="Identified bottlenecks sorted by severity",
    )
    total_at_risk: int = Field(
        ...,
        description="Total applications at risk of missing deadlines",
    )
    overall_health: str = Field(
        ...,
        description="Overall workflow health: 'healthy', 'warning', 'critical'",
    )


# =============================================================================
# Completion Rate Schemas
# =============================================================================


class CompletionRateMetrics(BaseModel):
    """Completion rate metrics for a time period."""

    period: str = Field(..., description="Time period (e.g., '2024-01', '2024-Q1')")
    total_started: int = Field(..., description="Applications started")
    submitted: int = Field(..., description="Applications submitted")
    awarded: int = Field(..., description="Applications awarded")
    rejected: int = Field(..., description="Applications rejected")
    in_progress: int = Field(..., description="Applications still in progress")
    submission_rate: float = Field(
        ...,
        description="Percentage that reached submission (0-100)",
        ge=0,
        le=100,
    )
    success_rate: float = Field(
        ...,
        description="Percentage of submitted that were awarded (0-100)",
        ge=0,
        le=100,
    )


class CompletionRatesResponse(BaseModel):
    """Response for completion rate tracking."""

    periods: list[CompletionRateMetrics] = Field(
        default_factory=list,
        description="Completion metrics by period",
    )
    overall_submission_rate: float = Field(
        ...,
        description="Overall submission rate (0-100)",
        ge=0,
        le=100,
    )
    overall_success_rate: float = Field(
        ...,
        description="Overall success rate (0-100)",
        ge=0,
        le=100,
    )
    trend: str = Field(
        ...,
        description="Trend direction: 'improving', 'declining', 'stable'",
    )


# =============================================================================
# Deadline Risk Schemas
# =============================================================================


class DeadlineRiskApplication(BaseModel):
    """Application with deadline risk assessment."""

    application_id: UUID = Field(..., description="Grant application ID")
    grant_title: str = Field(..., description="Grant title")
    current_stage: str = Field(..., description="Current stage")
    deadline: Optional[datetime] = Field(None, description="Application deadline")
    days_until_deadline: Optional[int] = Field(
        None,
        description="Days remaining until deadline",
    )
    estimated_days_to_complete: float = Field(
        ...,
        description="Estimated days needed to complete based on historical data",
    )
    risk_level: str = Field(
        ...,
        description="Risk level: 'low', 'medium', 'high', 'critical'",
    )
    risk_score: float = Field(
        ...,
        description="Risk score from 0 to 100",
        ge=0,
        le=100,
    )
    recommended_actions: list[str] = Field(
        default_factory=list,
        description="Recommended actions to mitigate risk",
    )


class DeadlineRiskForecastResponse(BaseModel):
    """Response for deadline risk forecasting."""

    at_risk_applications: list[DeadlineRiskApplication] = Field(
        default_factory=list,
        description="Applications with elevated deadline risk",
    )
    total_applications: int = Field(
        ...,
        description="Total applications analyzed",
    )
    low_risk_count: int = Field(..., description="Applications with low risk")
    medium_risk_count: int = Field(..., description="Applications with medium risk")
    high_risk_count: int = Field(..., description="Applications with high risk")
    critical_risk_count: int = Field(
        ...,
        description="Applications with critical risk",
    )


# =============================================================================
# Workflow Analytics Summary Schemas
# =============================================================================


class WorkflowAnalyticsSummary(BaseModel):
    """Summary of workflow analytics for dashboard."""

    total_applications: int = Field(..., description="Total applications tracked")
    active_applications: int = Field(..., description="Applications in progress")
    completed_applications: int = Field(
        ...,
        description="Applications completed (awarded or rejected)",
    )
    avg_completion_time_days: Optional[float] = Field(
        None,
        description="Average days from start to completion",
    )
    submission_rate: float = Field(
        ...,
        description="Percentage reaching submission (0-100)",
        ge=0,
        le=100,
    )
    success_rate: float = Field(
        ...,
        description="Percentage of submissions that were awarded (0-100)",
        ge=0,
        le=100,
    )
    current_bottleneck: Optional[str] = Field(
        None,
        description="Current primary bottleneck stage",
    )
    at_risk_count: int = Field(
        ...,
        description="Applications at risk of missing deadlines",
    )
    workflow_health: str = Field(
        ...,
        description="Overall workflow health: 'healthy', 'warning', 'critical'",
    )


class WorkflowAnalyticsResponse(BaseModel):
    """Complete workflow analytics response."""

    summary: WorkflowAnalyticsSummary = Field(
        ...,
        description="Summary metrics",
    )
    time_per_stage: TimePerStageResponse = Field(
        ...,
        description="Time analysis by stage",
    )
    bottlenecks: BottlenecksResponse = Field(
        ...,
        description="Identified bottlenecks",
    )
    deadline_risks: DeadlineRiskForecastResponse = Field(
        ...,
        description="Deadline risk forecast",
    )
    period_start: date = Field(..., description="Analysis period start")
    period_end: date = Field(..., description="Analysis period end")
    generated_at: datetime = Field(..., description="When analytics were generated")


# =============================================================================
# Stored Analytics Schemas
# =============================================================================


class StoredWorkflowAnalyticsResponse(BaseModel):
    """Schema for stored workflow analytics record."""

    id: UUID = Field(..., description="Analytics record ID")
    user_id: UUID = Field(..., description="User ID")
    period_start: date = Field(..., description="Period start date")
    period_end: date = Field(..., description="Period end date")
    period_type: str = Field(..., description="Period type (daily, weekly, monthly)")
    metrics: dict[str, Any] = Field(..., description="Stored metrics")
    generated_at: datetime = Field(..., description="Generation timestamp")

    class Config:
        from_attributes = True


# =============================================================================
# Team Productivity Schemas (for future team features)
# =============================================================================


class TeamMemberProductivity(BaseModel):
    """Productivity metrics for a team member."""

    user_id: UUID = Field(..., description="Team member user ID")
    name: str = Field(..., description="Team member name")
    applications_assigned: int = Field(..., description="Applications assigned")
    applications_completed: int = Field(..., description="Applications completed")
    avg_completion_time_days: Optional[float] = Field(
        None,
        description="Average completion time in days",
    )
    on_time_completion_rate: float = Field(
        ...,
        description="Percentage completed on time (0-100)",
        ge=0,
        le=100,
    )


class TeamProductivityResponse(BaseModel):
    """Team productivity metrics response."""

    team_members: list[TeamMemberProductivity] = Field(
        default_factory=list,
        description="Productivity by team member",
    )
    total_team_applications: int = Field(
        ...,
        description="Total team applications",
    )
    team_avg_completion_time_days: Optional[float] = Field(
        None,
        description="Team average completion time",
    )


__all__ = [
    # Event schemas
    "WorkflowEventBase",
    "WorkflowEventCreate",
    "WorkflowEventResponse",
    "WorkflowEventsListResponse",
    # Time per stage
    "StageTimeMetrics",
    "TimePerStageResponse",
    # Bottlenecks
    "BottleneckInfo",
    "BottlenecksResponse",
    # Completion rates
    "CompletionRateMetrics",
    "CompletionRatesResponse",
    # Deadline risk
    "DeadlineRiskApplication",
    "DeadlineRiskForecastResponse",
    # Summary and complete response
    "WorkflowAnalyticsSummary",
    "WorkflowAnalyticsResponse",
    "StoredWorkflowAnalyticsResponse",
    # Team productivity
    "TeamMemberProductivity",
    "TeamProductivityResponse",
]
