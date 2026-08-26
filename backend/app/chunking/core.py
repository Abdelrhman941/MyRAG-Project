import logging
from uuid import UUID

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ..core import get_settings
from ..models import Chunk, ParsedSegment

logger = logging.getLogger(__name__)
settings = get_settings()


def chunk(segments: list[ParsedSegment], document_id: UUID) -> list[Chunk]:
    """Convert parsed segments into embedding-ready chunks."""
    if not segments:
        return []

    # Combine segments into a single document string, keeping track of order.
    # RecursiveCharacterTextSplitter operates on a single text string.
    # For now, we will join the segments with a space or double newline.
    # Since whitespace collapse already happened, joining with a newline is good.
    full_text = "\n\n".join(seg.text for seg in segments)

    # Initialize the token-aware text splitter
    splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=settings.CHUNK_SIZE_TOKENS,
        chunk_overlap=settings.CHUNK_OVERLAP_TOKENS,
    )

    # Perform the split
    raw_chunks = splitter.split_text(full_text)

    # Convert to Chunk objects
    chunks: list[Chunk] = []
    for i, text in enumerate(raw_chunks):
        chunks.append(
            Chunk(
                text=text,
                document_id=document_id,
                chunk_index=i,
            )
        )

    return chunks
