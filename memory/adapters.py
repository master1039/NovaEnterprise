"""Replaceable short-term cache and durable SQL adapters for scoped memory."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.cache import CacheBackend
from backend.app.models import OrganizationalMemory, ScopedMemory
from memory.schemas import MemoryEntry, MemoryScope

_SHORT_TERM = {MemoryScope.CONVERSATION, MemoryScope.WORKFLOW}
_DURABLE = {MemoryScope.USER, MemoryScope.ORGANIZATIONAL}


@runtime_checkable
class MemoryAdapter(Protocol):
    def record(self, entry: MemoryEntry) -> MemoryEntry: ...

    def recall(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        limit: int,
    ) -> tuple[MemoryEntry, ...]: ...

    def clear(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        key: str | None,
    ) -> int: ...


def _part(value: str | None) -> str:
    resolved = value or ""
    return f"{len(resolved)}:{resolved}"


class CacheMemoryAdapter:
    """Store session-bound scopes behind the Phase 4 cache protocol."""

    def __init__(self, backend: CacheBackend, *, tenant_id: str, ttl_seconds: int = 3600) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        if ttl_seconds < 1:
            raise ValueError("ttl_seconds must be positive")
        self.backend = backend
        self.tenant_id = tenant_id
        self.ttl_seconds = ttl_seconds

    def _key(self, scope: MemoryScope, user_id: str | None, session_id: str | None) -> str:
        if scope not in _SHORT_TERM:
            raise ValueError("cache adapter only supports conversation and workflow memory")
        return ":".join(
            ("memory", _part(self.tenant_id), scope.value, _part(user_id), _part(session_id))
        )

    def _load(
        self, scope: MemoryScope, user_id: str | None, session_id: str | None
    ) -> list[MemoryEntry]:
        raw = self.backend.get(self._key(scope, user_id, session_id))
        if raw is None:
            return []
        payload = json.loads(raw)
        if not isinstance(payload, list):
            raise ValueError("cached memory must be a JSON array")
        entries = [MemoryEntry.model_validate(item) for item in payload]
        if any(
            entry.tenant_id != self.tenant_id
            or entry.scope is not scope
            or entry.user_id != user_id
            or entry.session_id != session_id
            for entry in entries
        ):
            raise ValueError("cached memory context mismatch")
        return entries

    def _save(
        self,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        entries: list[MemoryEntry],
    ) -> None:
        payload = [entry.model_dump(mode="json") for entry in entries]
        self.backend.set(
            self._key(scope, user_id, session_id),
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode(),
            ttl_seconds=self.ttl_seconds,
        )

    def record(self, entry: MemoryEntry) -> MemoryEntry:
        if entry.tenant_id != self.tenant_id:
            raise ValueError("entry tenant does not match memory adapter tenant")
        entries = self._load(entry.scope, entry.user_id, entry.session_id)
        existing = next((item for item in entries if item.id == entry.id), None)
        stored = entry.model_copy(
            update={"created_at": existing.created_at if existing else entry.created_at}
        )
        entries = [item for item in entries if item.id != entry.id]
        entries.append(stored)
        entries.sort(key=lambda item: (item.key, item.id))
        self._save(entry.scope, entry.user_id, entry.session_id, entries)
        return stored

    def recall(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        limit: int,
    ) -> tuple[MemoryEntry, ...]:
        return tuple(self._load(scope, user_id, session_id)[:limit])

    def clear(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        key: str | None,
    ) -> int:
        entries = self._load(scope, user_id, session_id)
        retained = [entry for entry in entries if key is not None and entry.key != key]
        removed = len(entries) - len(retained)
        cache_key = self._key(scope, user_id, session_id)
        if retained:
            self._save(scope, user_id, session_id, retained)
        else:
            self.backend.delete(cache_key)
        return removed


class SqlMemoryAdapter:
    """Persist user and organization memory with explicit tenant predicates."""

    def __init__(self, session: Session, *, tenant_id: str) -> None:
        if not tenant_id.strip():
            raise ValueError("tenant_id must not be blank")
        self.session = session
        self.tenant_id = tenant_id

    def record(self, entry: MemoryEntry) -> MemoryEntry:
        if entry.scope not in _DURABLE:
            raise ValueError("SQL adapter only supports user and organizational memory")
        if entry.tenant_id != self.tenant_id:
            raise ValueError("entry tenant does not match memory adapter tenant")
        try:
            if entry.scope is MemoryScope.ORGANIZATIONAL:
                existing_org = self.session.scalar(
                    select(OrganizationalMemory)
                    .where(
                        OrganizationalMemory.tenant_id == self.tenant_id,
                        OrganizationalMemory.key == entry.key,
                    )
                    .order_by(OrganizationalMemory.id)
                    .limit(1)
                )
                if existing_org is None:
                    existing_org = OrganizationalMemory(
                        id=entry.id,
                        tenant_id=self.tenant_id,
                        key=entry.key,
                        value=entry.value,
                        source=entry.source,
                        metadata_json=entry.metadata,
                        created_at=entry.created_at,
                        updated_at=entry.updated_at,
                    )
                    self.session.add(existing_org)
                else:
                    existing_org.value = entry.value
                    existing_org.source = entry.source
                    existing_org.metadata_json = entry.metadata
                    existing_org.updated_at = datetime.now(UTC)
                self.session.commit()
                return self._organization_entry(existing_org)

            existing = self.session.scalar(
                select(ScopedMemory).where(
                    ScopedMemory.id == entry.id,
                    ScopedMemory.tenant_id == self.tenant_id,
                )
            )
            now = datetime.now(UTC)
            if existing is None:
                existing = ScopedMemory(
                    id=entry.id,
                    tenant_id=self.tenant_id,
                    scope=entry.scope.value,
                    user_id=entry.user_id,
                    session_id=entry.session_id,
                    key=entry.key,
                    value=entry.value,
                    source=entry.source,
                    metadata_json=entry.metadata,
                    created_at=entry.created_at,
                    updated_at=now,
                )
                self.session.add(existing)
            else:
                existing.value = entry.value
                existing.source = entry.source
                existing.metadata_json = entry.metadata
                existing.updated_at = now
            self.session.commit()
            return self._entry(existing)
        except Exception:
            self.session.rollback()
            raise

    def recall(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        limit: int,
    ) -> tuple[MemoryEntry, ...]:
        if scope not in _DURABLE or session_id is not None:
            raise ValueError("invalid durable memory scope context")
        if scope is MemoryScope.ORGANIZATIONAL:
            rows = self.session.scalars(
                select(OrganizationalMemory)
                .where(OrganizationalMemory.tenant_id == self.tenant_id)
                .order_by(OrganizationalMemory.key, OrganizationalMemory.id)
                .limit(limit)
            )
            return tuple(self._organization_entry(row) for row in rows)
        statement = select(ScopedMemory).where(
            ScopedMemory.tenant_id == self.tenant_id,
            ScopedMemory.scope == scope.value,
        )
        if user_id is None:
            statement = statement.where(ScopedMemory.user_id.is_(None))
        else:
            statement = statement.where(ScopedMemory.user_id == user_id)
        rows = self.session.scalars(
            statement.order_by(ScopedMemory.key, ScopedMemory.id).limit(limit)
        )
        return tuple(self._entry(row) for row in rows)

    def clear(
        self,
        *,
        scope: MemoryScope,
        user_id: str | None,
        session_id: str | None,
        key: str | None,
    ) -> int:
        if scope not in _DURABLE or session_id is not None:
            raise ValueError("invalid durable memory scope context")
        if scope is MemoryScope.ORGANIZATIONAL:
            statement = delete(OrganizationalMemory).where(
                OrganizationalMemory.tenant_id == self.tenant_id
            )
            key_column = OrganizationalMemory.key
        else:
            statement = delete(ScopedMemory).where(
                ScopedMemory.tenant_id == self.tenant_id,
                ScopedMemory.scope == scope.value,
                ScopedMemory.user_id == user_id,
            )
            key_column = ScopedMemory.key
        if key is not None:
            statement = statement.where(key_column == key)
        try:
            result = self.session.execute(statement)
            self.session.commit()
            return int(result.rowcount or 0)
        except Exception:
            self.session.rollback()
            raise

    @staticmethod
    def _entry(row: ScopedMemory) -> MemoryEntry:
        return MemoryEntry(
            id=row.id,
            tenant_id=row.tenant_id,
            scope=MemoryScope(row.scope),
            user_id=row.user_id,
            session_id=row.session_id,
            key=row.key,
            value=row.value,
            source=row.source,
            metadata=row.metadata_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    @staticmethod
    def _organization_entry(row: OrganizationalMemory) -> MemoryEntry:
        return MemoryEntry(
            id=row.id,
            tenant_id=row.tenant_id,
            scope=MemoryScope.ORGANIZATIONAL,
            key=row.key,
            value=row.value,
            source=row.source,
            metadata=row.metadata_json,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
