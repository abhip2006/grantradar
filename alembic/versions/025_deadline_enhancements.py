"""Add deadline enhancements: recurring support, status history, reminder config

Revision ID: 025
Revises: 024
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add deadline enhancements (idempotent)."""
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Add new columns to deadlines table
    if not column_exists("deadlines", "is_recurring"):
        op.add_column(
            "deadlines",
            sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"),
        )
    if not column_exists("deadlines", "recurrence_rule"):
        op.add_column(
            "deadlines",
            sa.Column("recurrence_rule", sa.String(255), nullable=True),
        )
    if not column_exists("deadlines", "parent_deadline_id"):
        op.add_column(
            "deadlines",
            sa.Column(
                "parent_deadline_id",
                sa.CHAR(32) if dialect == "sqlite" else postgresql.UUID(as_uuid=True),
                sa.ForeignKey("deadlines.id", ondelete="CASCADE"),
                nullable=True,
            ),
        )
    if not column_exists("deadlines", "reminder_config"):
        op.add_column(
            "deadlines",
            sa.Column(
                "reminder_config",
                sa.JSON() if dialect == "sqlite" else postgresql.JSONB(),
                nullable=True,
                server_default='[30, 14, 7, 3, 1]',
            ),
        )
    if not column_exists("deadlines", "escalation_sent"):
        op.add_column(
            "deadlines",
            sa.Column("escalation_sent", sa.Boolean(), nullable=False, server_default="false"),
        )

    # Create indexes for recurring deadlines
    if not index_exists("ix_deadlines_parent_id", "deadlines"):
        op.create_index("ix_deadlines_parent_id", "deadlines", ["parent_deadline_id"])
    if not index_exists("ix_deadlines_is_recurring", "deadlines"):
        op.create_index("ix_deadlines_is_recurring", "deadlines", ["is_recurring"])

    # Create deadline_status_history table
    if not table_exists("deadline_status_history"):
        op.create_table(
            "deadline_status_history",
            sa.Column(
                "id",
                sa.CHAR(32) if dialect == "sqlite" else postgresql.UUID(as_uuid=True),
                primary_key=True,
            ),
            sa.Column(
                "deadline_id",
                sa.CHAR(32) if dialect == "sqlite" else postgresql.UUID(as_uuid=True),
                sa.ForeignKey("deadlines.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("previous_status", sa.String(30), nullable=True),
            sa.Column("new_status", sa.String(30), nullable=False),
            sa.Column(
                "changed_by",
                sa.CHAR(32) if dialect == "sqlite" else postgresql.UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "changed_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column("notes", sa.Text(), nullable=True),
        )
        op.create_index(
            "ix_deadline_status_history_deadline_id",
            "deadline_status_history",
            ["deadline_id"],
        )
        op.create_index(
            "ix_deadline_status_history_changed_at",
            "deadline_status_history",
            ["changed_at"],
        )

    # Migrate existing statuses (only run once, checking if old values exist)
    try:
        op.execute("UPDATE deadlines SET status = 'not_started' WHERE status = 'active'")
        op.execute("UPDATE deadlines SET status = 'awarded' WHERE status = 'completed'")
        op.execute("UPDATE deadlines SET status = 'rejected' WHERE status = 'archived'")
    except Exception:
        pass  # Ignore if already migrated


def downgrade() -> None:
    op.drop_index("ix_deadline_status_history_changed_at", "deadline_status_history")
    op.drop_index("ix_deadline_status_history_deadline_id", "deadline_status_history")
    op.drop_table("deadline_status_history")

    op.drop_index("ix_deadlines_is_recurring", "deadlines")
    op.drop_index("ix_deadlines_parent_id", "deadlines")

    op.drop_column("deadlines", "escalation_sent")
    op.drop_column("deadlines", "reminder_config")
    op.drop_column("deadlines", "parent_deadline_id")
    op.drop_column("deadlines", "recurrence_rule")
    op.drop_column("deadlines", "is_recurring")

    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'not_started'")
    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'drafting'")
    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'internal_review'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'submitted'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'under_review'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'awarded'")
    op.execute("UPDATE deadlines SET status = 'archived' WHERE status = 'rejected'")
