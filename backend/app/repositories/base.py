"""Small generic repository that applies tenant scope to every query."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.base import Base


class TenantRepository[ModelT: Base]:
    def __init__(self, session: Session, model: type[ModelT], tenant_id: str) -> None:
        self.session = session
        self.model = model
        self.tenant_id = tenant_id

    def add(self, entity: ModelT) -> ModelT:
        if getattr(entity, "tenant_id", None) != self.tenant_id:
            raise ValueError("entity tenant_id does not match repository tenant")
        self.session.add(entity)
        self.session.flush()
        return entity

    def get(self, entity_id: str) -> ModelT | None:
        return self.session.scalar(
            select(self.model).where(
                self.model.id == entity_id,
                self.model.tenant_id == self.tenant_id,
            )
        )

    def list(self, *, limit: int = 100, offset: int = 0) -> list[ModelT]:
        if not 1 <= limit <= 1000 or offset < 0:
            raise ValueError("limit must be 1..1000 and offset must be non-negative")
        return list(
            self.session.scalars(
                select(self.model)
                .where(self.model.tenant_id == self.tenant_id)
                .order_by(self.model.id)
                .limit(limit)
                .offset(offset)
            )
        )

    def count(self) -> int:
        return int(
            self.session.scalar(
                select(func.count())
                .select_from(self.model)
                .where(self.model.tenant_id == self.tenant_id)
            )
            or 0
        )
