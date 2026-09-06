from __future__ import annotations

from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core import get_settings
from ..models import Chunk, ParsedSegment

_splitter: RecursiveCharacterTextSplitter | None = None


def _get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter

    if _splitter is None:
        settings = get_settings()

        _splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=settings.CHUNK_SIZE_TOKENS,
            chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
        )

    return _splitter


def chunk(
    segments: list[ParsedSegment],
    document_id: UUID,
) -> list[Chunk]:
    """Convert parsed segments into embedding-ready chunks."""
    if not segments:
        return []

    splitter = _get_splitter()
    chunks: list[Chunk] = []

    for segment in segments:
        raw_chunks = splitter.split_text(segment.text)

        for text in raw_chunks:
            chunks.append(
                Chunk(
                    text=text,
                    document_id=document_id,
                    chunk_index=len(chunks),
                    page_number=segment.page_number,
                    section=segment.section,
                )
            )

    return chunks
