"""Local-only demo authentication and the authenticated user contract."""

from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, ConfigDict, Field

from backend.app.core.exceptions import ApplicationError
from backend.app.core.security import AuthenticatedUser, issue_access_token, require_role
from backend.app.schemas.common import UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: AuthenticatedUser


def _demo_users(tenant_id: str) -> dict[str, tuple[str, AuthenticatedUser]]:
    return {
        role.value: (
            f"demo-{role.value}",
            AuthenticatedUser(
                id=f"demo-{role.value}",
                username=role.value,
                role=role,
                tenant_id=tenant_id,
            ),
        )
        for role in UserRole
    }


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request) -> TokenResponse:
    settings = request.app.state.settings
    if not settings.demo_auth_enabled:
        raise ApplicationError(
            status_code=404,
            code="demo_auth_disabled",
            message="Demo authentication is not available in this environment.",
        )
    stored = _demo_users(settings.default_tenant_id).get(body.username)
    valid = stored is not None and hmac.compare_digest(body.password, stored[0])
    if not valid:
        raise ApplicationError(
            status_code=401,
            code="invalid_credentials",
            message="The username or password is incorrect.",
        )
    user = stored[1]
    token, expires_in = issue_access_token(user, settings)
    return TokenResponse(access_token=token, expires_in=expires_in, user=user)


@router.get("/me", response_model=AuthenticatedUser)
def current_user(
    user: Annotated[AuthenticatedUser, Depends(require_role(UserRole.VIEWER))],
) -> AuthenticatedUser:
    return user
