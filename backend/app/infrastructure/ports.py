"""Ports (Protocols) for external system adapters.

Each Protocol defines the interface that a concrete adapter must satisfy.
Services depend only on these protocols; never on concrete adapters.
"""

from pathlib import Path
from typing import Any, Protocol
from uuid import UUID

from ..models import Chunk


class VectorStorePort(Protocol):
    """Port for interacting with the vector database."""

    async def ensure_collection(self) -> None:
        """Ensure the target collection exists with the required configuration."""
        ...

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
        payload_metadata: dict[str, Any],
    ) -> None:
        """Upsert embedded chunks into the vector store.

        The call is idempotent: deterministic point IDs (uuid5 of document_id +
        chunk_index) mean re-ingesting the same document does not duplicate points.
        """
        ...

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all vectors associated with a document ID."""
        ...

    async def query(
        self,
        query_dense: list[float],
        query_sparse: dict[int, float] | None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve the top-*limit* chunks closest to the query vectors.

        Not implemented in Stage 03 — raises NotImplementedError.
        Stage 04 will implement hybrid retrieval here.
        """
        ...


class FileStoragePort(Protocol):
    """Port for file storage adapters (local filesystem, S3, etc.)."""

    async def save(self, filename: str, content: bytes) -> None:
        """Persist *content* under *filename*."""
        ...

    async def read(self, filename: str) -> bytes:
        """Return the raw bytes stored under *filename*."""
        ...

    async def delete(self, filename: str) -> None:
        """Remove the file stored under *filename*."""
        ...

    async def move_from(self, source_path: Path, filename: str) -> None:
        """Move a file from an absolute *source_path* to *filename*."""
        ...
