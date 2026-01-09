"""Add global audit logging table.

Comprehensive audit logging for tracking all system actions including
user activity, data changes, and system events for security and compliance.

Revision ID: 037
Revises: 036
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "037"
down_revision: Union[str, None] = "036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Audit logs table - comprehensive action tracking
    if "audit_logs" not in existing_tables:
        op.create_table(
            "audit_logs",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "timestamp",
                sa.TIMESTAMP(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "action",
                sa.String(50),
                nullable=False,
            ),
            sa.Column(
                "resource_type",
                sa.String(50),
                nullable=False,
            ),
            sa.Column(
                "resource_id",
                UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                "old_values",
                JSONB,
                nullable=True,
            ),
            sa.Column(
                "new_values",
                JSONB,
                nullable=True,
            ),
            sa.Column(
                "ip_address",
                sa.String(45),
                nullable=True,
            ),
            sa.Column(
                "user_agent",
                sa.String(500),
                nullable=True,
            ),
            sa.Column(
                "extra_data",
                JSONB,
                nullable=True,
            ),
            sa.Column(
                "success",
                sa.Boolean,
                nullable=False,
                server_default=sa.text("true"),
            ),
            sa.Column(
                "error_message",
                sa.Text,
                nullable=True,
            ),
            sa.Column(
                "request_id",
                sa.String(100),
                nullable=True,
            ),
            sa.Column(
                "duration_ms",
                sa.Integer,
                nullable=True,
            ),
        )

        # Create indexes for common query patterns
        op.create_index(
            "ix_audit_logs_timestamp",
            "audit_logs",
            ["timestamp"],
        )
        op.create_index(
            "ix_audit_logs_user_id",
            "audit_logs",
            ["user_id"],
        )
        op.create_index(
            "ix_audit_logs_action",
            "audit_logs",
            ["action"],
        )
        op.create_index(
            "ix_audit_logs_resource_type",
            "audit_logs",
            ["resource_type"],
        )
        op.create_index(
            "ix_audit_logs_resource_id",
            "audit_logs",
            ["resource_id"],
        )
        op.create_index(
            "ix_audit_logs_request_id",
            "audit_logs",
            ["request_id"],
        )

        # Composite indexes for common query patterns
        op.create_index(
            "ix_audit_logs_user_timestamp",
            "audit_logs",
            ["user_id", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_resource_type_timestamp",
            "audit_logs",
            ["resource_type", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_action_timestamp",
            "audit_logs",
            ["action", "timestamp"],
        )
        op.create_index(
            "ix_audit_logs_resource_type_resource_id",
            "audit_logs",
            ["resource_type", "resource_id"],
        )
        op.create_index(
            "ix_audit_logs_success_timestamp",
            "audit_logs",
            ["success", "timestamp"],
        )


def downgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    if "audit_logs" in existing_tables:
        # Drop indexes first
        op.drop_index("ix_audit_logs_success_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_resource_type_resource_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_action_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_resource_type_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_user_timestamp", table_name="audit_logs")
        op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_resource_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
        op.drop_index("ix_audit_logs_action", table_name="audit_logs")
        op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
        op.drop_index("ix_audit_logs_timestamp", table_name="audit_logs")
        # Drop table
        op.drop_table("audit_logs")
