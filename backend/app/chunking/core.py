import logging
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core import get_settings
from ..models import Chunk, ParsedSegment

logger = logging.getLogger(__name__)


_splitter = None


def _get_splitter() -> RecursiveCharacterTextSplitter:
    global _splitter
    if _splitter is None:
        settings = get_settings()
        _splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=settings.CHUNK_SIZE_TOKENS,
            chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
        )
    return _splitter


def chunk(segments: list[ParsedSegment], document_id: UUID) -> list[Chunk]:
    """Convert parsed segments into embedding-ready chunks."""
    if not segments:
        return []

    splitter = _get_splitter()

    chunks: list[Chunk] = []
    chunk_idx = 0

    for seg in segments:
        raw_chunks = splitter.split_text(seg.text)
        for text in raw_chunks:
            chunks.append(
                Chunk(
                    text=text,
                    document_id=document_id,
                    chunk_index=chunk_idx,
                    page_number=seg.page_number,
                    section=seg.section,
                )
            )
            chunk_idx += 1

    return chunks
