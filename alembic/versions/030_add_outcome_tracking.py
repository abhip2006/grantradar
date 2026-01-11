"""Add outcome tracking columns to matches table

Revision ID: 030_outcome_tracking
Revises: 029_user_profile_eligibility
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

revision: str = '030'
down_revision: Union[str, None] = '029'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    bind = op.get_bind()
    inspector = inspect(bind)
    columns = [col["name"] for col in inspector.get_columns(table_name)]
    return column_name in columns


def upgrade() -> None:
    """Add outcome tracking columns (idempotent)."""
    # Add outcome tracking columns to matches table
    if not column_exists('matches', 'application_status'):
        op.add_column('matches', sa.Column('application_status', sa.Text(), nullable=True))
    if not column_exists('matches', 'application_submitted_at'):
        op.add_column('matches', sa.Column('application_submitted_at', sa.TIMESTAMP(timezone=True), nullable=True))
    if not column_exists('matches', 'outcome_received_at'):
        op.add_column('matches', sa.Column('outcome_received_at', sa.TIMESTAMP(timezone=True), nullable=True))
    if not column_exists('matches', 'award_amount'):
        op.add_column('matches', sa.Column('award_amount', sa.Integer(), nullable=True))
    if not column_exists('matches', 'outcome_notes'):
        op.add_column('matches', sa.Column('outcome_notes', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('matches', 'outcome_notes')
    op.drop_column('matches', 'award_amount')
    op.drop_column('matches', 'outcome_received_at')
    op.drop_column('matches', 'application_submitted_at')
    op.drop_column('matches', 'application_status')
