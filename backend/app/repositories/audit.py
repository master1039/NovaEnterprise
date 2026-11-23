"""Append-only audit record access."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import AuditLog
from backend.app.repositories.base import TenantRepository


class AuditLogRepository(TenantRepository[AuditLog]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, AuditLog, tenant_id)

    def for_resource(self, resource_type: str, resource_id: str) -> list[AuditLog]:
        return list(
            self.session.scalars(
                select(AuditLog)
                .where(
                    AuditLog.tenant_id == self.tenant_id,
                    AuditLog.resource_type == resource_type,
                    AuditLog.resource_id == resource_id,
                )
                .order_by(AuditLog.created_at)
            )
        )
