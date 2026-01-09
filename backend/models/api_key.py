"""
API Key Database Model
SQLAlchemy ORM model for managing external API keys.
"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, List, Optional

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models import Base, GUID, JSONB

if TYPE_CHECKING:
    from backend.models import User


class APIKey(Base):
    """
    API keys for external integrations.

    Stores hashed API keys with scopes and rate limits for
    external service integrations (CI/CD pipelines, webhooks, etc.).
    The actual key is only shown once during creation.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the API key",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        GUID(),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Reference to the owning user",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        doc="Friendly name for the key (e.g., 'My Integration', 'CI/CD Pipeline')",
    )
    key_prefix: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        doc="First 8 characters of the key for identification",
    )
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="SHA-256 hash of the full API key",
    )
    scopes: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        default=list,
        doc="List of permission scopes (e.g., ['read:grants', 'write:applications'])",
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Timestamp of last API key usage",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Optional expiration timestamp",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        doc="Whether the API key is currently active",
    )
    rate_limit: Mapped[int] = mapped_column(
        Integer,
        default=1000,
        nullable=False,
        doc="Maximum requests per hour for this key",
    )
    request_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        doc="Total number of requests made with this key",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="api_keys",
    )

    __table_args__ = (
        # Note: user_id already has index=True on the column
        Index("ix_api_keys_key_prefix", key_prefix),
        Index("ix_api_keys_is_active", is_active),
        {"extend_existing": True},
    )

    def __repr__(self) -> str:
        return f"<APIKey(id={self.id}, name='{self.name}', prefix='{self.key_prefix}...')>"
