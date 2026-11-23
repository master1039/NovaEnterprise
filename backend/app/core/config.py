"""Central, environment-driven application settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

SUPPORTED_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}


class Settings(BaseSettings):
    """Runtime and persistence settings with safe local defaults."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="NOVA_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "NovaEnterprise"
    app_env: Literal["local", "test", "staging", "production"] = "local"
    debug: bool = False
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite:///./data/enterprise.db"
    default_tenant_id: str = "novaenterprise-demo"
    jwt_secret: str = Field(
        default="local-demo-secret-change-before-production-32",
        min_length=32,
    )
    jwt_issuer: str = "novaenterprise"
    jwt_audience: str = "novaenterprise-api"
    jwt_ttl_minutes: int = Field(default=60, ge=1, le=1440)
    rate_limit_per_minute: int = Field(default=120, ge=1, le=100_000)
    audit_trail_max_records: int = Field(default=10_000, ge=1, le=1_000_000)

    @field_validator("log_level")
    @classmethod
    def normalize_log_level(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in SUPPORTED_LOG_LEVELS:
            raise ValueError(f"log_level must be one of {sorted(SUPPORTED_LOG_LEVELS)}")
        return normalized

    @field_validator("api_prefix")
    @classmethod
    def validate_api_prefix(cls, value: str) -> str:
        normalized = value.rstrip("/") or "/"
        if not normalized.startswith("/"):
            raise ValueError("api_prefix must start with '/'")
        return normalized

    @model_validator(mode="after")
    def reject_demo_secret_in_production(self) -> "Settings":
        if self.app_env == "production" and self.jwt_secret.startswith("local-demo-"):
            raise ValueError("NOVA_JWT_SECRET must be replaced in production")
        return self

    @property
    def demo_auth_enabled(self) -> bool:
        return self.app_env in {"local", "test"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return one cached settings object per process."""

    return Settings()
