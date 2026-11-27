"""Public service for recording, recalling, and clearing four memory scopes."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from backend.app.core.guardrails import redact_secrets
from memory.adapters import MemoryAdapter
from memory.schemas import MemoryEntry, MemoryScope

MemoryOperationStatus = Literal["completed", "degraded"]


@dataclass(frozen=True)
class MemoryOperationResult:
    status: MemoryOperationStatus
    items: tuple[MemoryEntry, ...] = ()
    affected: int = 0
    errors: tuple[str, ...] = ()


def _safe_value(value: Any) -> Any:
    if isinstance(value, str):
        return redact_secrets(value)
    if isinstance(value, list):
        return [_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_safe_value(item) for item in value)
    if isinstance(value, dict):
        return {redact_secrets(str(key)): _safe_value(item) for key, item in value.items()}
    return value


class MemoryService:
    def __init__(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str,
        short_term: MemoryAdapter,
        durable: MemoryAdapter,
    ) -> None:
        for name, value in (
            ("tenant_id", tenant_id),
            ("user_id", user_id),
            ("session_id", session_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.session_id = session_id
        self.short_term = short_term
        self.durable = durable
        for adapter in (short_term, durable):
            adapter_tenant = getattr(adapter, "tenant_id", tenant_id)
            if adapter_tenant != tenant_id:
                raise ValueError("memory adapter tenant does not match service tenant")

    def record(
        self,
        scope: MemoryScope,
        *,
        key: str,
        value: str,
        source: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryOperationResult:
        user_id, session_id = self._context(scope)
        clean_key = redact_secrets(key.strip())
        now = datetime.now(UTC)
        entry = MemoryEntry(
            id=self._id(scope, clean_key),
            tenant_id=self.tenant_id,
            scope=scope,
            user_id=user_id,
            session_id=session_id,
            key=clean_key,
            value=redact_secrets(value.strip()),
            source=redact_secrets(source.strip()),
            metadata=_safe_value(metadata or {}),
            created_at=now,
            updated_at=now,
        )
        try:
            stored = self._adapter(scope).record(entry)
        except Exception as exc:
            return self._failure(scope, exc)
        return MemoryOperationResult("completed", (stored,), affected=1)

    def recall(self, scope: MemoryScope, *, limit: int = 50) -> MemoryOperationResult:
        if not 1 <= limit <= 100:
            raise ValueError("limit must be between 1 and 100")
        user_id, session_id = self._context(scope)
        try:
            items = self._adapter(scope).recall(
                scope=scope,
                user_id=user_id,
                session_id=session_id,
                limit=limit,
            )
        except Exception as exc:
            return self._failure(scope, exc)
        return MemoryOperationResult("completed", items)

    def clear(self, scope: MemoryScope, *, key: str | None = None) -> MemoryOperationResult:
        clean_key = redact_secrets(key.strip()) if key is not None else None
        if key is not None and not clean_key:
            raise ValueError("key must not be blank")
        user_id, session_id = self._context(scope)
        try:
            affected = self._adapter(scope).clear(
                scope=scope,
                user_id=user_id,
                session_id=session_id,
                key=clean_key,
            )
        except Exception as exc:
            return self._failure(scope, exc)
        return MemoryOperationResult("completed", affected=affected)

    def _adapter(self, scope: MemoryScope) -> MemoryAdapter:
        if scope in {MemoryScope.CONVERSATION, MemoryScope.WORKFLOW}:
            return self.short_term
        return self.durable

    def _context(self, scope: MemoryScope) -> tuple[str | None, str | None]:
        if scope in {MemoryScope.CONVERSATION, MemoryScope.WORKFLOW}:
            return self.user_id, self.session_id
        if scope is MemoryScope.USER:
            return self.user_id, None
        return None, None

    def _id(self, scope: MemoryScope, key: str) -> str:
        user_id, session_id = self._context(scope)
        identity = "\0".join(
            (self.tenant_id, scope.value, user_id or "", session_id or "", key.strip())
        )
        return f"memory-{hashlib.sha256(identity.encode()).hexdigest()[:32]}"

    @staticmethod
    def _failure(scope: MemoryScope, exc: Exception) -> MemoryOperationResult:
        return MemoryOperationResult(
            "degraded",
            errors=(f"{scope.value}: {redact_secrets(str(exc))}",),
        )
