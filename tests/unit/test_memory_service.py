"""Scoped memory preserves provenance and tenant, user, and session boundaries."""

from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from backend.app.core.cache import InMemoryCache
from backend.app.models import OrganizationalMemory
from memory.adapters import CacheMemoryAdapter, SqlMemoryAdapter
from memory.memory_service import MemoryService
from memory.schemas import MemoryEntry, MemoryScope


def _service(
    session: Session,
    cache: InMemoryCache,
    *,
    tenant_id: str = "tenant-a",
    user_id: str = "user-a",
    session_id: str = "session-a",
) -> MemoryService:
    return MemoryService(
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
        short_term=CacheMemoryAdapter(cache, tenant_id=tenant_id),
        durable=SqlMemoryAdapter(session, tenant_id=tenant_id),
    )


def test_memory_entry_contract_enforces_scope_context() -> None:
    common = {
        "id": "memory-1",
        "tenant_id": "tenant-a",
        "key": "answer_style",
        "value": "concise",
        "source": "user-setting",
    }

    with pytest.raises(ValidationError, match="user_id and session_id"):
        MemoryEntry(scope=MemoryScope.CONVERSATION, **common)
    with pytest.raises(ValidationError, match="user_id is required"):
        MemoryEntry(scope=MemoryScope.USER, **common)
    with pytest.raises(ValidationError, match="must not carry user_id or session_id"):
        MemoryEntry(scope=MemoryScope.ORGANIZATIONAL, user_id="user-a", **common)


def test_record_recall_and_clear_conversation_memory_with_provenance(
    db_session: Session,
) -> None:
    cache = InMemoryCache()
    service = _service(db_session, cache)

    recorded = service.record(
        MemoryScope.CONVERSATION,
        key="current_topic",
        value="Payments API reliability",
        source="research-question",
        metadata={"turn": 2},
    )
    recalled = service.recall(MemoryScope.CONVERSATION)

    assert recorded.status == "completed"
    assert recalled.status == "completed"
    assert [(item.key, item.value) for item in recalled.items] == [
        ("current_topic", "Payments API reliability")
    ]
    assert recalled.items[0].source == "research-question"
    assert recalled.items[0].metadata == {"turn": 2}
    assert service.clear(MemoryScope.CONVERSATION, key="current_topic").affected == 1
    assert service.recall(MemoryScope.CONVERSATION).items == ()


def test_short_term_scopes_are_isolated_by_tenant_user_session_and_scope(
    db_session: Session,
) -> None:
    cache = InMemoryCache()
    owner = _service(db_session, cache)
    owner.record(MemoryScope.CONVERSATION, key="topic", value="payments", source="question")
    owner.record(MemoryScope.WORKFLOW, key="step", value="retrieve", source="workflow")

    assert len(owner.recall(MemoryScope.CONVERSATION).items) == 1
    assert len(owner.recall(MemoryScope.WORKFLOW).items) == 1
    assert (
        _service(db_session, cache, session_id="session-b").recall(MemoryScope.CONVERSATION).items
        == ()
    )
    assert (
        _service(db_session, cache, user_id="user-b").recall(MemoryScope.CONVERSATION).items == ()
    )
    assert (
        _service(db_session, cache, tenant_id="tenant-b").recall(MemoryScope.CONVERSATION).items
        == ()
    )


def test_user_and_organizational_memory_are_durable_and_strictly_isolated(
    db_session: Session,
) -> None:
    cache = InMemoryCache()
    owner = _service(db_session, cache)
    owner.record(MemoryScope.USER, key="answer_style", value="concise", source="profile")
    owner.record(
        MemoryScope.ORGANIZATIONAL,
        key="fiscal_calendar",
        value="calendar quarters",
        source="finance-policy",
        metadata={"owner": "finance"},
    )

    fresh_service = _service(db_session, InMemoryCache(), session_id="session-new")
    assert [item.value for item in fresh_service.recall(MemoryScope.USER).items] == ["concise"]
    assert [item.value for item in fresh_service.recall(MemoryScope.ORGANIZATIONAL).items] == [
        "calendar quarters"
    ]
    assert fresh_service.recall(MemoryScope.ORGANIZATIONAL).items[0].metadata == {
        "owner": "finance"
    }
    assert _service(db_session, cache, user_id="user-b").recall(MemoryScope.USER).items == ()
    assert (
        len(_service(db_session, cache, user_id="user-b").recall(MemoryScope.ORGANIZATIONAL).items)
        == 1
    )
    assert (
        _service(db_session, cache, tenant_id="tenant-b").recall(MemoryScope.ORGANIZATIONAL).items
        == ()
    )


def test_organizational_recall_includes_phase2_seeded_facts(db_session: Session) -> None:
    db_session.add(
        OrganizationalMemory(
            id="memory-fiscal-calendar",
            tenant_id="tenant-a",
            key="fiscal_calendar",
            value="Calendar quarters",
            source="Finance policy",
        )
    )
    db_session.commit()

    result = _service(db_session, InMemoryCache()).recall(MemoryScope.ORGANIZATIONAL)

    assert [(item.id, item.key, item.source) for item in result.items] == [
        ("memory-fiscal-calendar", "fiscal_calendar", "Finance policy")
    ]

    updated = _service(db_session, InMemoryCache()).record(
        MemoryScope.ORGANIZATIONAL,
        key="fiscal_calendar",
        value="Fiscal year starts in April",
        source="Updated finance policy",
        metadata={"revision": 2},
    )

    assert updated.items[0].id == "memory-fiscal-calendar"
    assert updated.items[0].metadata == {"revision": 2}
    recalled = _service(db_session, InMemoryCache()).recall(MemoryScope.ORGANIZATIONAL)
    assert [(item.id, item.value) for item in recalled.items] == [
        ("memory-fiscal-calendar", "Fiscal year starts in April")
    ]


