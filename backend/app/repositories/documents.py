"""Repository for source documents and their future retrieval chunks."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Document, DocumentChunk
from backend.app.repositories.base import TenantRepository


class DocumentRepository(TenantRepository[Document]):
    def __init__(self, session: Session, tenant_id: str) -> None:
        super().__init__(session, Document, tenant_id)

    def by_source_path(self, source_path: str) -> Document | None:
        return self.session.scalar(
            select(Document).where(
                Document.tenant_id == self.tenant_id,
                Document.source_path == source_path,
            )
        )

    def chunks(self, document_id: str) -> list[DocumentChunk]:
        return list(
            self.session.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.tenant_id == self.tenant_id,
                    DocumentChunk.document_id == document_id,
                )
                .order_by(DocumentChunk.ordinal)
            )
        )
