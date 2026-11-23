"""Middleware support objects remain bounded and deterministic."""

from datetime import UTC, datetime

from backend.app.middleware.audit import AuditTrail, RequestAuditRecord
from backend.app.middleware.rate_limit import InMemoryRateLimiter


def test_audit_trail_retains_only_the_configured_number_of_records() -> None:
    trail = AuditTrail(max_records=2)
    for number in range(3):
        trail.append(
            RequestAuditRecord(
                request_id=f"request-{number}",
                method="GET",
                path="/",
                status_code=200,
                actor_id=None,
                tenant_id=None,
                occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
            )
        )

    assert [record.request_id for record in trail.records()] == ["request-1", "request-2"]


def test_rate_limiter_isolates_clients_and_reopens_after_the_window() -> None:
    now = [0.0]
    limiter = InMemoryRateLimiter(2, window_seconds=60, clock=lambda: now[0])

    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is True
    assert limiter.allow("client-a") is False
    assert limiter.allow("client-b") is True

    now[0] = 61.0
    assert limiter.allow("client-a") is True
