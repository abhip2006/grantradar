"""TypedDict definitions for JSONB field validation.

Provides type-safe definitions for JSONB fields used in SQLAlchemy models
to enable better type checking and validation of JSON data structures.
"""

from typing import TypedDict, Optional, List


# =============================================================================
# Checklist Items
# =============================================================================


class ChecklistItemDict(TypedDict, total=False):
    """
    TypedDict for checklist item stored in JSONB fields.

    Used in:
    - ChecklistTemplate.items
    - ApplicationChecklist.items

    Fields:
        id: Unique identifier for the item within the checklist
        title: Item title (required)
        description: Detailed description of the item
        required: Whether this item is required for completion
        weight: Weight for progress calculation (0.0-10.0)
        category: Category of the item (administrative, scientific, etc.)
        dependencies: IDs of items that must be completed first
        completed: Whether the item is completed (for application checklists)
        completed_at: ISO timestamp when item was completed
        completed_by: UUID of user who completed the item
        notes: Additional notes about completion
    """

    id: str
    title: str
    description: Optional[str]
    required: bool
    weight: float
    category: str
    dependencies: List[str]
    completed: bool
    completed_at: Optional[str]  # ISO 8601 datetime string
    completed_by: Optional[str]  # UUID as string
    notes: Optional[str]


# =============================================================================
# Review Workflow Stages
# =============================================================================


class WorkflowStageDict(TypedDict, total=False):
    """
    TypedDict for workflow stage configuration stored in JSONB fields.

    Used in:
    - ReviewWorkflow.stages

    Fields:
        order: Stage order (0-indexed)
        name: Stage name
        required_role: Role required to approve this stage (pi, co_i, reviewer, etc.)
        sla_hours: SLA time limit in hours
        auto_escalate: Whether to auto-escalate when SLA is exceeded
        description: Stage description
    """

    order: int
    name: str
    required_role: Optional[str]
    sla_hours: Optional[int]
    auto_escalate: bool
    description: Optional[str]


# =============================================================================
# Team Member Permissions
# =============================================================================


class TeamMemberPermissionsDict(TypedDict, total=False):
    """
    TypedDict for team member permissions stored in JSONB fields.

    Used in:
    - ApplicationTeamMember.permissions

    Fields:
        can_edit: Can edit application content
        can_approve: Can approve review stages
        can_submit: Can submit the application
        sections: Specific sections they can access (null = all sections)
    """

    can_edit: bool
    can_approve: bool
    can_submit: bool
    sections: Optional[List[str]]


# =============================================================================
# Compliance Rules
# =============================================================================


class ComplianceRuleItemDict(TypedDict, total=False):
    """
    TypedDict for a single compliance rule stored in JSONB fields.

    Used in:
    - ComplianceRule.rules

    Fields:
        type: Rule type (page_limit, font_size, margin, section_required, etc.)
        name: Rule name
        description: Rule description
        params: Rule parameters (varies by type)
        severity: Severity level (error, warning, info)
        message: Custom message when rule fails
        document_types: Document types this rule applies to (null = all)
    """

    type: str
    name: str
    description: Optional[str]
    params: dict
    severity: str  # "error", "warning", "info"
    message: Optional[str]
    document_types: Optional[List[str]]


# =============================================================================
# Compliance Scan Results
# =============================================================================


class ComplianceScanResultDict(TypedDict, total=False):
    """
    TypedDict for compliance scan result stored in JSONB fields.

    Used in:
    - ComplianceScan.results

    Fields:
        rule_id: Identifier for the rule
        rule_name: Name of the rule
        rule_type: Type of the rule
        passed: Whether the rule passed
        severity: Severity level (error, warning, info)
        message: Result message
        location: Location in document where issue was found
        details: Additional details (actual vs expected, etc.)
    """

    rule_id: str
    rule_name: str
    rule_type: Optional[str]
    passed: bool
    severity: str  # "error", "warning", "info"
    message: str
    location: Optional[str]
    details: Optional[dict]


