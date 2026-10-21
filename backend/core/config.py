"""
Configuration settings for Aanya Assistant using Pydantic Settings.
Loads configuration from environment variables or .env file.
"""
from functools import lru_cache
from typing import List, Union
import json
import logging
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("aanya.config")


class Settings(BaseSettings):
    """Application settings with environment variable overrides."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application Settings
    APP_NAME: str = "Aanya Assistant"
    APP_VERSION: str = "0.1.0"
    ENVIRONMENT: str = Field(default="development", description="development, production, testing")
    DEBUG: bool = False
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Security
    SECRET_KEY: str = Field(
        default="insecure-placeholder-key-for-dev-only-min-32-chars-long",
        description="Secret key for JWT / session signing. Must be changed in production.",
    )

    # CORS Configuration
    # Defaults to localhost and internal loopback for safe local development
    ALLOWED_ORIGINS: List[str] = Field(
        default=[
            "http://localhost",
            "http://localhost:80",
            "http://localhost:8000",
            "http://127.0.0.1",
            "http://127.0.0.1:80",
            "http://127.0.0.1:8000",
        ],
        description="Allowed CORS origins list",
    )

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            v_stripped = v.strip()
            if v_stripped.startswith("[") and v_stripped.endswith("]"):
                try:
                    return json.loads(v_stripped)
                except Exception:
                    pass
            return [i.strip() for i in v_stripped.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    # Database Settings
    POSTGRES_USER: str = "aanya_user"
    POSTGRES_PASSWORD: str = "aanya_password"
    POSTGRES_DB: str = "aanya_db"
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # Database Connection URL (defaults to Docker compose service 'db')
    DATABASE_URL: str = Field(
        default="postgresql+psycopg://aanya_user:aanya_password@db:5432/aanya_db",
        description="SQLAlchemy database connection URI (PostgreSQL or SQLite for tests)",
    )

    # Scheduler
    SCHEDULER_AUTOSTART: bool = True

    # Caddy & Production Domain
    DOMAIN_NAME: str = "localhost"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.lower() == "production"

    @property
    def is_testing(self) -> bool:
        return self.ENVIRONMENT.lower() == "testing"

    @model_validator(mode="after")
    def check_production_safety(self) -> "Settings":
        if self.is_production:
            if "placeholder" in self.SECRET_KEY.lower() or "insecure" in self.SECRET_KEY.lower():
                logger.warning(
                    "SECURITY WARNING: Running in production mode with default placeholder SECRET_KEY. "
                    "Configure SECRET_KEY in your .env file."
                )
        return self


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
