"""Add internal review workflow tables.

Revision ID: 021
Revises: 020
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create review_workflows table
    op.create_table(
        "review_workflows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("stages", postgresql.JSONB, nullable=False),  # [{order, name, required_role, sla_hours, auto_escalate}]
        sa.Column("is_default", sa.Boolean, server_default="false", nullable=False),
        sa.Column("is_active", sa.Boolean, server_default="true", nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_workflows_user_id", "review_workflows", ["user_id"])
    op.create_index("ix_review_workflows_is_default", "review_workflows", ["is_default"])
    op.create_index("ix_review_workflows_is_active", "review_workflows", ["is_active"])

    # Create application_reviews table
    op.create_table(
        "application_reviews",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kanban_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("review_workflows.id", ondelete="SET NULL"), nullable=True),
        sa.Column("current_stage", sa.Integer, server_default="0", nullable=False),
        sa.Column("status", sa.String(50), server_default="pending", nullable=False),  # pending, in_review, approved, rejected, escalated
        sa.Column("started_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("stage_started_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("escalation_sent", sa.Boolean, server_default="false", nullable=False),
    )
    op.create_index("ix_application_reviews_kanban_card_id", "application_reviews", ["kanban_card_id"])
    op.create_index("ix_application_reviews_workflow_id", "application_reviews", ["workflow_id"])
    op.create_index("ix_application_reviews_status", "application_reviews", ["status"])
    op.create_index("ix_application_reviews_current_stage", "application_reviews", ["current_stage"])

    # Create review_stage_actions table
    op.create_table(
        "review_stage_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("review_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("application_reviews.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage_order", sa.Integer, nullable=False),
        sa.Column("stage_name", sa.String(100), nullable=False),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),  # approved, rejected, returned, commented
        sa.Column("comments", sa.Text, nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),  # Additional action metadata
        sa.Column("acted_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_review_stage_actions_review_id", "review_stage_actions", ["review_id"])
    op.create_index("ix_review_stage_actions_reviewer_id", "review_stage_actions", ["reviewer_id"])
    op.create_index("ix_review_stage_actions_stage_order", "review_stage_actions", ["stage_order"])
    op.create_index("ix_review_stage_actions_action", "review_stage_actions", ["action"])
    op.create_index("ix_review_stage_actions_acted_at", "review_stage_actions", ["acted_at"])

    # Create application_team_members table
    op.create_table(
        "application_team_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("kanban_card_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False),  # pi, co_i, grant_writer, reviewer, admin
        sa.Column("permissions", postgresql.JSONB, nullable=True),  # {can_edit, can_approve, can_submit, sections: [...]}
        sa.Column("added_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("added_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kanban_card_id", "user_id", name="uq_application_team_member"),
    )
    op.create_index("ix_application_team_members_kanban_card_id", "application_team_members", ["kanban_card_id"])
    op.create_index("ix_application_team_members_user_id", "application_team_members", ["user_id"])
    op.create_index("ix_application_team_members_role", "application_team_members", ["role"])


def downgrade() -> None:
    op.drop_index("ix_application_team_members_role", table_name="application_team_members")
    op.drop_index("ix_application_team_members_user_id", table_name="application_team_members")
    op.drop_index("ix_application_team_members_kanban_card_id", table_name="application_team_members")
    op.drop_table("application_team_members")

    op.drop_index("ix_review_stage_actions_acted_at", table_name="review_stage_actions")
    op.drop_index("ix_review_stage_actions_action", table_name="review_stage_actions")
    op.drop_index("ix_review_stage_actions_stage_order", table_name="review_stage_actions")
    op.drop_index("ix_review_stage_actions_reviewer_id", table_name="review_stage_actions")
    op.drop_index("ix_review_stage_actions_review_id", table_name="review_stage_actions")
    op.drop_table("review_stage_actions")

    op.drop_index("ix_application_reviews_current_stage", table_name="application_reviews")
    op.drop_index("ix_application_reviews_status", table_name="application_reviews")
    op.drop_index("ix_application_reviews_workflow_id", table_name="application_reviews")
    op.drop_index("ix_application_reviews_kanban_card_id", table_name="application_reviews")
    op.drop_table("application_reviews")

    op.drop_index("ix_review_workflows_is_active", table_name="review_workflows")
    op.drop_index("ix_review_workflows_is_default", table_name="review_workflows")
    op.drop_index("ix_review_workflows_user_id", table_name="review_workflows")
    op.drop_table("review_workflows")
