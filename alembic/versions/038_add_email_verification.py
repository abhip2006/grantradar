"""Add email verification fields to users table

Revision ID: 038
Revises: 037
Create Date: 2026-01-08

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '038'
down_revision = '037'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add email verification columns to users table."""
    # Add email_verified boolean field (default False for existing users)
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
    op.add_column(
        'users',
        sa.Column(
            'email_verification_token_hash',
            sa.Text(),
            nullable=True,
        )
    )

    # Add email_verification_token_expires field
    op.add_column(
        'users',
        sa.Column(
            'email_verification_token_expires',
            sa.TIMESTAMP(timezone=True),
            nullable=True,
        )
    )

    # Create index on email_verification_token_hash for faster lookups
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
