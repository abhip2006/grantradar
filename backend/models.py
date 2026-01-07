"""
GrantRadar Database Models
SQLAlchemy ORM models for the grant intelligence platform.
"""
import uuid
from datetime import datetime
from typing import Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Column,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class Grant(Base):
    """
    Grant opportunities from various funding sources.

    Stores grant details including metadata, eligibility criteria,
    and vector embeddings for semantic similarity search.
    """

    __tablename__ = "grants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the grant",
    )
    source: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Data source (e.g., 'nih', 'nsf', 'grants_gov')",
    )
    external_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        doc="Unique identifier from the source system",
    )
    title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Grant title/name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Full grant description",
    )
    agency: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Funding agency name",
    )
    amount_min: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Minimum funding amount in USD",
    )
    amount_max: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Maximum funding amount in USD",
    )
    deadline: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Application deadline",
    )
    posted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the grant was posted/published",
    )
    url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Link to the grant opportunity",
    )
    eligibility: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Eligibility criteria as structured JSON",
    )
    categories: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Research categories/tags",
    )
    raw_data: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Raw data from source for debugging/auditing",
    )
    embedding = mapped_column(
        Vector(1536),
        nullable=True,
        doc="Vector embedding for semantic similarity search",
    )
    search_vector = mapped_column(
        TSVECTOR,
        nullable=True,
        doc="Full-text search vector combining title, description, and agency",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Record creation timestamp",
    )

    # Relationships
    matches: Mapped[list["Match"]] = relationship(
        "Match",
        back_populates="grant",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_grants_posted_at_desc", posted_at.desc()),
        Index("ix_grants_deadline_asc", deadline.asc()),
        Index("ix_grants_source", source),
        Index(
            "ix_grants_embedding",
            embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_grants_search_vector",
            search_vector,
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        return f"<Grant(id={self.id}, title='{self.title[:50]}...')>"


class User(Base):
    """
    User accounts for researchers and lab administrators.

    Stores authentication credentials, profile information,
    and subscription details.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the user",
    )
    email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        doc="User email address (used for login)",
    )
    password_hash: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Bcrypt hashed password",
    )
    name: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User's full name",
    )
    institution: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Research institution/university",
    )
    phone: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Phone number for SMS alerts",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Account creation timestamp",
    )
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Stripe customer ID for billing",
    )

    # Notification preferences
    email_notifications: Mapped[bool] = mapped_column(
        default=True,
        doc="Enable email notifications for grant matches",
    )
    sms_notifications: Mapped[bool] = mapped_column(
        default=False,
        doc="Enable SMS notifications for critical matches",
    )
    slack_notifications: Mapped[bool] = mapped_column(
        default=False,
        doc="Enable Slack notifications for grant matches",
    )
    digest_frequency: Mapped[str] = mapped_column(
        String(20),
        default="immediate",
        doc="Notification frequency: 'immediate', 'daily', or 'weekly'",
    )
    minimum_match_score: Mapped[float] = mapped_column(
        Float,
        default=0.7,
        doc="Minimum match score threshold for notifications (0.0 to 1.0)",
    )

    # Relationships
    lab_profiles: Mapped[list["LabProfile"]] = relationship(
        "LabProfile",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    matches: Mapped[list["Match"]] = relationship(
        "Match",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email='{self.email}')>"


class LabProfile(Base):
    """
    Research lab profile for grant matching.

    Contains research focus areas, methodologies, and track record
    used to compute match scores with grant opportunities.
    """

    __tablename__ = "lab_profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the lab profile",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    research_areas: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Primary research areas/topics",
    )
    methods: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Research methodologies and techniques",
    )
    career_stage: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Career stage (e.g., 'early_career', 'established', 'senior')",
    )
    past_grants: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Historical grant awards",
    )
    publications: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Publication history and metrics",
    )
    orcid: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="ORCID identifier for researcher",
    )
    profile_embedding = mapped_column(
        Vector(1536),
        nullable=True,
        doc="Vector embedding of research profile for matching",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Profile creation timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="lab_profiles",
    )

    __table_args__ = (
        Index("ix_lab_profiles_user_id", user_id),
        Index(
            "ix_lab_profiles_embedding",
            profile_embedding,
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"profile_embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<LabProfile(id={self.id}, user_id={self.user_id})>"


class Match(Base):
    """
    Grant-to-researcher match results.

    Stores computed match scores, AI-generated reasoning,
    and user feedback for continuous improvement.
    """

    __tablename__ = "matches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the match",
    )
    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the matched grant",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the matched user",
    )
    match_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        doc="Computed match score (0.0 to 1.0)",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="AI-generated explanation for the match",
    )
    predicted_success: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Predicted probability of successful application",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="Match computation timestamp",
    )
    user_action: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User action (e.g., 'saved', 'dismissed', 'applied')",
    )
    user_feedback: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Detailed user feedback for model improvement",
    )

    # Relationships
    grant: Mapped["Grant"] = relationship(
        "Grant",
        back_populates="matches",
    )
    user: Mapped["User"] = relationship(
        "User",
        back_populates="matches",
    )
    alerts: Mapped[list["AlertSent"]] = relationship(
        "AlertSent",
        back_populates="match",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_matches_grant_id", grant_id),
        Index("ix_matches_user_id", user_id),
        Index("ix_matches_score_desc", match_score.desc()),
        UniqueConstraint("grant_id", "user_id", name="uq_matches_grant_user"),
    )

    def __repr__(self) -> str:
        return f"<Match(id={self.id}, score={self.match_score:.2f})>"


class AlertSent(Base):
    """
    Notification delivery tracking.

    Records all alerts sent to users with engagement metrics
    for analyzing notification effectiveness.
    """

    __tablename__ = "alerts_sent"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the alert",
    )
    match_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the match that triggered this alert",
    )
    channel: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Notification channel (e.g., 'email', 'sms', 'push')",
    )
    sent_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When the alert was sent",
    )
    opened_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the user opened the alert",
    )
    clicked_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the user clicked through to view the grant",
    )

    # Relationships
    match: Mapped["Match"] = relationship(
        "Match",
        back_populates="alerts",
    )

    __table_args__ = (
        Index("ix_alerts_sent_match_id", match_id),
        Index("ix_alerts_sent_channel", channel),
        Index("ix_alerts_sent_sent_at_desc", sent_at.desc()),
    )

    def __repr__(self) -> str:
        return f"<AlertSent(id={self.id}, channel='{self.channel}')>"