# =============================================================================
# Workflow Event Metadata
# =============================================================================


class WorkflowEventMetadataDict(TypedDict, total=False):
    """
    TypedDict for workflow event metadata stored in JSONB fields.

    Used in:
    - WorkflowEvent.metadata_
    - ReviewStageAction.metadata_

    Fields:
        previous_value: Previous value before change
        new_value: New value after change
        reason: Reason for the change/action
        triggered_by: What triggered this event (user, system, automation)
        additional_info: Any additional context-specific information
    """

    previous_value: Optional[str]
    new_value: Optional[str]
    reason: Optional[str]
    triggered_by: Optional[str]
    additional_info: Optional[dict]


# =============================================================================
# Analytics Metrics
# =============================================================================


class StageTimeMetricsDict(TypedDict, total=False):
    """
    TypedDict for stage time metrics within workflow metrics.

    Used within WorkflowMetricsDict.avg_time_per_stage
    """

    avg_hours: float
    median_hours: float
    min_hours: float
    max_hours: float
    count: int


class WorkflowMetricsDict(TypedDict, total=False):
    """
    TypedDict for aggregated workflow metrics stored in JSONB fields.

    Used in:
    - WorkflowAnalytics.metrics

    Fields:
        avg_time_per_stage: Dictionary mapping stage names to time metrics
        bottlenecks: List of stage names identified as bottlenecks
        completion_rate: Percentage of applications reaching completion
        success_rate: Percentage of submitted applications that were awarded
        total_applications: Total applications in the analytics period
        applications_by_status: Count of applications by status
        fastest_completion_hours: Fastest application completion time
        slowest_completion_hours: Slowest application completion time
    """

    avg_time_per_stage: dict  # stage_name -> StageTimeMetricsDict or hours (float)
    bottlenecks: List[str]
    completion_rate: float
    success_rate: float
    total_applications: int
    applications_by_status: dict  # status -> count
    fastest_completion_hours: Optional[float]
    slowest_completion_hours: Optional[float]


# =============================================================================
# Document Component Metadata
# =============================================================================


class ComponentMetadataDict(TypedDict, total=False):
    """
    TypedDict for document component metadata stored in JSONB fields.

    Used in:
    - DocumentComponent.metadata

    Fields:
        author: Original author of the content
        institution: Institution associated with the content
        last_used: ISO timestamp of last usage
        use_count: Number of times the component has been used
        source: Source document or reference
        keywords: Search keywords for the component
        version_note: Note about this version of the component
    """

    author: Optional[str]
    institution: Optional[str]
    last_used: Optional[str]  # ISO 8601 datetime string
    use_count: int
    source: Optional[str]
    keywords: Optional[List[str]]
    version_note: Optional[str]


# =============================================================================
# Review Stage Action Metadata
# =============================================================================


class ReviewActionMetadataDict(TypedDict, total=False):
    """
    TypedDict for review stage action metadata stored in JSONB fields.

    Used in:
    - ReviewStageAction.metadata_

    Fields:
        files_attached: List of attached file references
        score: Numeric score if applicable
        criteria_scores: Scores by individual review criteria
        requires_followup: Whether follow-up is required
        followup_notes: Notes about required follow-up
    """

    files_attached: Optional[List[str]]
    score: Optional[float]
    criteria_scores: Optional[dict]
    requires_followup: bool
    followup_notes: Optional[str]


# =============================================================================
# Export All Types
# =============================================================================


__all__ = [
    # Checklist types
    "ChecklistItemDict",
    # Review workflow types
    "WorkflowStageDict",
    "TeamMemberPermissionsDict",
    "WorkflowEventMetadataDict",
    "ReviewActionMetadataDict",
    # Compliance types
    "ComplianceRuleItemDict",
    "ComplianceScanResultDict",
    # Component types
    "ComponentMetadataDict",
    # Analytics types
    "StageTimeMetricsDict",
    "WorkflowMetricsDict",
]
