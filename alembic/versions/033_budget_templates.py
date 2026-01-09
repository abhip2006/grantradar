"""Add budget_templates and user_budgets tables

Revision ID: 033
Revises: 032
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '033'
down_revision: Union[str, None] = '032'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Budget Templates table - stores typical budget allocations per mechanism
    if 'budget_templates' not in existing_tables:
        op.create_table(
            'budget_templates',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('mechanism_code', sa.String(50), nullable=False),
            sa.Column('category', sa.String(50), nullable=False),
            sa.Column('typical_percentage', sa.Float(), nullable=True),
            sa.Column('typical_amount_min', sa.Integer(), nullable=True),
            sa.Column('typical_amount_max', sa.Integer(), nullable=True),
            sa.Column('is_required', sa.Boolean(), server_default='false', nullable=False),
            sa.Column('priority', sa.Integer(), server_default='0', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('validation_rules', JSONB(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint('mechanism_code', 'category', name='uq_budget_templates_mechanism_category'),
        )
        op.create_index('ix_budget_templates_mechanism_code', 'budget_templates', ['mechanism_code'])
        op.create_index('ix_budget_templates_category', 'budget_templates', ['category'])

    # User Budgets table - stores user budget drafts
    if 'user_budgets' not in existing_tables:
        op.create_table(
            'user_budgets',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('grant_id', UUID(as_uuid=True), sa.ForeignKey('grants.id', ondelete='SET NULL'), nullable=True),
            sa.Column('match_id', UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='SET NULL'), nullable=True),
            sa.Column('mechanism_code', sa.String(50), nullable=True),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('budget_data', JSONB(), nullable=False),
            sa.Column('total_direct_costs', sa.Integer(), nullable=True),
            sa.Column('total_indirect_costs', sa.Integer(), nullable=True),
            sa.Column('total_budget', sa.Integer(), nullable=True),
            sa.Column('duration_years', sa.Integer(), nullable=True),
            sa.Column('status', sa.String(20), server_default='draft', nullable=False),
            sa.Column('version', sa.Integer(), server_default='1', nullable=False),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_user_budgets_user_id', 'user_budgets', ['user_id'])
        op.create_index('ix_user_budgets_grant_id', 'user_budgets', ['grant_id'])
        op.create_index('ix_user_budgets_match_id', 'user_budgets', ['match_id'])
        op.create_index('ix_user_budgets_mechanism_code', 'user_budgets', ['mechanism_code'])
        op.create_index('ix_user_budgets_status', 'user_budgets', ['status'])


def downgrade() -> None:
    # Drop user_budgets table and indexes
    op.drop_index('ix_user_budgets_status', table_name='user_budgets')
    op.drop_index('ix_user_budgets_mechanism_code', table_name='user_budgets')
    op.drop_index('ix_user_budgets_match_id', table_name='user_budgets')
    op.drop_index('ix_user_budgets_grant_id', table_name='user_budgets')
    op.drop_index('ix_user_budgets_user_id', table_name='user_budgets')
    op.drop_table('user_budgets')

    # Drop budget_templates table and indexes
    op.drop_index('ix_budget_templates_category', table_name='budget_templates')
    op.drop_index('ix_budget_templates_mechanism_code', table_name='budget_templates')
    op.drop_table('budget_templates')
