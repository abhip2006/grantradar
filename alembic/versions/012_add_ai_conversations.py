"""Add AI conversation tables for chat and eligibility features.

Revision ID: 012
Revises: 011
Create Date: 2025-01-08
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def table_exists(table_name: str) -> bool:
    """Check if a table exists in the database."""
    bind = op.get_bind()
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    """Create chat tables (idempotent)."""
    if table_exists("chat_sessions") and table_exists("chat_messages"):
        return

    # Chat sessions table
    if not table_exists("chat_sessions"):
        op.create_table(
            "chat_sessions",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(500), nullable=False),
            sa.Column("session_type", sa.String(50), nullable=False),  # 'eligibility', 'proposal_chat', 'research'
            sa.Column("context_grant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("grants.id", ondelete="SET NULL"), nullable=True),
            sa.Column("metadata", postgresql.JSONB(), nullable=True),
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_chat_sessions_user_id", "chat_sessions", ["user_id"])
        op.create_index("ix_chat_sessions_session_type", "chat_sessions", ["session_type"])

    # Chat messages table
    if not table_exists("chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),  # 'user', 'assistant', 'system'
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("sources", postgresql.JSONB(), nullable=True),  # For RAG citations
            sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_chat_messages_session_id", "chat_messages", ["session_id"])


def downgrade() -> None:
    op.drop_index("ix_chat_messages_session_id", table_name="chat_messages")
    op.drop_table("chat_messages")
    op.drop_index("ix_chat_sessions_session_type", table_name="chat_sessions")
    op.drop_index("ix_chat_sessions_user_id", table_name="chat_sessions")
    op.drop_table("chat_sessions")
