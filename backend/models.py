"""
GrantRadar Database Models
SQLAlchemy ORM models for the grant intelligence platform.
"""
import enum
import uuid
from datetime import datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    ARRAY,
    TIMESTAMP,
    Column,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class ApplicationStage(enum.Enum):
    """Enum for grant application pipeline stages."""

    RESEARCHING = "researching"
    WRITING = "writing"
    SUBMITTED = "submitted"
    AWARDED = "awarded"
    REJECTED = "rejected"


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
    applications: Mapped[list["GrantApplication"]] = relationship(
        "GrantApplication",
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
    slack_webhook_url: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Slack incoming webhook URL for notifications",
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
    applications: Mapped[list["GrantApplication"]] = relationship(
        "GrantApplication",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saved_searches: Mapped[list["SavedSearch"]] = relationship(
        "SavedSearch",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    deadlines: Mapped[List["Deadline"]] = relationship(
        "Deadline",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    calendar_integrations: Mapped[List["CalendarIntegration"]] = relationship(
        "CalendarIntegration",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    templates: Mapped[List["Template"]] = relationship(
        "Template",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    funding_alert_preferences: Mapped[Optional["FundingAlertPreference"]] = relationship(
        "FundingAlertPreference",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    chat_sessions: Mapped[List["ChatSession"]] = relationship(
        "ChatSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    research_sessions: Mapped[List["ResearchSession"]] = relationship(
        "ResearchSession",
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
    institution: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Research institution/university",
    )
    department: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Department within institution",
    )
    keywords: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Research keywords for matching",
    )
    source_text_hash: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        doc="SHA-256 hash of embedding source text for cache invalidation",
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
    vector_similarity: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="Vector similarity score (0.0 to 1.0)",
    )
    llm_match_score: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
        doc="LLM-computed match score (0-100)",
    )
    reasoning: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="AI-generated explanation for the match",
    )
    key_strengths: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Key strengths identified by LLM",
    )
    concerns: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Concerns identified by LLM",
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
    application: Mapped[Optional["GrantApplication"]] = relationship(
        "GrantApplication",
        back_populates="match",
        uselist=False,
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


class GrantApplication(Base):
    """
    Grant application pipeline tracking.

    Tracks grants through application stages from research to outcome.
    Users can add notes, target dates, and move grants through the pipeline.
    """

    __tablename__ = "grant_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the pipeline item",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    grant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the grant being tracked",
    )
    match_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("matches.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional reference to the match that led to this application",
    )
    stage: Mapped[ApplicationStage] = mapped_column(
        Enum(ApplicationStage),
        nullable=False,
        default=ApplicationStage.RESEARCHING,
        doc="Current stage in the application pipeline",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="User notes about this application",
    )
    target_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="User's target submission date",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When the grant was added to pipeline",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        doc="When the pipeline item was last updated",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="applications",
    )
    grant: Mapped["Grant"] = relationship(
        "Grant",
        back_populates="applications",
    )
    match: Mapped[Optional["Match"]] = relationship(
        "Match",
        back_populates="application",
    )

    __table_args__ = (
        Index("ix_grant_applications_user_id", user_id),
        Index("ix_grant_applications_grant_id", grant_id),
        Index("ix_grant_applications_stage", stage),
        UniqueConstraint("user_id", "grant_id", name="uq_grant_applications_user_grant"),
    )

    def __repr__(self) -> str:
        return f"<GrantApplication(id={self.id}, stage='{self.stage.value}')>"


class SavedSearch(Base):
    """
    Saved search filters for quick access and email alerts.

    Users can save search/filter combinations with a name,
    and optionally enable email alerts for new matching grants.
    """

    __tablename__ = "saved_searches"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the saved search",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="User-defined name for this saved search",
    )
    filters: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Search filters as JSON (source, categories, amount range, etc.)",
    )
    alert_enabled: Mapped[bool] = mapped_column(
        default=False,
        doc="Enable email alerts for new grants matching this search",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        doc="When the saved search was created",
    )
    last_alerted_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the last alert was sent for this search",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="saved_searches",
    )

    __table_args__ = (
        Index("ix_saved_searches_user_id", user_id),
        Index("ix_saved_searches_alert_enabled", alert_enabled),
    )

    def __repr__(self) -> str:
        return f"<SavedSearch(id={self.id}, name='{self.name}')>"


