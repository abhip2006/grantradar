"""Add calendar integration tables.

Revision ID: 009
Revises: 008
Create Date: 2025-01-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create calendar integration and reminder schedule tables."""
    # Create calendar_integrations table for OAuth token storage
    op.create_table(
        "calendar_integrations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "provider",
            sa.String(50),
            nullable=False,
            comment="Calendar provider: 'google' or 'outlook'",
        ),
        sa.Column(
            "access_token",
            sa.Text(),
            nullable=False,
            comment="Encrypted OAuth access token",
        ),
        sa.Column(
            "refresh_token",
            sa.Text(),
            nullable=True,
            comment="Encrypted OAuth refresh token",
        ),
        sa.Column(
            "token_expires_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When the access token expires",
        ),
        sa.Column(
            "calendar_id",
            sa.String(255),
            nullable=True,
            comment="External calendar ID from provider",
        ),
        sa.Column(
            "sync_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether calendar sync is enabled",
        ),
        sa.Column(
            "last_synced_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="Last successful sync timestamp",
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
            nullable=False,
        ),
    )

    # Create unique constraint on (user_id, provider)
    op.create_unique_constraint(
        "uq_calendar_integrations_user_provider",
        "calendar_integrations",
        ["user_id", "provider"],
    )

    # Create indexes for calendar_integrations
    op.create_index(
        "ix_calendar_integrations_user_id",
        "calendar_integrations",
        ["user_id"],
    )
    op.create_index(
        "ix_calendar_integrations_provider",
        "calendar_integrations",
        ["provider"],
    )

    # Create reminder_schedules table for deadline reminders
    op.create_table(
        "reminder_schedules",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "deadline_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("deadlines.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reminder_type",
            sa.String(30),
            nullable=False,
            comment="Reminder type: 'email', 'push', or 'sms'",
        ),
        sa.Column(
            "remind_before_minutes",
            sa.Integer(),
            nullable=False,
            comment="Minutes before deadline to send reminder (e.g., 1440 for 1 day)",
        ),
        sa.Column(
            "is_sent",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether the reminder has been sent",
        ),
        sa.Column(
            "sent_at",
            sa.TIMESTAMP(timezone=True),
            nullable=True,
            comment="When the reminder was sent",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create indexes for reminder_schedules
    op.create_index(
        "ix_reminder_schedules_deadline_id",
        "reminder_schedules",
        ["deadline_id"],
    )
    op.create_index(
        "ix_reminder_schedules_is_sent",
        "reminder_schedules",
        ["is_sent"],
    )
    op.create_index(
        "ix_reminder_schedules_reminder_type",
        "reminder_schedules",
        ["reminder_type"],
    )


def downgrade() -> None:
    """Remove calendar integration and reminder schedule tables."""
    # Drop reminder_schedules indexes and table
    op.drop_index("ix_reminder_schedules_reminder_type", table_name="reminder_schedules")
    op.drop_index("ix_reminder_schedules_is_sent", table_name="reminder_schedules")
    op.drop_index("ix_reminder_schedules_deadline_id", table_name="reminder_schedules")
    op.drop_table("reminder_schedules")

    # Drop calendar_integrations indexes, constraint, and table
    op.drop_index("ix_calendar_integrations_provider", table_name="calendar_integrations")
    op.drop_index("ix_calendar_integrations_user_id", table_name="calendar_integrations")
    op.drop_constraint(
        "uq_calendar_integrations_user_provider",
        "calendar_integrations",
        type_="unique",
    )
    op.drop_table("calendar_integrations")
