"""
Configuration management for ARGUS using Pydantic Settings.
Loads all environment variables and provides validated settings throughout the application.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    anthropic_api_key: str = ""

    # Database Configuration
    postgres_user: str = "argus"
    postgres_password: str = "argus_secret"
    postgres_db: str = "argus"
    database_url: str = "postgresql+asyncpg://argus:argus_secret@localhost:5432/argus"

    # Auth Configuration
    jwt_secret: str = "replace_with_64_char_random_string_minimum_32_chars_required"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60

    # Application Configuration
    environment: str = "development"
    log_level: str = "INFO"

    # Fairness Thresholds
    demographic_parity_warning: float = 0.05
    demographic_parity_critical: float = 0.10
    equalized_odds_warning: float = 0.05
    equalized_odds_critical: float = 0.10

    # Drift Detection Thresholds (PSI)
    psi_info: float = 0.10
    psi_warning: float = 0.20
    psi_critical: float = 0.25

    # Optional Configuration
    slack_webhook_url: Optional[str] = None
    audit_output_dir: str = "audit_outputs"

    class Config:
        """Pydantic config for case-insensitive environment variable loading."""
        env_file = ".env"
        case_sensitive = False


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses @lru_cache to ensure only one Settings instance is created per application lifecycle.
    
    Returns:
        Settings: Cached application settings instance
    """
    return Settings()


# Module-level settings instance for direct import
settings = get_settings()
