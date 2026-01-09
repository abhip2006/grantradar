"""Add institutions and institution_members tables for institutional dashboard

Revision ID: 034
Revises: 033
Create Date: 2026-01-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = '034'
down_revision: Union[str, None] = '033'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    from sqlalchemy import inspect
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()

    # Institutions table - stores institution/organization information
    if 'institutions' not in existing_tables:
        op.create_table(
            'institutions',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False),
            sa.Column('type', sa.String(50), nullable=False),  # university, research_institute, nonprofit, government, industry
            sa.Column('domain', sa.String(255), nullable=True),  # e.g., harvard.edu
            sa.Column('settings', JSONB(), nullable=True),  # Institution-specific settings
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('logo_url', sa.String(500), nullable=True),
            sa.Column('website', sa.String(500), nullable=True),
            sa.Column('address', sa.Text(), nullable=True),
            sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        )
        op.create_index('ix_institutions_name', 'institutions', ['name'])
        op.create_index('ix_institutions_type', 'institutions', ['type'])
        op.create_index('ix_institutions_domain', 'institutions', ['domain'])

    # Institution members table - tracks users belonging to institutions
    if 'institution_members' not in existing_tables:
        op.create_table(
            'institution_members',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('institution_id', UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='CASCADE'), nullable=False),
            sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('role', sa.String(30), nullable=False, server_default='viewer'),  # admin, manager, viewer
            sa.Column('department', sa.String(255), nullable=True),
            sa.Column('title', sa.String(255), nullable=True),  # Job title/position
            sa.Column('permissions', JSONB(), nullable=True),  # Custom permission overrides
            sa.Column('added_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
            sa.Column('added_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
            sa.UniqueConstraint('institution_id', 'user_id', name='uq_institution_member'),
        )
        op.create_index('ix_institution_members_institution_id', 'institution_members', ['institution_id'])
        op.create_index('ix_institution_members_user_id', 'institution_members', ['user_id'])
        op.create_index('ix_institution_members_role', 'institution_members', ['role'])
        op.create_index('ix_institution_members_department', 'institution_members', ['department'])

    # Add institution_id to lab_profiles table for institutional linking
    existing_columns = [col['name'] for col in inspector.get_columns('lab_profiles')]
    if 'institution_id' not in existing_columns:
        op.add_column(
            'lab_profiles',
            sa.Column('institution_id', UUID(as_uuid=True), sa.ForeignKey('institutions.id', ondelete='SET NULL'), nullable=True)
        )
        op.create_index('ix_lab_profiles_institution_id', 'lab_profiles', ['institution_id'])


def downgrade() -> None:
    # Drop institution_id from lab_profiles
    op.drop_index('ix_lab_profiles_institution_id', table_name='lab_profiles')
    op.drop_column('lab_profiles', 'institution_id')

    # Drop institution_members table and indexes
    op.drop_index('ix_institution_members_department', table_name='institution_members')
    op.drop_index('ix_institution_members_role', table_name='institution_members')
    op.drop_index('ix_institution_members_user_id', table_name='institution_members')
    op.drop_index('ix_institution_members_institution_id', table_name='institution_members')
    op.drop_table('institution_members')

    # Drop institutions table and indexes
    op.drop_index('ix_institutions_domain', table_name='institutions')
    op.drop_index('ix_institutions_type', table_name='institutions')
    op.drop_index('ix_institutions_name', table_name='institutions')
    op.drop_table('institutions')
