from dataclasses import dataclass

from .ingestion import Chunk


@dataclass(frozen=True)
class RetrievalResult:
    chunk: Chunk
    score: float
    original_file_name: str
