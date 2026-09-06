"""Protocols defining boundaries to external infrastructure systems."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, TypedDict
from uuid import UUID

from ..models import Chunk


class VectorSearchHit(TypedDict):
    """Normalized vector-search result."""

    id: str
    score: float
    payload: dict[str, Any]


class SessionData(TypedDict):
    """Normalized chat-session data."""

    id: UUID
    title: str | None
    summary: str | None
    summarized_message_count: int
    created_at: datetime
    updated_at: datetime


class MessageData(TypedDict):
    """Normalized chat-message data."""

    id: UUID
    session_id: UUID
    role: str
    content: str
    created_at: datetime
    sources: list[dict[str, Any]] | None


class VectorStorePort(Protocol):
    """Port for vector-store operations."""

    async def ensure_collection(self) -> None:
        """Ensure the vector collection and required indexes exist."""
        ...

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
        payload_metadata: dict[str, Any],
    ) -> None:
        """Upsert embedded document chunks."""
        ...

    async def delete_by_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all vectors belonging to a document."""
        ...

    async def query(
        self,
        query_dense: list[float],
        query_sparse: dict[int, float] | None,
        session_id: UUID,
        limit: int = 5,
    ) -> list[VectorSearchHit]:
        """Search the vector store for relevant chunks."""
        ...


class FileStoragePort(Protocol):
    """Port for document-file storage."""

    async def read(
        self,
        filename: str,
    ) -> bytes:
        """Read document content."""
        ...

    async def delete(
        self,
        filename: str,
    ) -> None:
        """Delete a document."""
        ...

    async def move_from(
        self,
        source_path: Path,
        filename: str,
    ) -> None:
        """Move a temporary file into document storage."""
        ...


class SessionRepositoryPort(Protocol):
    """Port for chat-session persistence."""

    async def create_session(self) -> UUID:
        """Create a chat session."""
        ...

    async def get_session(
        self,
        session_id: UUID,
    ) -> SessionData | None:
        """Return a session by ID."""
        ...

    async def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SessionData]:
        """List sessions ordered by creation time."""
        ...

    async def delete_session(
        self,
        session_id: UUID,
    ) -> None:
        """Delete a chat session."""
        ...

    async def add_message(
        self,
        session_id: UUID,
        role: str,
        content: str,
        sources: list[dict[str, Any]] | None = None,
    ) -> MessageData:
        """Add a message to a session."""
        ...

    async def count_messages(
        self,
        session_id: UUID,
    ) -> int:
        """Count messages in a session."""
        ...

    async def get_messages(
        self,
        session_id: UUID,
        offset: int,
        limit: int,
    ) -> list[MessageData]:
        """Return a chronological message slice."""
        ...

    async def get_recent_messages(
        self,
        session_id: UUID,
        n: int,
    ) -> list[MessageData]:
        """Return the latest messages chronologically."""
        ...

    async def update_summary(
        self,
        session_id: UUID,
        summary: str,
        summarized_count: int,
    ) -> None:
        """Update the session summary."""
        ...

    async def update_title(
        self,
        session_id: UUID,
        title: str,
    ) -> None:
        """Update the session title."""
        ...


class LLMProviderPort(Protocol):
    """Port for external LLM generation."""

    async def generate(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> str:
        """Generate a complete response."""
        ...

    def generate_stream(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Stream a generated response."""
        ...
