"""Safe document ingestion, extraction, and coordinated indexing."""

from backend.app.ingestion.loaders import LoadedDocument, load_document
from backend.app.ingestion.pipeline import IngestionPipeline, IngestionResult

__all__ = ["IngestionPipeline", "IngestionResult", "LoadedDocument", "load_document"]
