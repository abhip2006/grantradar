"""Add workflow analytics tables.

Revision ID: 023
Revises: 022
Create Date: 2025-01-08

Adds workflow_events and workflow_analytics tables for tracking
application workflow efficiency and generating insights.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create workflow_events table
    op.create_table(
        "workflow_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "kanban_card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("grant_applications.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("stage", sa.String(50), nullable=True),
        sa.Column("previous_stage", sa.String(50), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column(
            "occurred_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Add indexes for workflow_events
    op.create_index(
        "ix_workflow_events_kanban_card_id",
        "workflow_events",
        ["kanban_card_id"],
    )
    op.create_index(
        "ix_workflow_events_event_type",
        "workflow_events",
        ["event_type"],
    )
    op.create_index(
        "ix_workflow_events_stage",
        "workflow_events",
        ["stage"],
    )
    op.create_index(
        "ix_workflow_events_occurred_at",
        "workflow_events",
        [sa.text("occurred_at DESC")],
    )
    op.create_index(
        "ix_workflow_events_user_id",
        "workflow_events",
        ["user_id"],
    )

    # Create workflow_analytics table
    op.create_table(
        "workflow_analytics",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("period_type", sa.String(20), nullable=False, server_default="weekly"),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column(
            "generated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Add indexes for workflow_analytics
    op.create_index(
        "ix_workflow_analytics_user_id",
        "workflow_analytics",
        ["user_id"],
    )
    op.create_index(
        "ix_workflow_analytics_period",
        "workflow_analytics",
        ["period_start", "period_end"],
    )
    op.create_index(
        "ix_workflow_analytics_period_type",
        "workflow_analytics",
        ["period_type"],
    )
    op.create_index(
        "ix_workflow_analytics_generated_at",
        "workflow_analytics",
        [sa.text("generated_at DESC")],
    )

    # Add unique constraint for user + period combination
    op.create_unique_constraint(
        "uq_workflow_analytics_user_period",
        "workflow_analytics",
        ["user_id", "period_start", "period_end", "period_type"],
    )


def downgrade() -> None:
    # Drop workflow_analytics table and indexes
    op.drop_constraint(
        "uq_workflow_analytics_user_period",
        "workflow_analytics",
        type_="unique",
    )
    op.drop_index("ix_workflow_analytics_generated_at", table_name="workflow_analytics")
    op.drop_index("ix_workflow_analytics_period_type", table_name="workflow_analytics")
    op.drop_index("ix_workflow_analytics_period", table_name="workflow_analytics")
    op.drop_index("ix_workflow_analytics_user_id", table_name="workflow_analytics")
    op.drop_table("workflow_analytics")

    # Drop workflow_events table and indexes
    op.drop_index("ix_workflow_events_user_id", table_name="workflow_events")
    op.drop_index("ix_workflow_events_occurred_at", table_name="workflow_events")
    op.drop_index("ix_workflow_events_stage", table_name="workflow_events")
    op.drop_index("ix_workflow_events_event_type", table_name="workflow_events")
    op.drop_index("ix_workflow_events_kanban_card_id", table_name="workflow_events")
    op.drop_table("workflow_events")