def test_record_upserts_a_stable_identity_and_recall_is_bounded_and_ordered(
    db_session: Session,
) -> None:
    service = _service(db_session, InMemoryCache())
    first = service.record(MemoryScope.USER, key="zeta", value="old", source="profile")
    updated = service.record(MemoryScope.USER, key="zeta", value="new", source="profile")
    service.record(MemoryScope.USER, key="alpha", value="first", source="profile")

    result = service.recall(MemoryScope.USER, limit=1)

    assert first.items[0].id == updated.items[0].id
    assert [item.key for item in result.items] == ["alpha"]
    with pytest.raises(ValueError, match="limit"):
        service.recall(MemoryScope.USER, limit=0)


def test_clear_never_deletes_another_scope_or_users_memory(db_session: Session) -> None:
    cache = InMemoryCache()
    owner = _service(db_session, cache)
    other = _service(db_session, cache, user_id="user-b")
    owner.record(MemoryScope.USER, key="style", value="concise", source="profile")
    other.record(MemoryScope.USER, key="style", value="detailed", source="profile")
    owner.record(
        MemoryScope.ORGANIZATIONAL,
        key="policy",
        value="cite sources",
        source="research-policy",
    )

    assert owner.clear(MemoryScope.USER).affected == 1
    assert owner.recall(MemoryScope.USER).items == ()
    assert [item.value for item in other.recall(MemoryScope.USER).items] == ["detailed"]
    assert len(owner.recall(MemoryScope.ORGANIZATIONAL).items) == 1


def test_secrets_are_redacted_recursively_before_storage(db_session: Session) -> None:
    service = _service(db_session, InMemoryCache())

    result = service.record(
        MemoryScope.USER,
        key="api_key=key-secret",
        value="api_key=super-secret",
        source="password=hunter2",
        metadata={"api_key=metadata-key-secret": ["Authorization: Bearer abc.def"]},
    )
    item = result.items[0]

    assert "super-secret" not in item.value
    assert "key-secret" not in item.key
    assert "hunter2" not in item.source
    assert "abc.def" not in str(item.metadata)
    assert "metadata-key-secret" not in str(item.metadata)
    assert "[REDACTED]" in f"{item.value}{item.source}{item.metadata}"
    assert service.clear(MemoryScope.USER, key="api_key=key-secret").affected == 1


def test_cache_rejects_foreign_context_in_a_corrupted_payload(db_session: Session) -> None:
    cache = InMemoryCache()
    adapter = CacheMemoryAdapter(cache, tenant_id="tenant-a")
    service = MemoryService(
        tenant_id="tenant-a",
        user_id="user-a",
        session_id="session-a",
        short_term=adapter,
        durable=SqlMemoryAdapter(db_session, tenant_id="tenant-a"),
    )
    service.record(MemoryScope.CONVERSATION, key="topic", value="payments", source="question")
    cache_key = adapter._key(MemoryScope.CONVERSATION, "user-a", "session-a")
    raw = cache.get(cache_key)
    assert raw is not None
    cache.set(cache_key, raw.replace(b'"tenant_id":"tenant-a"', b'"tenant_id":"tenant-b"'))

    result = service.recall(MemoryScope.CONVERSATION)

    assert result.status == "degraded"
    assert result.items == ()
    assert "context mismatch" in result.errors[0]


class _FailingAdapter:
    def record(self, _entry):
        raise RuntimeError("api_key=must-not-escape")

    def recall(self, **_kwargs):
        raise RuntimeError("api_key=must-not-escape")

    def clear(self, **_kwargs):
        raise RuntimeError("api_key=must-not-escape")


def test_adapter_failure_is_truthful_redacted_and_never_fabricates_memory(
    db_session: Session,
) -> None:
    service = MemoryService(
        tenant_id="tenant-a",
        user_id="user-a",
        session_id="session-a",
        short_term=CacheMemoryAdapter(InMemoryCache(), tenant_id="tenant-a"),
        durable=_FailingAdapter(),  # type: ignore[arg-type]
    )

    result = service.recall(MemoryScope.USER)

    assert result.status == "degraded"
    assert result.items == ()
    assert "must-not-escape" not in result.errors[0]
    assert "[REDACTED]" in result.errors[0]


def test_service_rejects_a_misconfigured_cross_tenant_adapter(db_session: Session) -> None:
    with pytest.raises(ValueError, match="adapter tenant"):
        MemoryService(
            tenant_id="tenant-a",
            user_id="user-a",
            session_id="session-a",
            short_term=CacheMemoryAdapter(InMemoryCache(), tenant_id="tenant-b"),
            durable=SqlMemoryAdapter(db_session, tenant_id="tenant-a"),
        )
