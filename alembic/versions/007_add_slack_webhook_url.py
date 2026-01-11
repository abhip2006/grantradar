"""Add slack_webhook_url to users table.

Revision ID: 007
Revises: 006
Create Date: 2025-01-08
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add slack_webhook_url column to users table (idempotent)."""
    if not column_exists("users", "slack_webhook_url"):
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