class Deadline(Base):
    """
    User-created deadline for grant submissions.

    Allows users to track grant deadlines with customizable details,
    priority levels, and optional links to existing grants in the system.
    """

    __tablename__ = "deadlines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the deadline",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    grant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional reference to an existing grant",
    )
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        doc="Deadline title/name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Detailed description of the deadline",
    )
    funder: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        doc="Funding organization name",
    )
    mechanism: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        doc="Grant mechanism type (e.g., R01, R21)",
    )
    sponsor_deadline: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        doc="Official sponsor submission deadline",
    )
    internal_deadline: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Internal institutional deadline (usually before sponsor deadline)",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        default="active",
        nullable=False,
        doc="Deadline status: 'active', 'submitted', 'missed', 'cancelled'",
    )
    priority: Mapped[str] = mapped_column(
        String(20),
        default="medium",
        nullable=False,
        doc="Priority level: 'low', 'medium', 'high'",
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
        doc="URL to the grant opportunity",
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Additional notes about the deadline",
    )
    color: Mapped[str] = mapped_column(
        String(7),
        default="#3B82F6",
        nullable=False,
        doc="Hex color code for calendar display",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="deadlines",
    )
    grant: Mapped[Optional["Grant"]] = relationship("Grant")
    reminder_schedules: Mapped[List["ReminderSchedule"]] = relationship(
        "ReminderSchedule",
        back_populates="deadline",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_deadlines_user_id", user_id),
        Index("ix_deadlines_sponsor_deadline", sponsor_deadline),
        Index("ix_deadlines_status", status),
    )

    def __repr__(self) -> str:
        return f"<Deadline(id={self.id}, title='{self.title[:50]}...')>"


class CalendarIntegration(Base):
    """
    OAuth token storage for calendar sync providers.

    Stores encrypted OAuth tokens for Google Calendar and Outlook
    to enable automatic deadline syncing.
    """

    __tablename__ = "calendar_integrations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the calendar integration",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    provider: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Calendar provider: 'google' or 'outlook'",
    )
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Encrypted OAuth access token",
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Encrypted OAuth refresh token",
    )
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the access token expires",
    )
    calendar_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        doc="External calendar ID from provider",
    )
    sync_enabled: Mapped[bool] = mapped_column(
        default=True,
        doc="Whether calendar sync is enabled",
    )
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Last successful sync timestamp",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="calendar_integrations",
    )

    __table_args__ = (
        Index("ix_calendar_integrations_user_id", user_id),
        Index("ix_calendar_integrations_provider", provider),
        UniqueConstraint("user_id", "provider", name="uq_calendar_integrations_user_provider"),
    )

    def __repr__(self) -> str:
        return f"<CalendarIntegration(id={self.id}, provider='{self.provider}')>"


class ReminderSchedule(Base):
    """
    Scheduled reminders for user deadlines.

    Allows users to configure multiple reminders (email, push, SMS)
    for each deadline at different intervals.
    """

    __tablename__ = "reminder_schedules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the reminder schedule",
    )
    deadline_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deadlines.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the deadline",
    )
    reminder_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        doc="Reminder type: 'email', 'push', or 'sms'",
    )
    remind_before_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Minutes before deadline to send reminder (e.g., 1440 for 1 day)",
    )
    is_sent: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether the reminder has been sent",
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="When the reminder was sent",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    # Relationships
    deadline: Mapped["Deadline"] = relationship(
        "Deadline",
        back_populates="reminder_schedules",
    )

    __table_args__ = (
        Index("ix_reminder_schedules_deadline_id", deadline_id),
        Index("ix_reminder_schedules_is_sent", is_sent),
        Index("ix_reminder_schedules_reminder_type", reminder_type),
    )

    def __repr__(self) -> str:
        return f"<ReminderSchedule(id={self.id}, type='{self.reminder_type}', minutes={self.remind_before_minutes})>"


