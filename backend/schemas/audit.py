"""
Audit Logging Schemas
Pydantic models for audit log API requests and responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AuditAction(str, Enum):
    """Enum for audit action types."""

    # CRUD Operations
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"

    # Authentication
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    LOGIN_FAILED = "LOGIN_FAILED"
    PASSWORD_RESET = "PASSWORD_RESET"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    TOKEN_REFRESH = "TOKEN_REFRESH"

    # Access Control
    PERMISSION_GRANT = "PERMISSION_GRANT"
    PERMISSION_REVOKE = "PERMISSION_REVOKE"
    ROLE_CHANGE = "ROLE_CHANGE"

    # Export/Import
    EXPORT = "EXPORT"
    IMPORT = "IMPORT"
    BULK_OPERATION = "BULK_OPERATION"

    # System Events
    SYSTEM_CONFIG = "SYSTEM_CONFIG"
    API_ACCESS = "API_ACCESS"
    RATE_LIMIT = "RATE_LIMIT"


class AuditResourceType(str, Enum):
    """Enum for audit resource types."""

    # Core Resources
    USER = "user"
    GRANT = "grant"
    APPLICATION = "application"
    MATCH = "match"

    # Team Resources
    TEAM = "team"
    LAB_MEMBER = "lab_member"
    LAB_PROFILE = "lab_profile"

    # Grant Pipeline
    DEADLINE = "deadline"
    SAVED_SEARCH = "saved_search"
    TEMPLATE = "template"

    # Collaboration
    COMMENT = "comment"
    ASSIGNMENT = "assignment"
    NOTIFICATION = "notification"

    # Settings & Config
    CALENDAR_INTEGRATION = "calendar_integration"
    PERMISSION_TEMPLATE = "permission_template"
    ALERT_PREFERENCE = "alert_preference"

    # AI/Chat
    CHAT_SESSION = "chat_session"
    RESEARCH_SESSION = "research_session"

    # System
    SYSTEM = "system"
    API = "api"
    AUTH = "auth"


class AuditLogBase(BaseModel):
    """Base schema for audit log entries."""

    action: str = Field(..., description="Type of action performed")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[UUID] = Field(None, description="ID of the affected resource")
    old_values: Optional[dict[str, Any]] = Field(None, description="Previous values before action")
    new_values: Optional[dict[str, Any]] = Field(None, description="New values after action")
    extra_data: Optional[dict[str, Any]] = Field(None, description="Additional context")
    success: bool = Field(True, description="Whether action succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")


class AuditLogCreate(AuditLogBase):
    """Schema for creating audit log entries."""

    user_id: Optional[UUID] = Field(None, description="User who performed the action")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    duration_ms: Optional[int] = Field(None, description="Action duration in milliseconds")


class AuditLogResponse(AuditLogBase):
    """Schema for audit log response."""

    id: UUID = Field(..., description="Audit log entry ID")
    timestamp: datetime = Field(..., description="When the action occurred")
    user_id: Optional[UUID] = Field(None, description="User who performed the action")
    user_email: Optional[str] = Field(None, description="Email of the user")
    user_name: Optional[str] = Field(None, description="Name of the user")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    request_id: Optional[str] = Field(None, description="Request correlation ID")
    duration_ms: Optional[int] = Field(None, description="Action duration in milliseconds")

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    """Schema for paginated audit log list response."""

    items: list[AuditLogResponse] = Field(..., description="List of audit log entries")
    total: int = Field(..., description="Total number of matching entries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    total_pages: int = Field(..., description="Total number of pages")


class AuditLogFilters(BaseModel):
    """Schema for audit log query filters."""

    user_id: Optional[UUID] = Field(None, description="Filter by user ID")
    action: Optional[str] = Field(None, description="Filter by action type")
    actions: Optional[list[str]] = Field(None, description="Filter by multiple action types")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_types: Optional[list[str]] = Field(None, description="Filter by multiple resource types")
    resource_id: Optional[UUID] = Field(None, description="Filter by resource ID")
    success: Optional[bool] = Field(None, description="Filter by success status")
    start_date: Optional[datetime] = Field(None, description="Filter from this date")
    end_date: Optional[datetime] = Field(None, description="Filter until this date")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    search_query: Optional[str] = Field(None, description="Search in metadata and error messages")
    request_id: Optional[str] = Field(None, description="Filter by request ID")


class UserActivitySummary(BaseModel):
    """Schema for user activity summary."""

    user_id: UUID = Field(..., description="User ID")
    user_email: Optional[str] = Field(None, description="User email")
    user_name: Optional[str] = Field(None, description="User name")
    total_actions: int = Field(..., description="Total number of actions")
    successful_actions: int = Field(..., description="Number of successful actions")
    failed_actions: int = Field(..., description="Number of failed actions")
    actions_by_type: dict[str, int] = Field(..., description="Count of actions by type")
    resources_by_type: dict[str, int] = Field(..., description="Count of resources by type")
    first_activity: datetime = Field(..., description="Timestamp of first activity")
    last_activity: datetime = Field(..., description="Timestamp of last activity")
    ip_addresses: list[str] = Field(..., description="Unique IP addresses used")


class ResourceHistory(BaseModel):
    """Schema for resource change history."""

    resource_type: str = Field(..., description="Type of resource")
    resource_id: UUID = Field(..., description="Resource ID")
    history: list[AuditLogResponse] = Field(..., description="Change history entries")
    total_changes: int = Field(..., description="Total number of changes")
    created_at: Optional[datetime] = Field(None, description="When resource was created")
    created_by: Optional[UUID] = Field(None, description="Who created the resource")
    last_modified_at: Optional[datetime] = Field(None, description="When last modified")
    last_modified_by: Optional[UUID] = Field(None, description="Who last modified")


class AuditExportFormat(str, Enum):
    """Enum for export formats."""

    CSV = "csv"
    JSON = "json"


class AuditExportRequest(BaseModel):
    """Schema for audit log export request."""

    format: AuditExportFormat = Field(AuditExportFormat.CSV, description="Export format")
    filters: Optional[AuditLogFilters] = Field(None, description="Filters to apply")
    include_details: bool = Field(True, description="Include old/new values and metadata")
    max_records: int = Field(10000, description="Maximum records to export", le=100000)


class AuditStats(BaseModel):
    """Schema for audit log statistics."""

    total_logs: int = Field(..., description="Total number of audit logs")
    logs_today: int = Field(..., description="Logs created today")
    logs_this_week: int = Field(..., description="Logs created this week")
    logs_this_month: int = Field(..., description="Logs created this month")
    actions_by_type: dict[str, int] = Field(..., description="Count by action type")
    resources_by_type: dict[str, int] = Field(..., description="Count by resource type")
    success_rate: float = Field(..., description="Percentage of successful actions")
    unique_users: int = Field(..., description="Number of unique users")
    unique_ips: int = Field(..., description="Number of unique IP addresses")
    average_duration_ms: Optional[float] = Field(None, description="Average action duration")
