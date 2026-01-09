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
    app_version: str = "1.0.0"
    environment: str = "development"
    # SECURITY: Debug mode disabled by default - enable explicitly in .env for development
    debug: bool = False
    # SECURITY: Must be set in .env - validated at startup
    secret_key: str = "CHANGE-THIS-IN-PRODUCTION-REQUIRED"
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:5173"

    # ===== Development Auth Bypass =====
    # SECURITY: These must be False in production - only enable for local development
    dev_bypass_auth: bool = False  # Backend auth bypass
    vite_dev_bypass_auth: bool = False  # Frontend auth bypass (passed through for reference)

    # ===== SSL/HTTPS Configuration =====
    # Set to True when running behind HTTPS reverse proxy
    ssl_enabled: bool = False
    # Trust X-Forwarded-* headers from reverse proxy
    trust_proxy_headers: bool = True
    # Secure cookie settings (enabled when SSL is active)
    cookie_secure: bool = False  # Set to True in production with HTTPS
    # SameSite cookie policy: "lax", "strict", or "none"
    cookie_samesite: str = "lax"

    # ===== CORS Configuration =====
    # Allowed origins for CORS (comma-separated list or "*" for all)
    cors_origins: str = "http://localhost:3000,http://localhost:5173,http://localhost:80"
    # Allow credentials in CORS requests
    cors_allow_credentials: bool = True

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

    # ===== Google Calendar OAuth =====
    google_client_id: str = ""
    google_client_secret: str = ""

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

    # ===== Sentry Error Tracking =====
    sentry_dsn: Optional[str] = None
    sentry_environment: Optional[str] = None  # Falls back to environment if not set
    sentry_traces_sample_rate: float = 0.1  # 10% of transactions for performance monitoring
    sentry_profiles_sample_rate: float = 0.1  # 10% of transactions for profiling

    # ===== Rate Limiting =====
    rate_limit_enabled: bool = True  # Set to False to disable rate limiting

    # Auth endpoints (login, register) - strict limits
    rate_limit_auth_requests: int = 5
    rate_limit_auth_window: int = 60  # 5 requests per minute

    # AI endpoints (chat, writing, insights) - moderate limits
    rate_limit_ai_requests: int = 30
    rate_limit_ai_window: int = 60  # 30 requests per minute

    # Search endpoints - higher limits
    rate_limit_search_requests: int = 60
    rate_limit_search_window: int = 60  # 60 requests per minute

    # Standard API endpoints - default limits
    rate_limit_standard_requests: int = 120
    rate_limit_standard_window: int = 60  # 120 requests per minute


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
