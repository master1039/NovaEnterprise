"""Tenant-scoped, one-use approval gate for destructive operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from threading import Lock
from uuid import uuid4

from backend.app.schemas.common import UserRole


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CONSUMED = "consumed"


class ApprovalError(ValueError):
    pass


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    tenant_id: str
    action: str
    resource_id: str
    requested_by: str
    status: ApprovalStatus
    created_at: datetime
    decided_by: str | None = None
    decided_at: datetime | None = None


class ApprovalService:
    def __init__(self, *, id_factory: Callable[[], str] | None = None) -> None:
        self._id_factory = id_factory or (lambda: str(uuid4()))
        self._requests: dict[str, ApprovalRequest] = {}
        self._lock = Lock()

    def request(
        self, *, tenant_id: str, action: str, resource_id: str, requested_by: str
    ) -> ApprovalRequest:
        if not all(value.strip() for value in (tenant_id, action, resource_id, requested_by)):
            raise ApprovalError("approval fields must not be blank")
        approval = ApprovalRequest(
            id=self._id_factory(),
            tenant_id=tenant_id,
            action=action,
            resource_id=resource_id,
            requested_by=requested_by,
            status=ApprovalStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        with self._lock:
            self._requests[approval.id] = approval
        return approval

    def decide(
        self,
        approval_id: str,
        *,
        tenant_id: str,
        decided_by: str,
        decided_by_role: UserRole,
        approve: bool,
    ) -> ApprovalRequest:
        if decided_by_role is not UserRole.ADMIN:
            raise ApprovalError("only an admin can decide an approval")
        with self._lock:
            approval = self._find(approval_id, tenant_id)
            if approval.status is not ApprovalStatus.PENDING:
                raise ApprovalError("approval is no longer pending")
            updated = replace(
                approval,
                status=ApprovalStatus.APPROVED if approve else ApprovalStatus.REJECTED,
                decided_by=decided_by,
                decided_at=datetime.now(UTC),
            )
            self._requests[approval_id] = updated
            return updated

    def consume(
        self, approval_id: str, *, tenant_id: str, action: str, resource_id: str
    ) -> ApprovalRequest:
        with self._lock:
            approval = self._find(approval_id, tenant_id)
            if approval.status is not ApprovalStatus.APPROVED:
                raise ApprovalError("approval is not approved")
            if approval.action != action or approval.resource_id != resource_id:
                raise ApprovalError("approval does not match the requested action and resource")
            consumed = replace(approval, status=ApprovalStatus.CONSUMED)
            self._requests[approval_id] = consumed
            return consumed

    def get(self, approval_id: str, *, tenant_id: str) -> ApprovalRequest:
        with self._lock:
            return self._find(approval_id, tenant_id)

    def _find(self, approval_id: str, tenant_id: str) -> ApprovalRequest:
        approval = self._requests.get(approval_id)
        if approval is None or approval.tenant_id != tenant_id:
            raise ApprovalError("approval request not found")
        return approval
