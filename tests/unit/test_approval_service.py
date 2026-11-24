"""Destructive actions require scoped, explicit, one-use approval."""

from collections.abc import Iterator

import pytest

from backend.app.schemas.common import UserRole
from backend.app.services.approval_service import (
    ApprovalError,
    ApprovalService,
    ApprovalStatus,
)


def _ids() -> Iterator[str]:
    yield from ("approval-1", "approval-2")


def test_admin_can_approve_and_consume_matching_request_once() -> None:
    ids = _ids()
    service = ApprovalService(id_factory=lambda: next(ids))
    request = service.request(
        tenant_id="tenant-a",
        action="document.delete",
        resource_id="doc-1",
        requested_by="analyst-1",
    )
    approved = service.decide(
        request.id,
        tenant_id="tenant-a",
        decided_by="admin-1",
        decided_by_role=UserRole.ADMIN,
        approve=True,
    )
    assert approved.status is ApprovalStatus.APPROVED

    consumed = service.consume(
        request.id,
        tenant_id="tenant-a",
        action="document.delete",
        resource_id="doc-1",
    )
    assert consumed.status is ApprovalStatus.CONSUMED
    with pytest.raises(ApprovalError, match="not approved"):
        service.consume(
            request.id,
            tenant_id="tenant-a",
            action="document.delete",
            resource_id="doc-1",
        )


def test_approval_rejects_non_admin_and_cross_tenant_or_resource_use() -> None:
    ids = _ids()
    service = ApprovalService(id_factory=lambda: next(ids))
    request = service.request(
        tenant_id="tenant-a",
        action="document.delete",
        resource_id="doc-1",
        requested_by="analyst-1",
    )
    with pytest.raises(ApprovalError, match="admin"):
        service.decide(
            request.id,
            tenant_id="tenant-a",
            decided_by="analyst-2",
            decided_by_role=UserRole.ANALYST,
            approve=True,
        )
    with pytest.raises(ApprovalError, match="not found"):
        service.decide(
            request.id,
            tenant_id="tenant-b",
            decided_by="admin-1",
            decided_by_role=UserRole.ADMIN,
            approve=True,
        )


def test_approval_cannot_be_reused_for_a_different_action_or_resource() -> None:
    service = ApprovalService(id_factory=lambda: "approval-1")
    request = service.request(
        tenant_id="tenant-a",
        action="document.delete",
        resource_id="doc-1",
        requested_by="analyst-1",
    )
    service.decide(
        request.id,
        tenant_id="tenant-a",
        decided_by="admin-1",
        decided_by_role=UserRole.ADMIN,
        approve=True,
    )

    with pytest.raises(ApprovalError, match="does not match"):
        service.consume(
            request.id,
            tenant_id="tenant-a",
            action="document.delete",
            resource_id="doc-2",
        )
    with pytest.raises(ApprovalError, match="does not match"):
        service.consume(
            request.id,
            tenant_id="tenant-a",
            action="document.reindex",
            resource_id="doc-1",
        )
