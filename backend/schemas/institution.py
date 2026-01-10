"""Institution schemas for multi-user portfolio views and institutional dashboards."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, EmailStr


class InstitutionType(str, Enum):
    """Type of institution/organization."""

    UNIVERSITY = "university"
    RESEARCH_INSTITUTE = "research_institute"
    NONPROFIT = "nonprofit"
    GOVERNMENT = "government"
    INDUSTRY = "industry"


class InstitutionMemberRole(str, Enum):
    """Role of a member within an institution."""

    ADMIN = "admin"  # Full access, can manage institution settings and members
    MANAGER = "manager"  # Can view portfolio, manage members
    VIEWER = "viewer"  # Read-only access to portfolio


# ============================================================================
# Institution Schemas
# ============================================================================


class InstitutionSettings(BaseModel):
    """Institution-specific settings and preferences."""

    allow_member_self_join: bool = Field(
        default=False, description="Allow users with matching domain to join automatically"
    )
    require_approval: bool = Field(default=True, description="Require admin approval for new members")
    default_member_role: InstitutionMemberRole = Field(
        default=InstitutionMemberRole.VIEWER, description="Default role for new members"
    )
    visibility: str = Field(default="private", description="Institution visibility: 'private' or 'public'")
    enable_department_grouping: bool = Field(default=True, description="Enable department-level views")
    benchmarking_enabled: bool = Field(default=True, description="Enable success rate benchmarking")
    notification_preferences: Optional[dict] = Field(None, description="Institution-wide notification settings")

    class Config:
        from_attributes = True


class InstitutionCreate(BaseModel):
    """Request to create a new institution."""

    name: str = Field(..., min_length=2, max_length=255, description="Institution name")
    type: InstitutionType = Field(..., description="Type of institution")
    domain: Optional[str] = Field(
        None, max_length=255, description="Email domain for the institution (e.g., harvard.edu)"
    )
    description: Optional[str] = Field(None, max_length=2000, description="Description of the institution")
    logo_url: Optional[str] = Field(None, max_length=500, description="URL to institution logo")
    website: Optional[str] = Field(None, max_length=500, description="Institution website")
    address: Optional[str] = Field(None, max_length=1000, description="Physical address")
    settings: Optional[InstitutionSettings] = Field(None, description="Institution settings")


class InstitutionUpdate(BaseModel):
    """Request to update an institution."""

    name: Optional[str] = Field(None, min_length=2, max_length=255, description="Updated institution name")
    type: Optional[InstitutionType] = Field(None, description="Updated institution type")
    domain: Optional[str] = Field(None, max_length=255, description="Updated email domain")
    description: Optional[str] = Field(None, max_length=2000, description="Updated description")
    logo_url: Optional[str] = Field(None, max_length=500, description="Updated logo URL")
    website: Optional[str] = Field(None, max_length=500, description="Updated website")
    address: Optional[str] = Field(None, max_length=1000, description="Updated address")
    settings: Optional[InstitutionSettings] = Field(None, description="Updated settings")


class InstitutionResponse(BaseModel):
    """Response schema for institution data."""

    id: UUID = Field(..., description="Unique identifier for the institution")
    name: str = Field(..., description="Institution name")
    type: str = Field(..., description="Type of institution")
    domain: Optional[str] = Field(None, description="Email domain")
    description: Optional[str] = Field(None, description="Institution description")
    logo_url: Optional[str] = Field(None, description="Logo URL")
    website: Optional[str] = Field(None, description="Website")
    address: Optional[str] = Field(None, description="Physical address")
    settings: Optional[InstitutionSettings] = Field(None, description="Institution settings")
    created_by: Optional[UUID] = Field(None, description="User who created the institution")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    member_count: Optional[int] = Field(None, description="Number of members")

    class Config:
        from_attributes = True


# ============================================================================
# Member Schemas
# ============================================================================


class InstitutionMemberPermissions(BaseModel):
    """Custom permission overrides for institution members."""

    can_view_all_portfolios: bool = Field(default=False, description="Can view all member portfolios")
    can_view_metrics: bool = Field(default=True, description="Can view institution-wide metrics")
    can_manage_members: bool = Field(default=False, description="Can add/remove members")
    can_edit_settings: bool = Field(default=False, description="Can edit institution settings")
    can_export_data: bool = Field(default=False, description="Can export institution data")

    class Config:
        from_attributes = True


class InstitutionMemberCreate(BaseModel):
    """Request to add a member to an institution."""

    user_id: Optional[UUID] = Field(None, description="User ID (if existing user)")
    email: Optional[EmailStr] = Field(None, description="Email to invite (if not existing user)")
    role: InstitutionMemberRole = Field(default=InstitutionMemberRole.VIEWER, description="Member role")
    department: Optional[str] = Field(None, max_length=255, description="Department within institution")
    title: Optional[str] = Field(None, max_length=255, description="Job title/position")
    permissions: Optional[InstitutionMemberPermissions] = Field(None, description="Custom permission overrides")


class InstitutionMemberUpdate(BaseModel):
    """Request to update a member's role or details."""

    role: Optional[InstitutionMemberRole] = Field(None, description="Updated role")
    department: Optional[str] = Field(None, max_length=255, description="Updated department")
    title: Optional[str] = Field(None, max_length=255, description="Updated title")
    permissions: Optional[InstitutionMemberPermissions] = Field(None, description="Updated permissions")


