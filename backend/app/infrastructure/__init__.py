from ..core.config import Settings
from .db.session import get_db
from .file_storage.storage import DocumentStorage
from .llm_provider import OpenAICompatibleLLM
from .ports import (
    FileStoragePort,
    LLMProviderPort,
    SessionRepositoryPort,
    VectorStorePort,
)
from .session_store import SqliteSessionRepository
from .vector_store.qdrant import QdrantVectorStore


def build_vector_store(settings: Settings) -> VectorStorePort:
    """Build the configured vector-store adapter."""
    return QdrantVectorStore(settings)


__all__ = [
    "DocumentStorage",
    "FileStoragePort",
    "LLMProviderPort",
    "OpenAICompatibleLLM",
    "QdrantVectorStore",
    "SessionRepositoryPort",
    "SqliteSessionRepository",
    "VectorStorePort",
    "build_vector_store",
    "get_db",
]
