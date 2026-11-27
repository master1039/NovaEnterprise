"""Typed contracts for conversation, user, organizational, and workflow memory."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MemoryScope(StrEnum):
    CONVERSATION = "conversation"
    USER = "user"
    ORGANIZATIONAL = "organizational"
    WORKFLOW = "workflow"


class MemoryEntry(BaseModel):
    """A provenance-carrying fact with scope-specific ownership."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=64)
    scope: MemoryScope
    user_id: str | None = Field(default=None, min_length=1, max_length=64)
    session_id: str | None = Field(default=None, min_length=1, max_length=64)
    key: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=20_000)
    source: str = Field(min_length=1, max_length=240)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def validate_scope_context(self) -> MemoryEntry:
        if self.scope in {MemoryScope.CONVERSATION, MemoryScope.WORKFLOW}:
            if self.user_id is None or self.session_id is None:
                raise ValueError("conversation and workflow memory require user_id and session_id")
        elif self.scope is MemoryScope.USER:
            if self.user_id is None:
                raise ValueError("user_id is required for user memory")
            if self.session_id is not None:
                raise ValueError("user memory must not carry session_id")
        elif self.user_id is not None or self.session_id is not None:
            raise ValueError("organizational memory must not carry user_id or session_id")
        return self
