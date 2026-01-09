"""Add deadline enhancements: recurring support, status history, reminder config

Revision ID: 025
Revises: 024
Create Date: 2026-01-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Determine dialect for type compatibility
    bind = op.get_bind()
    dialect = bind.dialect.name

    # Add new columns to deadlines table
    op.add_column(
        "deadlines",
        sa.Column("is_recurring", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "deadlines",
        sa.Column("recurrence_rule", sa.String(255), nullable=True),
    )
    op.add_column(
        "deadlines",
        sa.Column(
            "parent_deadline_id",
            sa.CHAR(32) if dialect == "sqlite" else postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deadlines.id", ondelete="CASCADE"),
            nullable=True,
        ),
    )
    op.add_column(
        "deadlines",
        sa.Column(
            "reminder_config",
            sa.JSON() if dialect == "sqlite" else postgresql.JSONB(),
            nullable=True,
            server_default='[30, 14, 7, 3, 1]',
        ),
    )
    op.add_column(
        "deadlines",
        sa.Column("escalation_sent", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Create indexes for recurring deadlines
    op.create_index("ix_deadlines_parent_id", "deadlines", ["parent_deadline_id"])
    op.create_index("ix_deadlines_is_recurring", "deadlines", ["is_recurring"])

    # Create deadline_status_history table
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

    # Create indexes for status history
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

    # Migrate existing 'active' status to 'not_started'
    op.execute("UPDATE deadlines SET status = 'not_started' WHERE status = 'active'")
    # Migrate 'completed' to 'awarded' (closest equivalent)
    op.execute("UPDATE deadlines SET status = 'awarded' WHERE status = 'completed'")
    # Migrate 'archived' to 'rejected' (closest equivalent for finished but not won)
    op.execute("UPDATE deadlines SET status = 'rejected' WHERE status = 'archived'")


def downgrade() -> None:
    # Drop status history table
    op.drop_index("ix_deadline_status_history_changed_at", "deadline_status_history")
    op.drop_index("ix_deadline_status_history_deadline_id", "deadline_status_history")
    op.drop_table("deadline_status_history")

    # Drop indexes
    op.drop_index("ix_deadlines_is_recurring", "deadlines")
    op.drop_index("ix_deadlines_parent_id", "deadlines")

    # Remove columns from deadlines
    op.drop_column("deadlines", "escalation_sent")
    op.drop_column("deadlines", "reminder_config")
    op.drop_column("deadlines", "parent_deadline_id")
    op.drop_column("deadlines", "recurrence_rule")
    op.drop_column("deadlines", "is_recurring")

    # Migrate statuses back
    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'not_started'")
    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'drafting'")
    op.execute("UPDATE deadlines SET status = 'active' WHERE status = 'internal_review'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'submitted'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'under_review'")
    op.execute("UPDATE deadlines SET status = 'completed' WHERE status = 'awarded'")
    op.execute("UPDATE deadlines SET status = 'archived' WHERE status = 'rejected'")
