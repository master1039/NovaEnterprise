"""Repositories for resumable research state and inspectable events."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models import ResearchSession, WorkflowEvent
from backend.app.repositories.base import TenantRepository


class ResearchSessionRepository(TenantRepository[ResearchSession]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, ResearchSession, tenant_id)

    def for_user(self, user_id: str) -> list[ResearchSession]:
        return list(
            self.session.scalars(
                select(ResearchSession)
                .where(
                    ResearchSession.tenant_id == self.tenant_id,
                    ResearchSession.user_id == user_id,
                )
                .order_by(ResearchSession.created_at.desc())
            )
        )


class WorkflowEventRepository(TenantRepository[WorkflowEvent]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, WorkflowEvent, tenant_id)

    def next_sequence(self, session_id: str) -> int:
        current = self.session.scalar(
            select(func.max(WorkflowEvent.sequence)).where(
                WorkflowEvent.tenant_id == self.tenant_id,
                WorkflowEvent.session_id == session_id,
            )
        )
        return int(current or 0) + 1

    def for_session(self, session_id: str) -> list[WorkflowEvent]:
        return list(
            self.session.scalars(
                select(WorkflowEvent)
                .where(
                    WorkflowEvent.tenant_id == self.tenant_id,
                    WorkflowEvent.session_id == session_id,
                )
                .order_by(WorkflowEvent.sequence)
            )
        )
