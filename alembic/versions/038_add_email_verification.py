"""Add email verification fields to users table

Revision ID: 038
Revises: 037
Create Date: 2026-01-08

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def index_exists(index_name: str, table_name: str) -> bool:
    """Check if an index exists on a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    indexes = inspector.get_indexes(table_name)
    return any(idx["name"] == index_name for idx in indexes)


def upgrade() -> None:
    """Add email verification columns to users table (idempotent)."""
    # Add email_verified boolean field (default False for existing users)
    if not column_exists('users', 'email_verified'):
        op.add_column(
            'users',
            sa.Column(
                'email_verified',
                sa.Boolean(),
                nullable=False,
                server_default=sa.text('false'),
            )
        )

    # Add email_verification_token_hash field (stores hashed token)
    if not column_exists('users', 'email_verification_token_hash'):
        op.add_column(
            'users',
            sa.Column(
                'email_verification_token_hash',
                sa.Text(),
                nullable=True,
            )
        )

    # Add email_verification_token_expires field
    if not column_exists('users', 'email_verification_token_expires'):
        op.add_column(
            'users',
            sa.Column(
                'email_verification_token_expires',
                sa.TIMESTAMP(timezone=True),
                nullable=True,
            )
        )

    # Create index on email_verification_token_hash for faster lookups
    if not index_exists('ix_users_email_verification_token_hash', 'users'):
        op.create_index(
            'ix_users_email_verification_token_hash',
            'users',
            ['email_verification_token_hash'],
            unique=False,
        )


def downgrade() -> None:
    """Remove email verification columns from users table."""
    op.drop_index('ix_users_email_verification_token_hash', table_name='users')
    op.drop_column('users', 'email_verification_token_expires')
    op.drop_column('users', 'email_verification_token_hash')
    op.drop_column('users', 'email_verified')
