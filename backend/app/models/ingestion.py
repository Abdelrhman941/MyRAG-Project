from dataclasses import dataclass
from uuid import UUID


@dataclass(slots=True)
class ParsedSegment:
    """A segment of text parsed from a document, before chunking."""

    text: str
    page_number: int | None = None
    section: str | None = None


@dataclass(slots=True)
class Chunk:
    """A chunk of text ready for embedding and vector storage."""

    text: str
    document_id: UUID
    chunk_index: int
    page_number: int | None = None
    section: str | None = None
