"""Offline JWT validation and central role-based authorization."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from backend.app.core.config import Settings
from backend.app.core.exceptions import ApplicationError
from backend.app.schemas.common import UserRole

_bearer = HTTPBearer(auto_error=False)
_ROLE_LEVEL = {UserRole.VIEWER: 1, UserRole.ANALYST: 2, UserRole.ADMIN: 3}


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    username: str
    role: UserRole
    tenant_id: str


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue_access_token(
    user: AuthenticatedUser,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> tuple[str, int]:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.jwt_ttl_minutes)
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": user.id,
        "username": user.username,
        "role": user.role.value,
        "tenant_id": user.tenant_id,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    segments = [
        _b64encode(json.dumps(part, separators=(",", ":"), sort_keys=True).encode())
        for part in (header, payload)
    ]
    signing_input = ".".join(segments).encode()
    signature = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{segments[0]}.{segments[1]}.{_b64encode(signature)}", int(
        (expires_at - issued_at).total_seconds()
    )


def decode_access_token(
    token: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> AuthenticatedUser:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        header = json.loads(_b64decode(encoded_header))
        payload: dict[str, Any] = json.loads(_b64decode(encoded_payload))
        signature = _b64decode(encoded_signature)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise _invalid_token() from exc
    if header != {"alg": "HS256", "typ": "JWT"}:
        raise _invalid_token()
    expected = hmac.new(
        settings.jwt_secret.encode(),
        f"{encoded_header}.{encoded_payload}".encode(),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected):
        raise _invalid_token()
    current = int((now or datetime.now(UTC)).timestamp())
    try:
        if payload["iss"] != settings.jwt_issuer or payload["aud"] != settings.jwt_audience:
            raise ValueError
        if not isinstance(payload["exp"], int) or payload["exp"] <= current:
            raise ValueError
        if not isinstance(payload["iat"], int) or payload["iat"] > current + 30:
            raise ValueError
        return AuthenticatedUser(
            id=payload["sub"],
            username=payload["username"],
            role=UserRole(payload["role"]),
            tenant_id=payload["tenant_id"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid_token() from exc


def _invalid_token() -> ApplicationError:
    return ApplicationError(
        status_code=401,
        code="invalid_token",
        message="The access token is invalid or expired.",
    )


def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> AuthenticatedUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise ApplicationError(
            status_code=401,
            code="authentication_required",
            message="A bearer access token is required.",
        )
    user = decode_access_token(credentials.credentials, request.app.state.settings)
    request.state.user = user
    return user


def require_role(minimum_role: UserRole):
    """Return a FastAPI dependency enforcing the role hierarchy centrally."""

    def authorize(
        user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if _ROLE_LEVEL[user.role] < _ROLE_LEVEL[minimum_role]:
            raise ApplicationError(
                status_code=403,
                code="insufficient_role",
                message="Your role does not permit this action.",
            )
        return user

    return authorize
