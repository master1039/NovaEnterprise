"""JWT claims, signatures, expiry, and production configuration are strict."""

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings
from backend.app.core.exceptions import ApplicationError
from backend.app.core.security import AuthenticatedUser, decode_access_token, issue_access_token
from backend.app.schemas.common import UserRole


def test_access_token_round_trip_uses_expected_identity_claims() -> None:
    settings = Settings(app_env="test")
    user = AuthenticatedUser(
        id="user-1",
        username="analyst",
        role=UserRole.ANALYST,
        tenant_id="tenant-a",
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token, expires_in = issue_access_token(user, settings, now=now)
    decoded = decode_access_token(token, settings, now=now + timedelta(seconds=1))
    assert decoded == user
    assert expires_in == 3600


def test_expired_or_wrong_secret_token_is_rejected() -> None:
    settings = Settings(app_env="test", jwt_ttl_minutes=1)
    user = AuthenticatedUser(
        id="user-1",
        username="viewer",
        role=UserRole.VIEWER,
        tenant_id="tenant-a",
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token, _ = issue_access_token(user, settings, now=now)
    with pytest.raises(ApplicationError, match="invalid or expired"):
        decode_access_token(token, settings, now=now + timedelta(minutes=1))
    with pytest.raises(ApplicationError, match="invalid or expired"):
        decode_access_token(
            token,
            Settings(app_env="test", jwt_secret="a-different-secret-value-for-testing"),
            now=now,
        )


@pytest.mark.parametrize(
    "override",
    [{"jwt_issuer": "other-issuer"}, {"jwt_audience": "other-audience"}],
)
def test_wrong_issuer_or_audience_is_rejected(override: dict[str, str]) -> None:
    settings = Settings(app_env="test")
    user = AuthenticatedUser(
        id="user-1",
        username="viewer",
        role=UserRole.VIEWER,
        tenant_id="tenant-a",
    )
    now = datetime(2026, 1, 1, tzinfo=UTC)
    token, _ = issue_access_token(user, settings, now=now)

    with pytest.raises(ApplicationError, match="invalid or expired"):
        decode_access_token(
            token,
            Settings(app_env="test", **override),
            now=now,
        )


def test_production_rejects_the_local_demo_signing_secret() -> None:
    with pytest.raises(ValidationError, match="NOVA_JWT_SECRET"):
        Settings(app_env="production")


def test_signing_secret_must_be_at_least_32_characters() -> None:
    with pytest.raises(ValidationError, match="at least 32"):
        Settings(app_env="test", jwt_secret="too-short")