class TemplateCategory(Base):
    """
    Categories for organizing document templates.

    Provides logical grouping for templates like 'Abstract',
    'Budget Justification', 'Specific Aims', etc.
    """

    __tablename__ = "template_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the category",
    )
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        doc="Category name",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Category description",
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Order for displaying categories",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )

    # Relationships
    templates: Mapped[List["Template"]] = relationship(
        "Template",
        back_populates="category",
    )

    __table_args__ = (
        Index("ix_template_categories_name", name),
        Index("ix_template_categories_display_order", display_order),
    )

    def __repr__(self) -> str:
        return f"<TemplateCategory(id={self.id}, name='{self.name}')>"


class Template(Base):
    """
    Reusable document templates for grant proposals.

    Stores template content with variable placeholders that users
    can fill in when generating documents. Supports both system
    templates (read-only) and user-created templates.
    """

    __tablename__ = "templates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the template",
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        doc="Owner user ID (null for system templates)",
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("template_categories.id", ondelete="SET NULL"),
        nullable=True,
        doc="Template category reference",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Template title",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="Template description",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Template content with placeholders",
    )
    variables: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        doc="Variable definitions: [{name, type, description, default}]",
    )
    is_public: Mapped[bool] = mapped_column(
        default=False,
        doc="Whether template is publicly visible",
    )
    is_system: Mapped[bool] = mapped_column(
        default=False,
        doc="System templates are read-only",
    )
    usage_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        doc="Number of times template has been used",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="templates",
    )
    category: Mapped[Optional["TemplateCategory"]] = relationship(
        "TemplateCategory",
        back_populates="templates",
    )

    __table_args__ = (
        Index("ix_templates_user_id", user_id),
        Index("ix_templates_category_id", category_id),
        Index("ix_templates_is_public", is_public),
        Index("ix_templates_is_system", is_system),
        Index("ix_templates_title", title),
    )

    def __repr__(self) -> str:
        return f"<Template(id={self.id}, title='{self.title[:50]}...')>"


class FundingAlertPreference(Base):
    """
    User preferences for funding alert email newsletters.

    Stores configuration for personalized funding alert emails including
    frequency, minimum match scores, and content preferences.
    """

    __tablename__ = "funding_alert_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the preference record",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        doc="Reference to the owning user",
    )
    enabled: Mapped[bool] = mapped_column(
        default=True,
        doc="Whether funding alerts are enabled",
    )
    frequency: Mapped[str] = mapped_column(
        String(20),
        default="weekly",
        nullable=False,
        doc="Alert frequency: 'daily', 'weekly', or 'monthly'",
    )
    min_match_score: Mapped[int] = mapped_column(
        Integer,
        default=70,
        nullable=False,
        doc="Minimum match score (0-100) to include in alerts",
    )
    include_deadlines: Mapped[bool] = mapped_column(
        default=True,
        doc="Include upcoming deadline reminders in alerts",
    )
    include_new_grants: Mapped[bool] = mapped_column(
        default=True,
        doc="Include new matching grants in alerts",
    )
    include_insights: Mapped[bool] = mapped_column(
        default=True,
        doc="Include AI-generated personalized insights",
    )
    preferred_funders: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="List of preferred funder names to prioritize",
    )
    last_sent_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Timestamp of last sent funding alert",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="funding_alert_preferences",
    )

    __table_args__ = (
        Index("ix_funding_alert_preferences_user_id", user_id),
        Index("ix_funding_alert_preferences_enabled", enabled),
        Index("ix_funding_alert_preferences_frequency", frequency),
    )

    def __repr__(self) -> str:
        return f"<FundingAlertPreference(id={self.id}, user_id={self.user_id}, enabled={self.enabled})>"