class InstitutionMemberResponse(BaseModel):
    """Response schema for institution member data."""

    id: UUID = Field(..., description="Member record ID")
    institution_id: UUID = Field(..., description="Institution ID")
    user_id: UUID = Field(..., description="User ID")
    role: str = Field(..., description="Member role")
    department: Optional[str] = Field(None, description="Department")
    title: Optional[str] = Field(None, description="Job title")
    permissions: Optional[InstitutionMemberPermissions] = Field(None, description="Custom permissions")
    added_at: datetime = Field(..., description="When member was added")
    added_by: Optional[UUID] = Field(None, description="Who added the member")
    updated_at: datetime = Field(..., description="Last update timestamp")
    # User details
    user_name: Optional[str] = Field(None, description="User's name")
    user_email: Optional[str] = Field(None, description="User's email")

    class Config:
        from_attributes = True


class InstitutionMembersListResponse(BaseModel):
    """Response for listing institution members."""

    members: List[InstitutionMemberResponse]
    total: int
    by_department: dict[str, int] = Field(default_factory=dict, description="Member count by department")
    by_role: dict[str, int] = Field(default_factory=dict, description="Member count by role")


# ============================================================================
# Portfolio and Metrics Schemas
# ============================================================================


class GrantTrackedSummary(BaseModel):
    """Summary of a tracked grant in the portfolio."""

    grant_id: UUID
    title: str
    agency: Optional[str]
    deadline: Optional[datetime]
    amount_min: Optional[int]
    amount_max: Optional[int]
    stage: str  # researching, writing, submitted, awarded, rejected
    user_id: UUID
    user_name: Optional[str]
    department: Optional[str]


class PortfolioAggregation(BaseModel):
    """Aggregated portfolio view across institution members."""

    total_grants_tracked: int = Field(..., description="Total grants being tracked across all members")
    grants_by_stage: dict[str, int] = Field(..., description="Count of grants by pipeline stage")
    grants_by_department: dict[str, int] = Field(default_factory=dict, description="Count of grants by department")
    total_potential_funding: int = Field(..., description="Sum of max amounts for all tracked grants")
    upcoming_deadlines: List[GrantTrackedSummary] = Field(
        default_factory=list, description="Grants with upcoming deadlines"
    )
    recent_submissions: List[GrantTrackedSummary] = Field(default_factory=list, description="Recently submitted grants")
    recent_awards: List[GrantTrackedSummary] = Field(default_factory=list, description="Recent award wins")


class FundingPipelineMetric(BaseModel):
    """Metrics for the funding pipeline."""

    stage: str
    count: int
    total_potential: int
    avg_time_in_stage_days: Optional[float] = None


class DepartmentStats(BaseModel):
    """Statistics for a specific department."""

    department: str
    member_count: int
    grants_tracked: int
    grants_submitted: int
    grants_awarded: int
    success_rate: Optional[float] = Field(None, description="Percentage of submitted grants that were awarded")
    total_funding_received: int = Field(default=0, description="Total funding from awarded grants")


class InstitutionMetricsResponse(BaseModel):
    """Institution-wide metrics and benchmarks."""

    # Overview
    total_members: int
    total_grants_tracked: int
    total_grants_submitted: int
    total_grants_awarded: int
    total_funding_received: int

    # Success rates
    overall_success_rate: Optional[float] = Field(None, description="Institution-wide success rate")
    success_rate_by_funder: dict[str, float] = Field(default_factory=dict, description="Success rate by funding agency")
    success_rate_by_category: dict[str, float] = Field(
        default_factory=dict, description="Success rate by research category"
    )

    # Pipeline metrics
    pipeline_metrics: List[FundingPipelineMetric] = Field(
        default_factory=list, description="Metrics for each pipeline stage"
    )

    # Time-based metrics
    avg_days_to_submission: Optional[float] = Field(None, description="Average days from tracking to submission")
    avg_days_to_decision: Optional[float] = Field(None, description="Average days from submission to decision")

    # Trends
    monthly_submissions: dict[str, int] = Field(
        default_factory=dict, description="Submissions per month (YYYY-MM: count)"
    )
    monthly_awards: dict[str, int] = Field(default_factory=dict, description="Awards per month (YYYY-MM: count)")


class DepartmentListResponse(BaseModel):
    """Response for listing departments with stats."""

    departments: List[DepartmentStats]
    total_departments: int


class DeadlineSummary(BaseModel):
    """Summary of an upcoming deadline."""

    deadline_id: Optional[UUID] = None
    grant_id: Optional[UUID] = None
    application_id: Optional[UUID] = None
    title: str
    agency: Optional[str] = None
    deadline_date: datetime
    days_until_deadline: int
    status: str
    user_id: UUID
    user_name: Optional[str] = None
    department: Optional[str] = None
    priority: str = "medium"


class InstitutionDeadlinesResponse(BaseModel):
    """All upcoming deadlines across institution members."""

    deadlines: List[DeadlineSummary]
    total: int
    overdue_count: int
    due_this_week: int
    due_this_month: int


# ============================================================================
# Benchmark Schemas
# ============================================================================


class BenchmarkComparison(BaseModel):
    """Comparison between individual/department and institution average."""

    metric_name: str
    individual_value: float
    institution_average: float
    percentile: Optional[float] = Field(None, description="Percentile rank within institution")
    difference: float = Field(..., description="Difference from institution average")


class BenchmarkReport(BaseModel):
    """Benchmarking report for a member or department."""

    entity_type: str = Field(..., description="'member' or 'department'")
    entity_id: str
    entity_name: str
    comparisons: List[BenchmarkComparison]
    overall_performance_score: Optional[float] = Field(None, description="Composite performance score (0-100)")
    recommendations: List[str] = Field(default_factory=list, description="AI-generated improvement recommendations")


# ============================================================================
# List Response Schemas
# ============================================================================


class InstitutionsListResponse(BaseModel):
    """Response for listing institutions."""

    institutions: List[InstitutionResponse]
    total: int
