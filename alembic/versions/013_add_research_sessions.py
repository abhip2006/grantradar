"""Add research sessions and alert preferences tables.

Revision ID: 013
Revises: 012
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Research sessions table for Deep Research feature
    op.create_table(
        "research_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),  # pending, processing, completed, failed
        sa.Column("results", postgresql.JSONB(), nullable=True),
        sa.Column("insights", sa.Text(), nullable=True),  # AI-generated insights
        sa.Column("grants_found", sa.Integer(), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index("ix_research_sessions_user_id", "research_sessions", ["user_id"])
    op.create_index("ix_research_sessions_status", "research_sessions", ["status"])

    # Funding alert preferences table
    op.create_table(
        "funding_alert_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("frequency", sa.String(20), nullable=False, server_default="weekly"),  # daily, weekly, monthly
        sa.Column("min_match_score", sa.Integer(), nullable=False, server_default="70"),  # Minimum match score to include
        sa.Column("include_deadlines", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("include_new_grants", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("include_insights", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("preferred_funders", postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column("last_sent_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_funding_alert_preferences_user_id", "funding_alert_preferences", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_funding_alert_preferences_user_id", table_name="funding_alert_preferences")
    op.drop_table("funding_alert_preferences")
    op.drop_index("ix_research_sessions_status", table_name="research_sessions")
    op.drop_index("ix_research_sessions_user_id", table_name="research_sessions")
    op.drop_table("research_sessions")
