"""Add lab members and assignees tables.

Revision ID: 018
Revises: 017
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create lab members table
    op.create_table(
        "lab_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("lab_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("member_email", sa.String(255), nullable=False),
        sa.Column("member_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("role", sa.String(30), server_default="member", nullable=False),
        sa.Column("invited_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("accepted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.UniqueConstraint("lab_owner_id", "member_email", name="uq_lab_member"),
    )
    op.create_index("ix_lab_members_lab_owner_id", "lab_members", ["lab_owner_id"])
    op.create_index("ix_lab_members_member_email", "lab_members", ["member_email"])
    op.create_index("ix_lab_members_member_user_id", "lab_members", ["member_user_id"])

    # Create application assignees table
    op.create_table(
        "application_assignees",
        sa.Column("application_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grant_applications.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("assigned_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_assignees_application_id", "application_assignees", ["application_id"])
    op.create_index("ix_assignees_user_id", "application_assignees", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_assignees_user_id", table_name="application_assignees")
    op.drop_index("ix_assignees_application_id", table_name="application_assignees")
    op.drop_table("application_assignees")
    op.drop_index("ix_lab_members_member_user_id", table_name="lab_members")
    op.drop_index("ix_lab_members_member_email", table_name="lab_members")
    op.drop_index("ix_lab_members_lab_owner_id", table_name="lab_members")
    op.drop_table("lab_members")
