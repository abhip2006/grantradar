"""Add user notification preferences

Revision ID: 003
Revises: 002
Create Date: 2025-01-07

Adds notification preference columns to the users table:
- email_notifications: bool (default True)
- sms_notifications: bool (default False)
- slack_notifications: bool (default False)
- digest_frequency: str (immediate/daily/weekly, default 'immediate')
- minimum_match_score: float (default 0.7)
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# Revision identifiers
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add notification preference columns to users table."""

    # Add email_notifications column
    op.add_column(
        "users",
        sa.Column(
            "email_notifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )

    # Add sms_notifications column
    op.add_column(
        "users",
        sa.Column(
            "sms_notifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Add slack_notifications column
    op.add_column(
        "users",
        sa.Column(
            "slack_notifications",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )

    # Add digest_frequency column
    op.add_column(
        "users",
        sa.Column(
            "digest_frequency",
            sa.String(20),
            nullable=False,
            server_default="immediate",
        ),
    )

    # Add minimum_match_score column
    op.add_column(
        "users",
        sa.Column(
            "minimum_match_score",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.7"),
        ),
    )


def downgrade() -> None:
    """Remove notification preference columns from users table."""

    op.drop_column("users", "minimum_match_score")
    op.drop_column("users", "digest_frequency")
    op.drop_column("users", "slack_notifications")
    op.drop_column("users", "sms_notifications")
    op.drop_column("users", "email_notifications")
