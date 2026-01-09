"""Add compliance engine tables for funder requirements tracking

Revision ID: 035
Revises: 033
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '035'
down_revision: Union[str, None] = '034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Funder Requirements table - stores compliance requirements by funder
    if 'funder_requirements' not in existing_tables:
        op.create_table(
            'funder_requirements',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('funder_name', sa.String(255), nullable=False),
            sa.Column('requirement_type', sa.String(50), nullable=False),  # reporting, financial, ethical, data_management
            sa.Column('requirement_text', sa.Text(), nullable=False),
            sa.Column('frequency', sa.String(30), nullable=False),  # one_time, quarterly, annual, final
            sa.Column('deadline_offset_days', sa.Integer(), nullable=True),  # days after award start/anniversary
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('mechanism', sa.String(50), nullable=True),  # Optional: specific mechanism (R01, R21, etc.)
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_funder_requirements_funder_name', 'funder_requirements', ['funder_name'])
        op.create_index('ix_funder_requirements_requirement_type', 'funder_requirements', ['requirement_type'])
        op.create_index('ix_funder_requirements_frequency', 'funder_requirements', ['frequency'])
        op.create_index('ix_funder_requirements_is_active', 'funder_requirements', ['is_active'])
        op.create_index('ix_funder_requirements_mechanism', 'funder_requirements', ['mechanism'])

    # Compliance Tasks table - tracks user's compliance tasks
    if 'compliance_tasks' not in existing_tables:
        op.create_table(
            'compliance_tasks',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('match_id', UUID(as_uuid=True), sa.ForeignKey('matches.id', ondelete='SET NULL'), nullable=True),
            sa.Column('grant_id', UUID(as_uuid=True), sa.ForeignKey('grants.id', ondelete='SET NULL'), nullable=True),
            sa.Column('application_id', UUID(as_uuid=True), sa.ForeignKey('grant_applications.id', ondelete='SET NULL'), nullable=True),
            sa.Column('requirement_id', UUID(as_uuid=True), sa.ForeignKey('funder_requirements.id', ondelete='SET NULL'), nullable=True),
            sa.Column('title', sa.String(500), nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('due_date', sa.TIMESTAMP(timezone=True), nullable=False),
            sa.Column('status', sa.String(30), server_default='pending', nullable=False),  # pending, in_progress, completed, overdue
            sa.Column('completed_at', sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('completed_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('notes', sa.Text(), nullable=True),
            sa.Column('reminder_sent_at', sa.TIMESTAMP(timezone=True), nullable=True),
            sa.Column('award_date', sa.TIMESTAMP(timezone=True), nullable=True),  # Award start date for calculating recurring deadlines
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_compliance_tasks_user_id', 'compliance_tasks', ['user_id'])
        op.create_index('ix_compliance_tasks_match_id', 'compliance_tasks', ['match_id'])
        op.create_index('ix_compliance_tasks_grant_id', 'compliance_tasks', ['grant_id'])
        op.create_index('ix_compliance_tasks_application_id', 'compliance_tasks', ['application_id'])
        op.create_index('ix_compliance_tasks_requirement_id', 'compliance_tasks', ['requirement_id'])
        op.create_index('ix_compliance_tasks_due_date', 'compliance_tasks', ['due_date'])
        op.create_index('ix_compliance_tasks_status', 'compliance_tasks', ['status'])
        op.create_index('ix_compliance_tasks_user_status', 'compliance_tasks', ['user_id', 'status'])

    # Compliance Templates table - stores document templates for compliance reports
    if 'compliance_templates' not in existing_tables:
        op.create_table(
            'compliance_templates',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('funder_name', sa.String(255), nullable=False),
            sa.Column('mechanism', sa.String(50), nullable=True),
            sa.Column('template_name', sa.String(255), nullable=False),
            sa.Column('template_type', sa.String(50), nullable=False),  # progress_report, financial_report, data_plan
            sa.Column('template_content', JSONB(), nullable=False),  # Template structure/fields
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_compliance_templates_funder_name', 'compliance_templates', ['funder_name'])
        op.create_index('ix_compliance_templates_mechanism', 'compliance_templates', ['mechanism'])
        op.create_index('ix_compliance_templates_template_type', 'compliance_templates', ['template_type'])
        op.create_index('ix_compliance_templates_is_active', 'compliance_templates', ['is_active'])


def downgrade() -> None:
    # Drop compliance_templates table and indexes
    op.drop_index('ix_compliance_templates_is_active', table_name='compliance_templates')
    op.drop_index('ix_compliance_templates_template_type', table_name='compliance_templates')
    op.drop_index('ix_compliance_templates_mechanism', table_name='compliance_templates')
    op.drop_index('ix_compliance_templates_funder_name', table_name='compliance_templates')
    op.drop_table('compliance_templates')

    # Drop compliance_tasks table and indexes
    op.drop_index('ix_compliance_tasks_user_status', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_status', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_due_date', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_requirement_id', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_application_id', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_grant_id', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_match_id', table_name='compliance_tasks')
    op.drop_index('ix_compliance_tasks_user_id', table_name='compliance_tasks')
    op.drop_table('compliance_tasks')

    # Drop funder_requirements table and indexes
    op.drop_index('ix_funder_requirements_mechanism', table_name='funder_requirements')
    op.drop_index('ix_funder_requirements_is_active', table_name='funder_requirements')
    op.drop_index('ix_funder_requirements_frequency', table_name='funder_requirements')
    op.drop_index('ix_funder_requirements_requirement_type', table_name='funder_requirements')
    op.drop_index('ix_funder_requirements_funder_name', table_name='funder_requirements')
    op.drop_table('funder_requirements')
