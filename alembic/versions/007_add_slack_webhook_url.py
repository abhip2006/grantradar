"""Add slack_webhook_url to users table.

Revision ID: 007
Revises: 006
Create Date: 2025-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add slack_webhook_url column to users table."""
    op.add_column(
        "users",
        sa.Column(
            "slack_webhook_url",
            sa.Text(),
            nullable=True,
            comment="Slack incoming webhook URL for notifications",
        ),
    )


def downgrade() -> None:
    """Remove slack_webhook_url column from users table."""
    op.drop_column("users", "slack_webhook_url")
