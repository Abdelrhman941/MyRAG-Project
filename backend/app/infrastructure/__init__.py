from .db.session import get_db
from .file_storage.storage import DocumentStorage
from .llm_provider import OpenAICompatibleLLM
from .ports import (
    FileStoragePort,
    LLMProviderPort,
    SessionRepositoryPort,
    VectorStorePort,
)
from .session_store import NotFoundError, SqliteSessionRepository
from .vector_store.qdrant import QdrantVectorStore
from ..core.config import Settings


def build_vector_store(settings: Settings) -> VectorStorePort:
    return QdrantVectorStore(settings)


__all__ = [
    "DocumentStorage",
    "FileStoragePort",
    "LLMProviderPort",
    "NotFoundError",
    "OpenAICompatibleLLM",
    "QdrantVectorStore",
    "SessionRepositoryPort",
    "SqliteSessionRepository",
    "VectorStorePort",
    "build_vector_store",
    "get_db",
]
