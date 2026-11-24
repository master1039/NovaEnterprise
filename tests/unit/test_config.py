"""Settings are centralized, validated, and environment-driven."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.app_name == "NovaEnterprise"
    assert settings.app_env == "test"
    assert settings.debug is False
    assert settings.api_prefix == "/api/v1"
    assert settings.log_level == "WARNING"


def test_settings_read_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NOVA_APP_NAME", "NovaEnterprise Test")
    monkeypatch.setenv("NOVA_LOG_LEVEL", "debug")
    monkeypatch.setenv("NOVA_API_PREFIX", "/internal/v1")
    get_settings.cache_clear()

    settings = get_settings()

    assert settings.app_name == "NovaEnterprise Test"
    assert settings.log_level == "DEBUG"
    assert settings.api_prefix == "/internal/v1"


def test_api_prefix_must_start_with_a_slash() -> None:
    with pytest.raises(ValidationError):
        Settings(api_prefix="api/v1", _env_file=None)


def test_log_level_must_be_supported() -> None:
    with pytest.raises(ValidationError):
        Settings(log_level="verbose", _env_file=None)


def test_neo4j_credentials_must_be_configured_as_a_pair() -> None:
    with pytest.raises(ValidationError, match="must be set together"):
        Settings(neo4j_username="neo4j", _env_file=None)
