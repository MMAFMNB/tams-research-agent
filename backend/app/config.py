"""Application configuration using pydantic-settings."""

import os
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # App
    APP_NAME: str = "TAM Research Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    API_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/tam_research"
    DATABASE_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes default

    # Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Auth
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    JWT_ALGORITHM: str = "HS256"

    # Anthropic
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # Storage
    STORAGE_TYPE: str = "local"  # "local" or "oci"
    LOCAL_STORAGE_PATH: str = "/tmp/tam-reports"
    OCI_BUCKET_NAME: str = ""
    OCI_NAMESPACE: str = ""

    # Assets
    ASSETS_DIR: str = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")

    # Branding defaults (TAM Capital)
    DEFAULT_PRIMARY_COLOR: str = "#222F62"
    DEFAULT_ACCENT_COLOR: str = "#1A6DB6"
    DEFAULT_TURQUOISE: str = "#6CB9B6"

    # Tadawul ticker mapping
    TADAWUL_TICKERS: dict = {
        "2020": "2020.SR", "2010": "2010.SR", "2222": "2222.SR",
        "1120": "1120.SR", "7010": "7010.SR", "2350": "2350.SR",
        "1180": "1180.SR", "2280": "2280.SR", "2060": "2060.SR",
        "4030": "4030.SR", "1010": "1010.SR", "1150": "1150.SR",
        "3060": "3060.SR", "4200": "4200.SR", "4001": "4001.SR",
    }

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    def resolve_ticker(self, user_input: str) -> str:
        """Resolve user input to a Yahoo Finance ticker symbol."""
        cleaned = user_input.strip().upper()
        if cleaned in self.TADAWUL_TICKERS:
            return self.TADAWUL_TICKERS[cleaned]
        if cleaned.endswith(".SR"):
            return cleaned
        if cleaned.isdigit():
            return f"{cleaned}.SR"
        return cleaned


@lru_cache
def get_settings() -> Settings:
    return Settings()
