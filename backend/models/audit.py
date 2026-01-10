"""
Global Audit Logging Model
Comprehensive audit logging for all system actions.
"""

import enum
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    String,
    TIMESTAMP,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models import Base, GUID, JSONB


class AuditAction(enum.Enum):
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


class AuditResourceType(enum.Enum):
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


class AuditLog(Base):
    """
    Global audit log for tracking all system actions.

    Provides comprehensive tracking of user actions, system events,
    and data changes for security, compliance, and debugging purposes.
    Unlike TeamActivityLog which focuses on team-specific actions,
    AuditLog captures all significant system events across the platform.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the audit log entry",
    )
    timestamp: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        index=True,
        doc="Timestamp when the action occurred",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="User who performed the action (null for system actions)",
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of action performed (CREATE, READ, UPDATE, DELETE, LOGIN, etc.)",
    )
    resource_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        doc="Type of resource affected (grant, user, team, application, etc.)",
    )
    resource_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        GUID(),
        nullable=True,
        index=True,
        doc="ID of the resource affected (if applicable)",
    )
    old_values: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        doc="Previous values before the action (for UPDATE actions)",
    )
    new_values: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        doc="New values after the action (for CREATE/UPDATE actions)",
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45),
        nullable=True,
        doc="IP address of the client (IPv4 or IPv6)",
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        doc="User agent string from the client request",
    )
    extra_data: Mapped[Optional[dict]] = mapped_column(
        JSONB(),
        nullable=True,
        doc="Additional context and metadata for the action",
    )
    success: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        doc="Whether the action completed successfully",
    )
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Error message if the action failed",
    )
    request_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        doc="Request ID for correlating related log entries",
    )
    duration_ms: Mapped[Optional[int]] = mapped_column(
        nullable=True,
        doc="Duration of the action in milliseconds",
    )

    # Relationships
    user = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="selectin",
        doc="User who performed the action",
    )

    # Composite indexes for common query patterns
    __table_args__ = (
        Index(
            "ix_audit_logs_user_timestamp",
            "user_id",
            "timestamp",
        ),
        Index(
            "ix_audit_logs_resource_type_timestamp",
            "resource_type",
            "timestamp",
        ),
        Index(
            "ix_audit_logs_action_timestamp",
            "action",
            "timestamp",
        ),
        Index(
            "ix_audit_logs_resource_type_resource_id",
            "resource_type",
            "resource_id",
        ),
        Index(
            "ix_audit_logs_success_timestamp",
            "success",
            "timestamp",
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog(id={self.id}, action='{self.action}', "
            f"resource_type='{self.resource_type}', success={self.success})>"
        )

    def to_dict(self) -> dict:
        """Convert audit log entry to dictionary."""
        return {
            "id": str(self.id),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": str(self.resource_id) if self.resource_id else None,
            "old_values": self.old_values,
            "new_values": self.new_values,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "extra_data": self.extra_data,
            "success": self.success,
            "error_message": self.error_message,
            "request_id": self.request_id,
            "duration_ms": self.duration_ms,
        }
