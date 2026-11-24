"""Safe in-process request audit trail for the local Phase 3 runtime."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("novaenterprise.audit")


@dataclass(frozen=True)
class RequestAuditRecord:
    request_id: str
    method: str
    path: str
    status_code: int
    actor_id: str | None
    tenant_id: str | None
    occurred_at: datetime


class AuditTrail:
    def __init__(self, *, max_records: int = 10_000) -> None:
        if max_records < 1:
            raise ValueError("max_records must be positive")
        self._records: deque[RequestAuditRecord] = deque(maxlen=max_records)
        self._lock = Lock()

    def append(self, record: RequestAuditRecord) -> None:
        with self._lock:
            self._records.append(record)

    def records(self) -> tuple[RequestAuditRecord, ...]:
        with self._lock:
            return tuple(self._records)


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, trail: AuditTrail) -> None:
        super().__init__(app)
        self.trail = trail

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            user = getattr(request.state, "user", None)
            record = RequestAuditRecord(
                request_id=getattr(request.state, "request_id", "unknown"),
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                actor_id=getattr(user, "id", None),
                tenant_id=getattr(user, "tenant_id", None),
                occurred_at=datetime.now(UTC),
            )
            self.trail.append(record)
            logger.info(
                "request_audit",
                extra={
                    "request_id": record.request_id,
                    "method": record.method,
                    "path": record.path,
                    "status_code": record.status_code,
                    "actor_id": record.actor_id,
                    "tenant_id": record.tenant_id,
                },
            )
