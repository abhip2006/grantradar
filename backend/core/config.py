"""
GrantRadar Configuration
Central configuration management using Pydantic Settings
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ===== Application =====
    app_name: str = "GrantRadar"
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key-change-in-production"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # ===== Database =====
    database_url: str = "postgresql://grantradar:grantradar_dev_password@localhost:5432/grantradar"
    async_database_url: str = "postgresql+asyncpg://grantradar:grantradar_dev_password@localhost:5432/grantradar"

    # ===== Redis =====
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # ===== AI API Keys =====
    anthropic_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None

    # ===== Notification Services =====
    sendgrid_api_key: Optional[str] = None
    twilio_account_sid: Optional[str] = None
    twilio_auth_token: Optional[str] = None
    twilio_phone_number: Optional[str] = None
    slack_webhook_url: Optional[str] = None  # Default Slack webhook for system notifications

    # ===== Stripe =====
    stripe_secret_key: Optional[str] = None
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

    # ===== Email =====
    from_email: str = "alerts@grantradar.com"
    from_name: str = "GrantRadar"

    # ===== Grant Source URLs =====
    nih_reporter_api_url: str = "https://api.reporter.nih.gov/v2/projects/search"
    nsf_api_url: str = "https://www.research.gov/awardapi-service/v1/awards.json"
    grants_gov_api_url: str = "https://api.grants.gov/v1/api/search2"
    grants_gov_rss_url: str = "https://www.grants.gov/rss/GG_NewOps.xml"

    # ===== Embedding Config =====
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    # ===== LLM Config =====
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_tokens: int = 4096


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
