"""Add team collaboration features.

Add invitation tracking and team activity logging for collaboration.

Revision ID: 027
Revises: 026
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "027"
down_revision: Union[str, None] = "026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add invitation tracking columns to lab_members table
    op.add_column(
        "lab_members",
        sa.Column("invitation_token", sa.String(64), unique=True, nullable=True)
    )
    op.add_column(
        "lab_members",
        sa.Column("invitation_expires_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "lab_members",
        sa.Column("invitation_status", sa.String(20), server_default="pending", nullable=False)
    )
    op.add_column(
        "lab_members",
        sa.Column("declined_at", sa.TIMESTAMP(timezone=True), nullable=True)
    )
    op.add_column(
        "lab_members",
        sa.Column(
            "permissions",
            postgresql.JSONB,
            server_default='{"can_view": true, "can_edit": false, "can_create": false, "can_delete": false, "can_invite": false}',
            nullable=True
        )
    )

    # Create indexes for invitation fields
    op.create_index(
        "ix_lab_members_invitation_token",
        "lab_members",
        ["invitation_token"],
        unique=True
    )
    op.create_index(
        "ix_lab_members_invitation_status",
        "lab_members",
        ["invitation_status"]
    )

    # Create team_activity_log table for audit trail
    op.create_table(
        "team_activity_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()")
        ),
        sa.Column(
            "lab_owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False
        ),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True
        ),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column("entity_type", sa.String(30), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("entity_name", sa.String(500), nullable=True),
        sa.Column("metadata", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False
        ),
    )

    # Create indexes for team_activity_log
    op.create_index(
        "ix_team_activity_log_lab_owner_id",
        "team_activity_log",
        ["lab_owner_id"]
    )
    op.create_index(
        "ix_team_activity_log_created_at",
        "team_activity_log",
        ["created_at"]
    )
    op.create_index(
        "ix_team_activity_log_action_type",
        "team_activity_log",
        ["action_type"]
    )
    op.create_index(
        "ix_team_activity_log_entity_type",
        "team_activity_log",
        ["entity_type"]
    )


def downgrade() -> None:
    # Drop team_activity_log table and indexes
    op.drop_index("ix_team_activity_log_entity_type", table_name="team_activity_log")
    op.drop_index("ix_team_activity_log_action_type", table_name="team_activity_log")
    op.drop_index("ix_team_activity_log_created_at", table_name="team_activity_log")
    op.drop_index("ix_team_activity_log_lab_owner_id", table_name="team_activity_log")
    op.drop_table("team_activity_log")

    # Drop indexes from lab_members
    op.drop_index("ix_lab_members_invitation_status", table_name="lab_members")
    op.drop_index("ix_lab_members_invitation_token", table_name="lab_members")

    # Drop columns from lab_members
    op.drop_column("lab_members", "permissions")
    op.drop_column("lab_members", "declined_at")
    op.drop_column("lab_members", "invitation_status")
    op.drop_column("lab_members", "invitation_expires_at")
    op.drop_column("lab_members", "invitation_token")
