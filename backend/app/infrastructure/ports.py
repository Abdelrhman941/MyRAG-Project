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

        Performs a hybrid (dense + sparse) retrieval against the vector store
        using RRF fusion.
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


class SessionRepositoryPort(Protocol):
    """Port for chat session storage."""

    async def create_session(self) -> UUID:
        """Create a new session and return its ID."""
        ...

    async def get_session(self, session_id: UUID) -> dict[str, Any] | None:
        """Return the session info (id, title, summary, created_at, updated_at)."""
        ...

    async def list_sessions(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List sessions ordered by created_at desc."""
        ...

    async def delete_session(self, session_id: UUID) -> None:
        """Delete a session and all its messages."""
        ...

    async def add_message(
        self, session_id: UUID, role: str, content: str
    ) -> dict[str, Any]:
        """Add a message to the session."""
        ...

    async def list_messages(self, session_id: UUID) -> list[dict[str, Any]]:
        """List all messages for a session (oldest first)."""
        ...

    async def get_recent_messages(
        self, session_id: UUID, n: int
    ) -> list[dict[str, Any]]:
        """List the last N messages for a session (oldest first)."""
        ...

    async def update_summary(self, session_id: UUID, summary: str) -> None:
        """Update the long-term summary for a session."""
        ...

    async def update_title(self, session_id: UUID, title: str) -> None:
        """Update the title of a session."""
        ...