class GrantDeadlineHistory(Base):
    """
    Historical record of grant deadlines for forecasting and analysis.

    Stores historical deadline data from various funding sources to enable
    prediction of future grant cycles and deadline patterns. This data is
    used by the forecasting service to estimate when grants will reopen.
    """

    __tablename__ = "grant_deadline_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the historical record",
    )
    grant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional reference to matching grant in system (null for historical records)",
    )
    funder_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        doc="Name of the funding organization",
    )
    grant_title: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Title of the grant opportunity",
    )
    deadline_date: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=False,
        index=True,
        doc="Application deadline date",
    )
    open_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Date when grant opened for applications",
    )
    announcement_date: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Date when grant was announced",
    )
    fiscal_year: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        doc="Fiscal year of the grant cycle",
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
    categories: Mapped[Optional[list[str]]] = mapped_column(
        ARRAY(Text),
        nullable=True,
        doc="Research categories/tags associated with the grant",
    )
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        doc="Data source (e.g., 'grants.gov', 'nih', 'nsf')",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Record creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Record last update timestamp",
    )

    # Relationships
    grant: Mapped[Optional["Grant"]] = relationship("Grant")

    __table_args__ = (
        Index("ix_grant_deadline_history_funder_name", funder_name),
        Index("ix_grant_deadline_history_deadline_date", deadline_date),
        Index("ix_grant_deadline_history_fiscal_year", fiscal_year),
        Index("ix_grant_deadline_history_source", source),
    )

    def __repr__(self) -> str:
        return f"<GrantDeadlineHistory(id={self.id}, funder='{self.funder_name}', deadline={self.deadline_date})>"


class ChatSession(Base):
    """
    Chat session for AI-powered conversations.

    Tracks eligibility check conversations and other AI interactions
    with context about the grant being discussed.
    """

    __tablename__ = "chat_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the chat session",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        doc="Session title for display",
    )
    session_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="eligibility",
        doc="Session type (eligibility, general, etc.)",
    )
    context_grant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("grants.id", ondelete="SET NULL"),
        nullable=True,
        doc="Optional reference to grant being discussed",
    )
    metadata_: Mapped[Optional[dict[str, Any]]] = mapped_column(
        "metadata",
        JSONB,
        nullable=True,
        doc="Additional session metadata",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Session creation timestamp",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="Session last update timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="chat_sessions",
    )
    context_grant: Mapped[Optional["Grant"]] = relationship("Grant")
    messages: Mapped[List["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )

    __table_args__ = (
        Index("ix_chat_sessions_user_id", user_id),
        Index("ix_chat_sessions_session_type", session_type),
    )

    def __repr__(self) -> str:
        return f"<ChatSession(id={self.id}, type='{self.session_type}')>"


class ChatMessage(Base):
    """
    Individual message in a chat session.

    Stores the conversation history between user and AI assistant.
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the message",
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the chat session",
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        doc="Message role: 'user', 'assistant', or 'system'",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Message content",
    )
    sources: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="RAG citations and source references",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Message creation timestamp",
    )

    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages",
    )

    __table_args__ = (Index("ix_chat_messages_session_id", session_id),)

    def __repr__(self) -> str:
        return f"<ChatMessage(id={self.id}, role='{self.role}')>"


class ResearchSession(Base):
    """
    Deep research session for intelligent grant discovery.

    Tracks research queries and their results, including AI-generated
    insights and processing metrics.
    """

    __tablename__ = "research_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        doc="Unique identifier for the research session",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        doc="Reference to the owning user",
    )
    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        doc="Research query submitted by user",
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending",
        doc="Status: 'pending', 'processing', 'completed', 'failed'",
    )
    results: Mapped[Optional[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
        doc="Research results as JSON",
    )
    insights: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        doc="AI-generated insights from research",
    )
    grants_found: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Number of grants found in research",
    )
    processing_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        doc="Processing time in milliseconds",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        doc="Session creation timestamp",
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        TIMESTAMP(timezone=True),
        nullable=True,
        doc="Session completion timestamp",
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="research_sessions",
    )

    __table_args__ = (
        Index("ix_research_sessions_user_id", user_id),
        Index("ix_research_sessions_status", status),
    )

    def __repr__(self) -> str:
        return f"<ResearchSession(id={self.id}, status='{self.status}')>"
