"""Add team collaboration tables for grant assignments, comments, and notifications.

Add grant_assignments, team_comments, and team_notifications tables to support
shared grant tracking, assignment, and coordination within teams.

Revision ID: 036
Revises: 033
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "036"
down_revision: Union[str, None] = "035"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Grant Assignments table - track who is assigned to work on grants
    if "grant_assignments" not in existing_tables:
        op.create_table(
            "grant_assignments",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "match_id",
                UUID(as_uuid=True),
                sa.ForeignKey("matches.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "grant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("grants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "assigned_to",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "assigned_by",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "lab_owner_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "role",
                sa.String(30),
                nullable=False,
                server_default="contributor",
            ),
            sa.Column(
                "status",
                sa.String(30),
                nullable=False,
                server_default="active",
            ),
            sa.Column(
                "due_date",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "notes",
                sa.Text(),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes for grant_assignments
        op.create_index(
            "ix_grant_assignments_match_id",
            "grant_assignments",
            ["match_id"],
        )
        op.create_index(
            "ix_grant_assignments_grant_id",
            "grant_assignments",
            ["grant_id"],
        )
        op.create_index(
            "ix_grant_assignments_assigned_to",
            "grant_assignments",
            ["assigned_to"],
        )
        op.create_index(
            "ix_grant_assignments_lab_owner_id",
            "grant_assignments",
            ["lab_owner_id"],
        )
        op.create_index(
            "ix_grant_assignments_status",
            "grant_assignments",
            ["status"],
        )
        op.create_index(
            "ix_grant_assignments_due_date",
            "grant_assignments",
            ["due_date"],
        )
        # Unique constraint to prevent duplicate assignments
        op.create_unique_constraint(
            "uq_grant_assignment_user_grant",
            "grant_assignments",
            ["assigned_to", "grant_id", "lab_owner_id"],
        )

    # Team Comments table - threaded comments on grants
    if "team_comments" not in existing_tables:
        op.create_table(
            "team_comments",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "match_id",
                UUID(as_uuid=True),
                sa.ForeignKey("matches.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "grant_id",
                UUID(as_uuid=True),
                sa.ForeignKey("grants.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "lab_owner_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "comment_text",
                sa.Text(),
                nullable=False,
            ),
            sa.Column(
                "parent_id",
                UUID(as_uuid=True),
                sa.ForeignKey("team_comments.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "mentions",
                JSONB(),
                nullable=True,
            ),
            sa.Column(
                "is_edited",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                onupdate=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes for team_comments
        op.create_index(
            "ix_team_comments_match_id",
            "team_comments",
            ["match_id"],
        )
        op.create_index(
            "ix_team_comments_grant_id",
            "team_comments",
            ["grant_id"],
        )
        op.create_index(
            "ix_team_comments_user_id",
            "team_comments",
            ["user_id"],
        )
        op.create_index(
            "ix_team_comments_lab_owner_id",
            "team_comments",
            ["lab_owner_id"],
        )
        op.create_index(
            "ix_team_comments_parent_id",
            "team_comments",
            ["parent_id"],
        )
        op.create_index(
            "ix_team_comments_created_at",
            "team_comments",
            ["created_at"],
        )

    # Team Notifications table - notifications for team collaboration events
    if "team_notifications" not in existing_tables:
        op.create_table(
            "team_notifications",
            sa.Column(
                "id",
                UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "user_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "team_id",
                UUID(as_uuid=True),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "notification_type",
                sa.String(50),
                nullable=False,
            ),
            sa.Column(
                "message",
                sa.Text(),
                nullable=False,
            ),
            sa.Column(
                "entity_type",
                sa.String(30),
                nullable=True,
            ),
            sa.Column(
                "entity_id",
                UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                "metadata",
                JSONB(),
                nullable=True,
            ),
            sa.Column(
                "is_read",
                sa.Boolean(),
                server_default="false",
                nullable=False,
            ),
            sa.Column(
                "read_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.func.now(),
                nullable=False,
            ),
        )

        # Create indexes for team_notifications
        op.create_index(
            "ix_team_notifications_user_id",
            "team_notifications",
            ["user_id"],
        )
        op.create_index(
            "ix_team_notifications_team_id",
            "team_notifications",
            ["team_id"],
        )
        op.create_index(
            "ix_team_notifications_notification_type",
            "team_notifications",
            ["notification_type"],
        )
        op.create_index(
            "ix_team_notifications_is_read",
            "team_notifications",
            ["is_read"],
        )
        op.create_index(
            "ix_team_notifications_user_read",
            "team_notifications",
            ["user_id", "is_read"],
        )
        op.create_index(
            "ix_team_notifications_created_at",
            "team_notifications",
            ["created_at"],
        )


def downgrade() -> None:
    # Drop team_notifications table and indexes
    op.drop_index("ix_team_notifications_created_at", table_name="team_notifications")
    op.drop_index("ix_team_notifications_user_read", table_name="team_notifications")
    op.drop_index("ix_team_notifications_is_read", table_name="team_notifications")
    op.drop_index("ix_team_notifications_notification_type", table_name="team_notifications")
    op.drop_index("ix_team_notifications_team_id", table_name="team_notifications")
    op.drop_index("ix_team_notifications_user_id", table_name="team_notifications")
    op.drop_table("team_notifications")

    # Drop team_comments table and indexes
    op.drop_index("ix_team_comments_created_at", table_name="team_comments")
    op.drop_index("ix_team_comments_parent_id", table_name="team_comments")
    op.drop_index("ix_team_comments_lab_owner_id", table_name="team_comments")
    op.drop_index("ix_team_comments_user_id", table_name="team_comments")
    op.drop_index("ix_team_comments_grant_id", table_name="team_comments")
    op.drop_index("ix_team_comments_match_id", table_name="team_comments")
    op.drop_table("team_comments")

    # Drop grant_assignments table and indexes
    op.drop_constraint("uq_grant_assignment_user_grant", "grant_assignments", type_="unique")
    op.drop_index("ix_grant_assignments_due_date", table_name="grant_assignments")
    op.drop_index("ix_grant_assignments_status", table_name="grant_assignments")
    op.drop_index("ix_grant_assignments_lab_owner_id", table_name="grant_assignments")
    op.drop_index("ix_grant_assignments_assigned_to", table_name="grant_assignments")
    op.drop_index("ix_grant_assignments_grant_id", table_name="grant_assignments")
    op.drop_index("ix_grant_assignments_match_id", table_name="grant_assignments")
    op.drop_table("grant_assignments")
